from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# 1. Tool / FOP Row Schema (Upper Table, 16 Rows)
class Form2ToolRecordSchema(BaseModel):
    id: Optional[int] = None
    rowIndex: Optional[int] = 0
    toolDescription: Optional[str] = ""
    operationNo: Optional[str] = ""
    machineNo: Optional[str] = ""
    toolNo: Optional[str] = ""
    time: Optional[str] = ""
    reasonForFOP: Optional[str] = ""
    fopParts: Optional[int] = 0
    fopRejection: Optional[int] = 0
    toolSetBy: Optional[str] = ""
    handoverCheck: Optional[str] = ""
    defect: Optional[str] = ""
    remarks: Optional[str] = ""
    materialOrTool: Optional[str] = ""


# 2. Shift Handover & 5-Why Analysis Details Schema
class Form2DetailsSchema(BaseModel):
    problemAnalysis: Optional[str] = ""
    why1: Optional[str] = ""
    why2: Optional[str] = ""
    why3: Optional[str] = ""
    why4: Optional[str] = ""
    why5: Optional[str] = ""
    rootCause: Optional[str] = ""
    action: Optional[str] = ""
    action1: Optional[str] = ""
    action2: Optional[str] = ""
    handoverCheck: Optional[str] = ""
    rmOnLineQty: Optional[str] = ""
    runningCavity: Optional[str] = ""
    allGaugesOnline: Optional[str] = "Y"
    missingGauges: Optional[str] = ""
    pdiReportPvNo: Optional[str] = ""
    toolInLineNo: Optional[str] = ""
    shiftCommunication: Optional[str] = ""
    materialToolCommunication: Optional[str] = ""
    supervisor: Optional[str] = ""
    preparedByEmployeeNo: Optional[str] = ""


# 3. PDI / Rework / Operation Matrix Schema (Lower Table)
class Form2PDISchema(BaseModel):
    id: Optional[int] = None
    rowIndex: Optional[int] = 0
    rowLabel: Optional[str] = ""
    operationNo: Optional[str] = ""
    machiningRejection: Optional[int] = 0
    castingRejection: Optional[int] = 0
    supplierInfo: Optional[str] = ""
    dieCavityNo: Optional[str] = ""
    abnormalityAlarm: Optional[str] = ""


# 4. Form Header Metadata Schema
class Form2HeaderSchema(BaseModel):
    page_type: Optional[str] = "Page B"
    form_title: Optional[str] = "First Operation Part (FOP) Record & Shift Handover"
    log_date: Optional[str] = None
    date: Optional[str] = None
    shift: Optional[str] = "A"
    machine_no: Optional[str] = None
    machineNo: Optional[str] = None
    qa_cell: Optional[str] = None
    qaCell: Optional[str] = None
    operation_no: Optional[str] = None
    operationNo: Optional[str] = None
    employee_id: Optional[str] = None
    employeeId: Optional[str] = None
    employee_name: Optional[str] = None
    uploadedBy: Optional[str] = None
    supervisor_name: Optional[str] = None
    shift_incharge: Optional[str] = None
    module_incharge: Optional[str] = None
    status: Optional[str] = "submitted"
    image_path: Optional[str] = ""


# 5. Submit / Save Payload Schema (sent by Frontend to POST /api/v1/forms/form2/submit)
class Form2SubmitPayload(BaseModel):
    header: Optional[Form2HeaderSchema] = Field(default_factory=Form2HeaderSchema)
    records: List[Form2ToolRecordSchema] = Field(default_factory=list)
    details: Optional[Form2DetailsSchema] = Field(default_factory=Form2DetailsSchema)
    pdiInspection: List[Form2PDISchema] = Field(default_factory=list)
    imagePath: Optional[str] = ""
    
    # Flat top-level convenience aliases (matches legacy frontend formats)
    date: Optional[str] = None
    shift: Optional[str] = None
    machineNo: Optional[str] = None
    uploadedBy: Optional[str] = None
    uploadedById: Optional[str] = None
    employeeId: Optional[str] = None


# 6. OCR Extracted Payload Schema for LLM Vision Engine
class Form2ExtractedData(BaseModel):
    header: Form2HeaderSchema
    records: List[Form2ToolRecordSchema]
    details: Form2DetailsSchema
    pdiInspection: List[Form2PDISchema]


# 7. OCR Preview Response Schema (returned by POST /api/v1/forms/form2/extract)
class Form2ExtractionResponse(BaseModel):
    status: str = "success"
    message: str = "Form 2 extracted successfully for verification."
    extractionConfidence: float = 0.95
    sourceImage: Optional[str] = None
    extractedAt: str
    data: Form2ExtractedData


# 8. List Item Summary Schema (returned in GET /api/v1/forms/form2)
class Form2ListItem(BaseModel):
    id: int
    formCode: str
    pageType: str
    formTitle: str
    date: str
    shift: str
    machineNo: Optional[str] = ""
    qaCell: Optional[str] = ""
    operationNo: Optional[str] = ""
    employeeId: Optional[str] = ""
    uploadedBy: Optional[str] = ""
    supervisorName: Optional[str] = ""
    shiftIncharge: Optional[str] = ""
    status: str
    totalFopParts: int
    totalFopRejections: int
    createdAt: datetime
    updatedAt: datetime


# 9. Full Nested Response Schema (returned in GET /api/v1/forms/form2/{id})
class Form2DetailResponse(BaseModel):
    id: int
    formCode: str
    pageType: str
    formTitle: str
    date: str
    shift: str
    machineNo: Optional[str] = ""
    qaCell: Optional[str] = ""
    operationNo: Optional[str] = ""
    employeeId: Optional[str] = ""
    uploadedBy: Optional[str] = ""
    supervisorName: Optional[str] = ""
    shiftIncharge: Optional[str] = ""
    status: str
    imagePath: Optional[str] = ""
    totalFopParts: int
    totalFopRejections: int
    createdAt: datetime
    updatedAt: datetime
    records: List[Form2ToolRecordSchema]
    details: Form2DetailsSchema
    pdiInspection: List[Form2PDISchema]
