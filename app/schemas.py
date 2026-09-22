from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

RoleLiteral = Literal["participant", "speaker", "admin"]
AbstractStatusLiteral = Literal["pending", "approved", "rejected"]
InvitationStatusLiteral = Literal["sent", "accepted", "declined"]
FeeStatusLiteral = Literal["unpaid", "paid"]
HotelStatusLiteral = Literal["requested", "confirmed", "cancelled"]


# ==================== AUTH ====================
class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: RoleLiteral = "participant"
    consent_152fz: bool

    @field_validator("consent_152fz")
    @classmethod
    def must_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Необходимо согласие на обработку персональных данных (152-ФЗ)")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну букву и одну цифру")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: EmailStr
    role: RoleLiteral
    is_online: bool
    consent_given: bool
    consent_date: Optional[datetime]
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=200)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ==================== CONFERENCES ====================
class ConferenceCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=5000)
    location: str = Field(default="", max_length=200)
    start_date: datetime
    end_date: datetime
    registration_deadline: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date <= self.start_date:
            raise ValueError("Дата окончания конференции должна быть позже даты начала")
        if self.registration_deadline and self.registration_deadline > self.end_date:
            raise ValueError("Дата окончания регистрации не может быть позже окончания конференции")
        return self


class ConferenceUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    location: Optional[str] = Field(default=None, max_length=200)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None


class ConferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    location: str
    start_date: datetime
    end_date: datetime
    registration_deadline: Optional[datetime]
    created_by: Optional[int]
    created_at: datetime


# ==================== REGISTRATIONS ====================
class RegistrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conference_id: int
    participant_id: int
    status: str
    registered_at: datetime


# ==================== ABSTRACTS ====================
class AbstractCreate(BaseModel):
    conference_id: int
    title: str = Field(min_length=3, max_length=300)
    content: str = Field(min_length=10, max_length=20000)
    duration_minutes: int = Field(gt=0, le=600, description="Длительность доклада в минутах (строго больше 0)")


class AbstractUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=300)
    content: Optional[str] = Field(default=None, min_length=10, max_length=20000)
    duration_minutes: Optional[int] = Field(default=None, gt=0, le=600)


class AbstractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conference_id: int
    author_id: int
    title: str
    content: str
    duration_minutes: int
    status: str
    submitted_at: datetime


# ==================== RATINGS ====================
class RatingCreate(BaseModel):
    score: int = Field(ge=1, le=5, description="Оценка от 1 до 5")
    review: Optional[str] = Field(default=None, max_length=2000)


class RatingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    abstract_id: int
    user_id: int
    score: int
    review: Optional[str]
    created_at: datetime


# ==================== INVITATIONS ====================
class InvitationCreate(BaseModel):
    conference_id: int
    participant_id: int


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conference_id: int
    participant_id: int
    status: str
    sent_at: datetime


class InvitationStatusUpdate(BaseModel):
    status: InvitationStatusLiteral


# ==================== FEES ====================
class FeeCreate(BaseModel):
    conference_id: int
    participant_id: Optional[int] = None
    amount: float = Field(gt=0)


class FeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conference_id: int
    participant_id: int
    amount: float
    status: str
    paid_at: Optional[datetime]


# ==================== HOTELS ====================
class HotelCreate(BaseModel):
    conference_id: int
    check_in: date
    check_out: date

    @model_validator(mode="after")
    def validate_dates(self):
        # По ТЗ (Рис 8): дата заезда не может быть в прошлом
        if self.check_in < date.today():
            raise ValueError("Дата заезда не может быть в прошлом. Укажите будущую дату.")
        # По ТЗ: выезд строго позже заезда
        if self.check_out <= self.check_in:
            raise ValueError("Дата выезда должна быть строго позже даты заезда")
        return self


class HotelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conference_id: int
    participant_id: int
    check_in: date
    check_out: date
    status: str
    created_at: datetime


class HotelStatusUpdate(BaseModel):
    status: HotelStatusLiteral


# ==================== MAILINGS ====================
class MailingCreate(BaseModel):
    conference_id: int
    participant_id: Optional[int] = None
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20000)


class MailingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conference_id: int
    participant_id: int
    subject: str
    body: str
    status: str
    sent_at: Optional[datetime]