from pydantic import BaseModel
from typing import Optional

class UserSchema(BaseModel):
    name : str
    email: str
    password: str
    role: Optional[str] = "commom"
    active: Optional[bool] = True

class Config: 
    from_attributes = True