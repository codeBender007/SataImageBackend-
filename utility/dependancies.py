import jwt
import os
from fastapi.security import OAuth2PasswordBearer , HTTPAuthorizationCredentials , HTTPBearer
from fastapi import Depends , HTTPException ,status
from sqlalchemy.orm import Session
from database.db import get_db
from models.userModels import User



SECRET_KEY= os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

# step1: fetch login token using this function
oauth2_schema = OAuth2PasswordBearer(tokenUrl='/api/login')
security = HTTPBearer()

# step2: Token decode and fetch current user 
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):

    token = credentials.credentials
    # we will create unaunthentication variable  
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials / Token invalid",
        headers={'WWW-Authentication':"Bearer"},
    )

    try :
        # decode token
        payload = jwt.decode(token , SECRET_KEY , ALGORITHM)

        # fetch usename from token
        username: str = payload.get('sub')

        # if username is not in token then give error 
        if username is None:
            raise credentials_exception

    # if get excepted error then still give this variable ok 
    except Exception:
        raise credentials_exception

    # username exist then find in db
    # in query function User is model so please import from model folder  
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise credentials_exception
    return user


# i create function which is check current user is admin or not 
def get_current_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access denied: Admin rights required'
        )
    return current_user

    