from fastapi import FastAPI , Depends , HTTPException , status
from sqlalchemy.orm import Session
from models.userModels import User
from database.db import engine , Base , get_db
import os
from pydantic import BaseModel
from schemas.loginSceham import LoginSchema
from schemas.jwtSchema import jwtSchema
from schemas.userSchema import user
from utility.auth import create_access_token

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

    if user.password != request.password:
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
@app.post('/api/createuser' , response_model=jwtSchema)
def createUser(request: user ):
    r=0
