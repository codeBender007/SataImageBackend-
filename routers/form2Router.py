from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database.db import get_db
from models.form2Models import Form2HandoverLog, Form2ToolRecord, Form2PDIInspectionRecord
from models.userModels import User
from schemas.form2Schema import (
    Form2SubmitPayload,
    Form2ExtractionResponse,
    Form2ExtractedData,
    Form2DetailResponse,
    Form2ToolRecordSchema,
    Form2DetailsSchema,
    Form2PDISchema
)
from services.form2VisionExtractor import run_form2_vision_extractor

router = APIRouter(prefix="/api/form-b", tags=["Form 2 / Page B - FOP & Shift Handover"])


# ============================================================================
# 1. OCR Upload & Extraction Endpoint
# POST /api/form-b/extract (also /api/form-b/extractimage)
# ============================================================================
@router.post(
    "/extract",
    summary="Upload & Extract Form 2 (Page B) Document",
    response_model=dict
)
@router.post(
    "/extractimage",
    summary="Upload & Extract Form 2 (Page B) Document (Alias)",
    response_model=dict
)
async def extract_form2_document(
    file: UploadFile = File(..., description="Form photo or scanned document (JPG, PNG, HEIC)")
):
    """
    Accepts an uploaded physical form image, runs the Multimodal Document OCR pipeline,
    and returns parsed key-value metadata, 16-row tool table, 5-Why analysis, and PDI matrix.
    Does NOT save permanently to DB yet, enabling human-in-the-loop double verification.
    """
    # 1. Validate file extension / MIME
    allowed_mimes = ["image/jpeg", "image/png", "image/jpg", "image/webp", "image/heic"]
    if file.content_type and file.content_type.lower() not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload a JPG, PNG, or HEIC image file."
        )

    # 2. Read file bytes
    try:
        image_bytes = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded file: {str(e)}"
        )

    # 3. Process via Gemini Vision Extractor
    try:
        extracted_data = run_form2_vision_extractor(
            image_bytes=image_bytes,
            mime_type=file.content_type or "image/jpeg",
            filename=file.filename or "form2_upload.jpg"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR Extraction Engine failed: {str(e)}"
        )

    return {
        "status": "success",
        "message": "Form 2 extracted successfully for verification and human review.",
        "extractionConfidence": 0.95,
        "sourceImage": file.filename,
        "extractedAt": datetime.utcnow().isoformat(),
        "data": extracted_data
    }


