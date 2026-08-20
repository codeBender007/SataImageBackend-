from database.db import Base
from sqlalchemy import Column , String , DateTime
from  datetime import datetime



class User(Base):
    __tablename__ = "users"

    # employee_id is the Primary Key
    employee_id = Column(String, primary_key=True, index=True)
    
    full_name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    
    role = Column(String, nullable=False, default="employee")  # "admin" / "employee"
    designation = Column(String, nullable=True)
    department = Column(String, nullable=True)
    status = Column(String, default="Active")
    created_at = Column(DateTime, default=datetime.utcnow)