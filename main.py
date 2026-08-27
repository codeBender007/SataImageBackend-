# In FastAPI, the code works in such a way that before the API function's code executes, the function's parameters are executed. 
# If the parameters are also functions, then the parameter functions' code will execute first, and after that, the code inside the
# API function will execute.

from fastapi import FastAPI , Depends , HTTPException , status , File , UploadFile ,Query
from typing import Optional
from sqlalchemy.orm import Session
from models.userModels import User
from models.productionModels import ProductionLog , HourlyProductionEntry , TPMLossEntry
from database.db import engine , Base , get_db
import os
import base64
from pydantic import BaseModel
from schemas.loginSceham import LoginSchema
from schemas.formASchema import FormASaveSchema
from schemas.jwtSchema import jwtSchema
from schemas.userSchema import userSchema
from utility.auth import create_access_token
from utility.dependancies import get_current_admin , get_current_user
from passlib.context import CryptContext
from services.visionExtractor import run_vision_extractor

pwd_context = CryptContext(schemes=['bcrypt'] , deprecated='auto')

# automatic create all models when write this line of code ok
Base.metadata.create_all(bind=engine)

# pydantic models 
class LoginSchema(BaseModel):
    username: str
    password: str


app = FastAPI()

# base route
@app.get('/')
def firstApi():
    return {"message":"Welcome to FastAPI Backend!"}

@app.post("/item/{item_id}")
def secondApi(item_id: int , q: str = None):
    return {"item_id : ":item_id , "query : ":q}

@app.post('/api/login' , response_model=jwtSchema)
def login(request: LoginSchema , db: Session = Depends(get_db)):

    user = db.query(User).filter(User.username == request.username).first()

    if not user:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = 'Invalid Crediantials: User not found'
        )

    # missing a step which is hashedpassword to unhashedpassword then match ok 


    if not pwd_context.verify(request.password , user.password):
        raise HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail='Invalid Credentials: Password incorrect'
        )

    token = {
        'sub':user.username,
        'employee_id':user.employee_id,
        'role':user.role
    }

    jwt_token = create_access_token(data = token)

    return {
        'access_token':jwt_token,
        'token_type':'bearer',
        'role':user.role,
        'employee_id':user.employee_id
    }


# create user from admin
# execute parameter function code before execute api function code
@app.post('/api/createuser')
def createUser(request: userSchema , db: Session = Depends(get_db) , admin_user: User = Depends(get_current_admin)):


    # step1: check employeeId , email , username already exist are not in database
    exist_user = db.query(User).filter(
        (User.employee_id == request.employee_id) |
        (User.email == request.email)| 
        (User.username == request.username)
    ).first()

    if exist_user:
        if exist_user.employee_id == request.employee_id:
            msg = "Employee ID Already Exist."
        elif exist_user.email == request.email:
            msg = "Email Already Exist."
        else:
            msg = "Username Already Exist."

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
    # *****************************

    # step2: change password to hashedPassword 
    hashedPassword = pwd_context.hash(request.password)
    # *********************

    # step3: create new User model object then save object save in database 
    newUser = User(
        employee_id=request.employee_id,
        full_name=request.username,
        username=request.username,
        email=request.email,
        password=hashedPassword,
        role=request.role,
        designation=request.designation,
        department=request.department,
        status=request.status
    )
    # **************************


    # step4: give User object in add function paramter then commit and refresh 
    db.add(newUser)
    db.commit()
    db.refresh(newUser)

    return {
        "Message":"User Created Successfull.",
        "employee_id":newUser.employee_id,
        "username":newUser.username,
        'role':newUser.role
    }


@app.post('/api/production/extractimage')
async def extractFormData(file: UploadFile = File(...) , currentUser: User = Depends(get_current_user)):

    # step1: File type validation
    if file.content_type not in ['image/jpeg' , 'image/png' , 'image/jpg']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Only uplaod JPG/PNG Files.'
        )

    # step2: Read image content
    imageBytes = await file.read()
    try:
        # Hugging Face function execution
        extracted_json = run_vision_extractor(imageBytes, file.content_type)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hugging Face Extraction Error: {str(e)}"
        )

    return {
        "status": "success",
        "message": "Form extracted successfully via Hugging Face model.",
        "data": extracted_json
    }


