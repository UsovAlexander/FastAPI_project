from pydantic import BaseModel, EmailStr, HttpUrl
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    username: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class LinkBase(BaseModel):
    original_url: str

class LinkCreate(LinkBase):
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None

class LinkUpdate(BaseModel):
    original_url: str

class LinkResponse(LinkBase):
    id: str
    short_code: str
    created_at: datetime
    expires_at: Optional[datetime]
    clicks: int
    owner_id: Optional[str]
    custom_alias: Optional[str]
    
    class Config:
        from_attributes = True

class LinkStats(LinkResponse):
    last_clicked_at: Optional[datetime]
    short_url: str

class Token(BaseModel):
    access_token: str
    token_type: str