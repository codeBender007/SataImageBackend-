from pydantic import BaseModel


class userSchema(BaseModel):
    employee_id: str
    full_name: str
    username: str
    email: str
    password: str
    role: str
    designation: str
    department: str
    status: str