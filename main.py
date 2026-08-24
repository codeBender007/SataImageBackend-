# In FastAPI, the code works in such a way that before the API function's code executes, the function's parameters are executed. 
# If the parameters are also functions, then the parameter functions' code will execute first, and after that, the code inside the
# API function will execute.

from fastapi import FastAPI , Depends , HTTPException , status
from sqlalchemy.orm import Session
from models.userModels import User
from database.db import engine , Base , get_db
import os
from pydantic import BaseModel
from schemas.loginSceham import LoginSchema
from schemas.jwtSchema import jwtSchema
from schemas.userSchema import userSchema
from utility.auth import create_access_token
from utility.dependancies import get_current_admin
from passlib.context import CryptContext

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