import jwt
import os
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends , HTTPException ,status
from sqlalchemy.orm import Session
from database.db import get_db



SECRET_KEY= os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

oauth2_schema = OAuth2PasswordBearer(tokenUrl='/api/login')

def get_current_user(token: str = Depends(oauth2_schema) , db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials / Token invalid",
        headers={'WWW-Authentication':"Bearer"},
    )