from pydantic import BaseModel
from dotenv import load_dotenv


load_dotenv()


class jwtSchema(BaseModel):
    access_token: str
    token_type: str
    role: str
    employee_id: str