# ============================================================================
# 2. Confirm & Submit Endpoint
# POST /api/form-b/save (also /api/form-b/submit and /api/form-b)
# ============================================================================
@router.post(
    "/save",
    summary="Confirm & Persist Validated Form 2 Record",
    status_code=status.HTTP_201_CREATED,
    response_model=dict
)
@router.post(
    "/submit",
    summary="Confirm & Persist Validated Form 2 Record (Alias)",
    status_code=status.HTTP_201_CREATED,
    response_model=dict
)
@router.post(
    "",
    summary="Confirm & Persist Validated Form 2 Record (Root Alias)",
    status_code=status.HTTP_201_CREATED,
    response_model=dict
)
def submit_form2_record(
    payload: Form2SubmitPayload,
    db: Session = Depends(get_db)
):
    """
    Persists the human-verified or corrected Form 2 data into the SQLite database.
    Inserts master header log, child 16 tool rows, and PDI matrix in an atomic transaction.
    """
    try:
        header = payload.header
        details = payload.details
        records = payload.records
        pdi_list = payload.pdiInspection

        # Resolve field values with fallback aliases
        log_date = header.log_date or header.date or payload.date or datetime.utcnow().strftime("%Y-%m-%d")
        shift = header.shift or payload.shift or "A"
        machine_no = header.machine_no or header.machineNo or payload.machineNo or (records[0].machineNo if records else "MC-201")
        qa_cell = header.qa_cell or header.qaCell or "Cell A"
        op_no = header.operation_no or header.operationNo or "10"
        
        emp_id = header.employee_id or header.employeeId or payload.employeeId or "EMP001"
        emp_name = header.employee_name or header.uploadedBy or payload.uploadedBy or "Operator"
        supervisor = header.supervisor_name or details.supervisor or "Supervisor"
        shift_incharge = header.shift_incharge or "Shift Incharge"

        # Calculate summary totals
        total_parts = sum(int(r.fopParts or 0) for r in records) if records else 0
        total_rejections = sum(int(r.fopRejection or 0) for r in records) if records else 0

        # Generate unique Form Code
        year = datetime.utcnow().year
        total_count = db.query(Form2HandoverLog).count()
        form_code = f"FOP-{year}-{str(total_count + 1).zfill(4)}"

        # 1. Create Master Log Record
        master_log = Form2HandoverLog(
            form_code=form_code,
            page_type=header.page_type or "Page B",
            form_title=header.form_title or "First Operation Part (FOP) Record & Shift Handover",
            log_date=log_date,
            shift=shift,
            machine_no=machine_no,
            qa_cell=qa_cell,
            operation_no=op_no,
            employee_id=emp_id,
            employee_name=emp_name,
            supervisor_name=supervisor,
            shift_incharge=shift_incharge,
            module_incharge=header.module_incharge or supervisor,
            status=header.status or "submitted",
            original_image_path=payload.imagePath or header.image_path or "",
            total_fop_parts=total_parts,
            total_fop_rejections=total_rejections,
            
            # 5-Why Problem Analysis
            problem_analysis=details.problemAnalysis or "",
            why_1=details.why1 or "",
            why_2=details.why2 or "",
            why_3=details.why3 or "",
            why_4=details.why4 or "",
            why_5=details.why5 or "",
            root_cause=details.rootCause or "",
            action_1=details.action1 or details.action or "",
            action_2=details.action2 or "",
            
            # Handover Checklist & Quantitative Fields
            handover_check=details.handoverCheck or "",
            rm_online_qty=details.rmOnLineQty or "",
            running_cavity=details.runningCavity or "",
            all_gauges_online=details.allGaugesOnline or "Y",
            missing_gauges=details.missingGauges or "",
            pdi_report_pv_no=details.pdiReportPvNo or "",
            tool_in_line_no=details.toolInLineNo or "",
            shift_communication=details.shiftCommunication or "",
            material_tool_communication=details.materialToolCommunication or "",
            prepared_by_emp_no=details.preparedByEmployeeNo or emp_id
        )

        db.add(master_log)
        db.flush()  # Generates master_log.id

        # 2. Insert Tool Rows
        tool_entities = []
        if records:
            for idx, r in enumerate(records):
                tool_entities.append(Form2ToolRecord(
                    form2_id=master_log.id,
                    row_index=r.rowIndex if r.rowIndex is not None else idx,
                    tool_description=r.toolDescription or "",
                    operation_no=r.operationNo or "",
                    machine_no=r.machineNo or machine_no,
                    tool_no=r.toolNo or "",
                    time_stamp=r.time or "",
                    reason_for_fop=r.reasonForFOP or "",
                    fop_parts=int(r.fopParts or 0),
                    fop_rejection=int(r.fopRejection or 0),
                    tool_set_by=r.toolSetBy or "",
                    handover_check=r.handoverCheck or "",
                    defect=r.defect or "",
                    remarks=r.remarks or "",
                    material_or_tool=r.materialOrTool or ""
                ))
            db.add_all(tool_entities)

        # 3. Insert PDI Matrix Rows
        pdi_entities = []
        if pdi_list:
            for idx, p in enumerate(pdi_list):
                pdi_entities.append(Form2PDIInspectionRecord(
                    form2_id=master_log.id,
                    row_index=p.rowIndex if p.rowIndex is not None else idx,
                    row_label=p.rowLabel or f"Row {idx + 1}",
                    operation_no=p.operationNo or "",
                    machining_rejection=int(p.machiningRejection or 0),
                    casting_rejection=int(p.castingRejection or 0),
                    supplier_info=p.supplierInfo or "",
                    die_cavity_no=p.dieCavityNo or "",
                    abnormality_alarm=p.abnormalityAlarm or ""
                ))
            db.add_all(pdi_entities)

        # 4. Commit Transaction
        db.commit()
        db.refresh(master_log)

        return {
            "status": "success",
            "message": "Form 2 (Page B - FOP & Shift Handover) saved successfully into database.",
            "formId": master_log.id,
            "formCode": master_log.form_code,
            "data": {
                "id": master_log.id,
                "formCode": master_log.form_code,
                "date": master_log.log_date,
                "shift": master_log.shift,
                "machineNo": master_log.machine_no,
                "employeeName": master_log.employee_name,
                "totalFopParts": master_log.total_fop_parts,
                "totalFopRejections": master_log.total_fop_rejections,
                "toolRecordsCount": len(tool_entities)
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist Form 2: {str(e)}"
        )


# ============================================================================
# 3. List All Form 2 Submissions (Read API with Pagination & Filtering)
# GET /api/form-b/list (also GET /api/form-b)
# ============================================================================
@router.get(
    "/list",
    summary="List Form 2 Submissions",
    response_model=dict
)
@router.get(
    "",
    summary="List Form 2 Submissions (Root Alias)",
    response_model=dict
)
def list_form2_records(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    log_date: Optional[str] = Query(None, description="Exact date filter (YYYY-MM-DD)"),
    date_from: Optional[str] = Query(None, description="Start date filter"),
    date_to: Optional[str] = Query(None, description="End date filter"),
    shift: Optional[str] = Query(None, description="Shift filter (A, B, C)"),
    machine_no: Optional[str] = Query(None, description="Machine number filter"),
    employee_id: Optional[str] = Query(None, description="Employee ID filter"),
    status_filter: Optional[str] = Query(None, alias="status", description="Status filter"),
    search: Optional[str] = Query(None, description="Keyword search in form code, machine, operator, etc."),
    db: Session = Depends(get_db)
):
    """
    Returns a paginated list of all saved Form 2 records with flexible filtering.
    """
    try:
        query = db.query(Form2HandoverLog)

        if log_date:
            query = query.filter(Form2HandoverLog.log_date == log_date)
        if date_from:
            query = query.filter(Form2HandoverLog.log_date >= date_from)
        if date_to:
            query = query.filter(Form2HandoverLog.log_date <= date_to)
        if shift:
            query = query.filter(Form2HandoverLog.shift == shift)
        if machine_no:
            query = query.filter(Form2HandoverLog.machine_no.ilike(f"%{machine_no}%"))
        if employee_id:
            query = query.filter(Form2HandoverLog.employee_id == employee_id)
        if status_filter:
            query = query.filter(Form2HandoverLog.status == status_filter)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Form2HandoverLog.form_code.ilike(search_pattern),
                    Form2HandoverLog.employee_name.ilike(search_pattern),
                    Form2HandoverLog.machine_no.ilike(search_pattern),
                    Form2HandoverLog.supervisor_name.ilike(search_pattern),
                    Form2HandoverLog.problem_analysis.ilike(search_pattern)
                )
            )

        total_records = query.count()
        offset = (page - 1) * limit
        items = query.order_by(Form2HandoverLog.id.desc()).offset(offset).limit(limit).all()

        result_list = []
        for log in items:
            result_list.append({
                "id": log.id,
                "formCode": log.form_code,
                "pageType": log.page_type,
                "formTitle": log.form_title,
                "date": log.log_date,
                "shift": log.shift,
                "machineNo": log.machine_no,
                "qaCell": log.qa_cell,
                "operationNo": log.operation_no,
                "employeeId": log.employee_id,
                "uploadedBy": log.employee_name,
                "supervisorName": log.supervisor_name,
                "shiftIncharge": log.shift_incharge,
                "status": log.status,
                "totalFopParts": log.total_fop_parts,
                "totalFopRejections": log.total_fop_rejections,
                "createdAt": log.created_at.isoformat() if log.created_at else None,
                "updatedAt": log.updated_at.isoformat() if log.updated_at else None
            })

        return {
            "status": "success",
            "pagination": {
                "totalCount": total_records,
                "page": page,
                "limit": limit,
                "totalPages": (total_records + limit - 1) // limit if total_records > 0 else 1
            },
            "count": len(result_list),
            "data": result_list
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Form 2 records: {str(e)}"
        )


