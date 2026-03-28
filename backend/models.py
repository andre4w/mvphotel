from pydantic import BaseModel, EmailStr
from typing import Optional


class HotelRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    website_url: Optional[str] = None


class HotelLogin(BaseModel):
    email: EmailStr
    password: str


class HotelUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    website_url: Optional[str] = None


class ChatMessage(BaseModel):
    hotel_token: str
    session_id: str
    message: str
    language: Optional[str] = "en"


class AnswerQuestion(BaseModel):
    answer: str


class Token(BaseModel):
    access_token: str
    token_type: str
