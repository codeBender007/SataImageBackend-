from pydantic import BaseModel
from typing import Optional


class jwtSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    token: Optional[str] = None
    role: str
    employee_id: str
    username: Optional[str] = None
    fullName: Optional[str] = None