# ============================================================================
# 4. Get Form 2 by ID Endpoint (Detailed Nested Document)
# GET /api/v1/forms/form2/{id}
# ============================================================================
@router.get(
    "/{id}",
    summary="Get Detailed Form 2 Record by ID",
    response_model=dict
)
def get_form2_by_id(
    id: int = Path(..., description="Unique ID of the Form 2 record"),
    db: Session = Depends(get_db)
):
    """
    Retrieves the complete nested document with header metadata, 16 itemized tool records,
    5-Why problem analysis, and PDI inspection matrix.
    """
    log = db.query(Form2HandoverLog).filter(Form2HandoverLog.id == id).first()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form 2 record with ID {id} was not found."
        )

    # Unpack Tool rows
    tool_data = []
    for t in log.tool_records:
        tool_data.append({
            "id": t.id,
            "rowIndex": t.row_index,
            "toolDescription": t.tool_description,
            "operationNo": t.operation_no,
            "machineNo": t.machine_no,
            "toolNo": t.tool_no,
            "time": t.time_stamp,
            "reasonForFOP": t.reason_for_fop,
            "fopParts": t.fop_parts,
            "fopRejection": t.fop_rejection,
            "toolSetBy": t.tool_set_by,
            "handoverCheck": t.handover_check,
            "defect": t.defect,
            "remarks": t.remarks,
            "materialOrTool": t.material_or_tool
        })

    # Unpack PDI rows
    pdi_data = []
    for p in log.pdi_records:
        pdi_data.append({
            "id": p.id,
            "rowIndex": p.row_index,
            "rowLabel": p.row_label,
            "operationNo": p.operation_no,
            "machiningRejection": p.machining_rejection,
            "castingRejection": p.casting_rejection,
            "supplierInfo": p.supplier_info,
            "dieCavityNo": p.die_cavity_no,
            "abnormalityAlarm": p.abnormality_alarm
        })

    return {
        "status": "success",
        "data": {
            "id": log.id,
            "formCode": log.form_code,
            "pageType": log.page_type,
            "formTitle": log.form_title,
            "date": log.log_date,
            "shift": log.shift,
            "machineNo": log.machine_no,
            "qaCell": log.qa_cell,
            "operationNo": log.operation_no,
            "employeeId": log.employee_id,
            "uploadedBy": log.employee_name,
            "supervisorName": log.supervisor_name,
            "shiftIncharge": log.shift_incharge,
            "status": log.status,
            "imagePath": log.original_image_path,
            "totalFopParts": log.total_fop_parts,
            "totalFopRejections": log.total_fop_rejections,
            "createdAt": log.created_at.isoformat() if log.created_at else None,
            "updatedAt": log.updated_at.isoformat() if log.updated_at else None,
            
            # Tool Records (16 rows)
            "records": tool_data,
            
            # 5-Why & Shift Handover Details
            "details": {
                "problemAnalysis": log.problem_analysis,
                "why1": log.why_1,
                "why2": log.why_2,
                "why3": log.why_3,
                "why4": log.why_4,
                "why5": log.why_5,
                "rootCause": log.root_cause,
                "action": log.action_1,
                "action1": log.action_1,
                "action2": log.action_2,
                "handoverCheck": log.handover_check,
                "rmOnLineQty": log.rm_online_qty,
                "runningCavity": log.running_cavity,
                "allGaugesOnline": log.all_gauges_online,
                "missingGauges": log.missing_gauges,
                "pdiReportPvNo": log.pdi_report_pv_no,
                "toolInLineNo": log.tool_in_line_no,
                "shiftCommunication": log.shift_communication,
                "materialToolCommunication": log.material_tool_communication,
                "supervisor": log.supervisor_name,
                "preparedByEmployeeNo": log.prepared_by_emp_no
            },
            
            # PDI Inspection & Defect Matrix
            "pdiInspection": pdi_data
        }
    }