@app.post("/api/form-a-save")
def saveFormA(
    request: FormASaveSchema, 
    db: Session = Depends(get_db), 
    currentUser: User = Depends(get_current_user)
):
    try:
        # Step 1: Parent Header Log
        parentLog = ProductionLog(
            logDate=request.log_date,
            shift=request.shift,
            opearationNumber=request.operation_number,
            machineNo=request.machine_no,
            qaCell=request.qa_cell,
            employeeNumber=request.employee_number or currentUser.employee_id,
            supervisorName=request.supervisor_name,
            shiftInchargeName=request.shift_incharge_name,
            pdiOkPart=request.pdi_ok_part1,
            pdiOkPart2=request.pdi_ok_part2,
            entryPersonName=request.entry_person_name or currentUser.full_name,
            abnormalityParts=request.abnormality_parts,
            otherAbnormality=request.other_abnormality,
            imagePath=request.image_path
        )

        db.add(parentLog)
        db.flush()

        # Step 2: Hourly Entries (request.production_grid use karein)
        hourlyRecords = []
        for entry in request.production_grid:
            hourlyItem = HourlyProductionEntry(
                production_log_id=parentLog.id,
                part_number=entry.part_number,
                hour_slot=entry.hour_slot,
                uph=entry.uph or 0,
                actual_production=entry.actual_production or 0,
                casting_rejection=entry.casting_rejection or 0,
                machining_rejection=entry.machining_rejection or 0,
                unprocessed_rejection=entry.unprocessed_rejection or 0
            )
            hourlyRecords.append(hourlyItem)

        if hourlyRecords:
            db.add_all(hourlyRecords)

        # Step 3: TPM Loss Entries (request.loss_entries use karein)
        tpm_records = []
        for tpm in request.loss_entries:
            tpm_item = TPMLossEntry(
                production_log_id=parentLog.id,
                loss_category=tpm.loss_category,
                loss_reason=tpm.loss_reason,
                hour_slot=tpm.hour_slot,
                duration_minutes=tpm.duration_minutes or 0
            )
            tpm_records.append(tpm_item)
            
        if tpm_records:
            db.add_all(tpm_records)

        # Step 4: Commit transaction
        db.commit()
        db.refresh(parentLog)

        return {
            "status": "success",
            "message": "Form A data saved successfully",
            "log_id": parentLog.id
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save Form A: {str(e)}"
        )


@app.get("/api/form-a/list")
def get_form_a_list(
    log_date: Optional[str] = Query(None, description="Filter by date (e.g. 13/06/26)"),
    shift: Optional[str] = Query(None, description="Filter by shift (e.g. A, B, C)"),
    machine_no: Optional[str] = Query(None, description="Filter by machine number"),
    operator_id: Optional[str] = Query(None, description="Filter by employee/operator ID"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to fetch"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Base query setup
        query = db.query(ProductionLog)

        # 1. Role-based check
        if current_user.role != "admin":
            # Normal employee sirf apne records dekhega
            query = query.filter(ProductionLog.employeeNumber == current_user.employee_id)
        elif operator_id:
            # Admin kisi specific employee/operator ke mutabiq filter kar sakta hai
            query = query.filter(ProductionLog.employeeNumber == operator_id)

        # 2. Optional Filters
        if log_date:
            query = query.filter(ProductionLog.logDate == log_date)

        if shift:
            query = query.filter(ProductionLog.shift == shift)

        if machine_no:
            query = query.filter(ProductionLog.machineNo.ilike(f"%{machine_no}%"))

        # Total count after filters (Pagination ke liye)
        total_records = query.count()

        # 3. Sorting & Pagination (Latest records pehle)
        logs = (
            query.order_by(ProductionLog.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        # 4. Response formatting
        result_list = []
        for item in logs:
            result_list.append({
                "id": item.id,
                "logDate": item.logDate,
                "shift": item.shift,
                "machineNo": item.machineNo,
                "qaCell": item.qaCell,
                "opearationNumber": item.opearationNumber,
                "employeeNumber": item.employeeNumber,
                "supervisorName": item.supervisorName,
                "shiftInchargeName": item.shiftInchargeName,
                "entryPersonName": item.entryPersonName,
                "pdiOkPart": item.pdiOkPart,
                "createdAt": item.createdAt
            })

        return {
            "status": "success",
            "total_count": total_records,
            "count": len(result_list),
            "data": result_list
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Form A list: {str(e)}"
        )

    