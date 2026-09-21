from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> datetime:
    """Единая точка получения текущего времени (UTC, naive — для совместимости с PostgreSQL TIMESTAMP)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------- Участники (Participant) ----------
class User(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    # роль: participant | speaker | admin
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="participant")
    is_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 152-ФЗ: явная фиксация согласия субъекта на обработку ПДн
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


# ---------- Конференции ----------
class Conference(Base):
    __tablename__ = "conferences"
    __table_args__ = (
        CheckConstraint("end_date > start_date", name="ck_conf_dates"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    location: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    registration_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


# ---------- Регистрации участников на конференцию ----------
class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("conference_id", "participant_id", name="uq_registration"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conference_id: Mapped[int] = mapped_column(ForeignKey("conferences.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="registered")
    registered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


# ---------- Тезисы / доклады ----------
class Abstract(Base):
    __tablename__ = "abstracts"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="ck_abstract_duration_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conference_id: Mapped[int] = mapped_column(ForeignKey("conferences.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


# ---------- Оценки докладов ----------
class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("abstract_id", "user_id", name="uq_rating_once"),
        CheckConstraint("score >= 1 AND score <= 5", name="ck_rating_score_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    abstract_id: Mapped[int] = mapped_column(ForeignKey("abstracts.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


# ---------- Приглашения ----------
class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conference_id: Mapped[int] = mapped_column(ForeignKey("conferences.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sent")  # sent | accepted | declined
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


# ---------- Оргвзносы ----------
class Fee(Base):
    __tablename__ = "fees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conference_id: Mapped[int] = mapped_column(ForeignKey("conferences.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # По ТЗ: unpaid | paid
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unpaid")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---------- Гостиница ----------
class HotelBooking(Base):
    __tablename__ = "hotel_bookings"
    __table_args__ = (
        CheckConstraint("check_out > check_in", name="ck_hotel_dates"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conference_id: Mapped[int] = mapped_column(ForeignKey("conferences.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    check_in: Mapped[datetime] = mapped_column(Date, nullable=False)
    check_out: Mapped[datetime] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="requested")  # requested | confirmed | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


# ---------- Рассылки ----------
class Mailing(Base):
    __tablename__ = "mailings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conference_id: Mapped[int] = mapped_column(ForeignKey("conferences.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # По ТЗ: sent | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sent")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=utcnow)