# ============================================================================
# 5. Update / Edit Form 2 Record Endpoint
# PUT /api/v1/forms/form2/{id}
# ============================================================================
@router.put(
    "/{id}",
    summary="Update Existing Form 2 Record",
    response_model=dict
)
def update_form2_record(
    id: int = Path(..., description="ID of the Form 2 record to update"),
    payload: Form2SubmitPayload = ...,
    db: Session = Depends(get_db)
):
    """
    Updates an existing Form 2 record and replaces its child tool and PDI rows with the updated set.
    """
    log = db.query(Form2HandoverLog).filter(Form2HandoverLog.id == id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form 2 record with ID {id} not found."
        )

    try:
        header = payload.header
        details = payload.details
        records = payload.records
        pdi_list = payload.pdiInspection

        # Update Master Log Fields
        if header.log_date or header.date:
            log.log_date = header.log_date or header.date
        if header.shift:
            log.shift = header.shift
        if header.machine_no or header.machineNo:
            log.machine_no = header.machine_no or header.machineNo
        if header.qa_cell or header.qaCell:
            log.qa_cell = header.qa_cell or header.qaCell
        if header.operation_no or header.operationNo:
            log.operation_no = header.operation_no or header.operationNo
        if header.supervisor_name or details.supervisor:
            log.supervisor_name = header.supervisor_name or details.supervisor
        if header.shift_incharge:
            log.shift_incharge = header.shift_incharge

        # Update 5-Why
        log.problem_analysis = details.problemAnalysis or log.problem_analysis
        log.why_1 = details.why1 or log.why_1
        log.why_2 = details.why2 or log.why_2
        log.why_3 = details.why3 or log.why_3
        log.why_4 = details.why4 or log.why_4
        log.why_5 = details.why5 or log.why_5
        log.root_cause = details.rootCause or log.root_cause
        log.action_1 = details.action1 or details.action or log.action_1
        log.action_2 = details.action2 or log.action_2
        log.shift_communication = details.shiftCommunication or log.shift_communication
        
        # Calculate totals
        if records:
            log.total_fop_parts = sum(int(r.fopParts or 0) for r in records)
            log.total_fop_rejections = sum(int(r.fopRejection or 0) for r in records)

            # Clear and replace tool records
            db.query(Form2ToolRecord).filter(Form2ToolRecord.form2_id == log.id).delete()
            for idx, r in enumerate(records):
                db.add(Form2ToolRecord(
                    form2_id=log.id,
                    row_index=r.rowIndex if r.rowIndex is not None else idx,
                    tool_description=r.toolDescription or "",
                    operation_no=r.operationNo or "",
                    machine_no=r.machineNo or log.machine_no,
                    tool_no=r.toolNo or "",
                    time_stamp=r.time or "",
                    reason_for_fop=r.reasonForFOP or "",
                    fop_parts=int(r.fopParts or 0),
                    fop_rejection=int(r.fopRejection or 0),
                    tool_set_by=r.toolSetBy or "",
                    handover_check=r.handoverCheck or "",
                    defect=r.defect or "",
                    remarks=r.remarks or "",
                    material_or_tool=r.materialOrTool or ""
                ))

        if pdi_list:
            db.query(Form2PDIInspectionRecord).filter(Form2PDIInspectionRecord.form2_id == log.id).delete()
            for idx, p in enumerate(pdi_list):
                db.add(Form2PDIInspectionRecord(
                    form2_id=log.id,
                    row_index=p.rowIndex if p.rowIndex is not None else idx,
                    row_label=p.rowLabel or f"Row {idx + 1}",
                    operation_no=p.operationNo or "",
                    machining_rejection=int(p.machiningRejection or 0),
                    casting_rejection=int(p.castingRejection or 0),
                    supplier_info=p.supplierInfo or "",
                    die_cavity_no=p.dieCavityNo or "",
                    abnormality_alarm=p.abnormalityAlarm or ""
                ))

        log.updated_at = datetime.utcnow()
        db.commit()

        return {
            "status": "success",
            "message": f"Form 2 record #{id} updated successfully.",
            "formId": id
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update Form 2: {str(e)}"
        )


# ============================================================================
# 6. Delete Form 2 Record Endpoint
# DELETE /api/v1/forms/form2/{id}
# ============================================================================
@router.delete(
    "/{id}",
    summary="Delete Form 2 Record",
    response_model=dict
)
def delete_form2_record(
    id: int = Path(..., description="ID of the Form 2 record to delete"),
    db: Session = Depends(get_db)
):
    """
    Deletes the Form 2 record and all associated child tool and PDI rows via cascading deletion.
    """
    log = db.query(Form2HandoverLog).filter(Form2HandoverLog.id == id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form 2 record with ID {id} not found."
        )

    try:
        db.delete(log)
        db.commit()
        return {
            "status": "success",
            "message": f"Form 2 record #{id} ({log.form_code}) deleted successfully."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete Form 2 record: {str(e)}"
        )
