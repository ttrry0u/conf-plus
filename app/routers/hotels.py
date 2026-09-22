from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api", tags=["Гостиница"])

# Максимальное количество мест в гостинице
MAX_HOTEL_CAPACITY = 1000


def _active_bookings_count(db: Session, conference_id: int) -> int:
    """Считает занятые места: подтверждённые брони с датой выезда в будущем."""
    return (
        db.query(models.HotelBooking)
        .filter(
            models.HotelBooking.conference_id == conference_id,
            models.HotelBooking.status == "confirmed",
            models.HotelBooking.check_out >= date.today(),
        )
        .count()
    )


@router.post("/hotels", response_model=schemas.HotelOut, status_code=status.HTTP_201_CREATED)
def request_hotel(
    payload: schemas.HotelCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    conf = db.get(models.Conference, payload.conference_id)
    if not conf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Конференция не найдена")
    if payload.check_out <= payload.check_in:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Дата выезда должна быть позже даты заезда")

    booking = models.HotelBooking(
        conference_id=payload.conference_id,
        participant_id=user.id,
        check_in=payload.check_in,
        check_out=payload.check_out,
        status="requested",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/hotels/my", response_model=list[schemas.HotelOut])
def my_hotels(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return (
        db.query(models.HotelBooking)
        .filter_by(participant_id=user.id)
        .order_by(models.HotelBooking.id.desc())
        .all()
    )


@router.get("/hotels", response_model=list[schemas.HotelOut])
def list_all_hotels(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    """Все заявки на проживание (только для администратора)."""
    return db.query(models.HotelBooking).order_by(models.HotelBooking.id.desc()).all()


@router.get("/hotels/capacity")
def hotel_capacity(db: Session = Depends(get_db)):
    """Сводка по заполненности гостиницы (для отображения админу и участникам)."""
    confirmed = (
        db.query(models.HotelBooking)
        .filter(
            models.HotelBooking.status == "confirmed",
            models.HotelBooking.check_out >= date.today(),
        )
        .count()
    )
    return {
        "capacity": MAX_HOTEL_CAPACITY,
        "occupied": confirmed,
        "available": max(MAX_HOTEL_CAPACITY - confirmed, 0),
    }


@router.get("/conferences/{conference_id}/hotels", response_model=list[schemas.HotelOut])
def list_hotels(
    conference_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    return db.query(models.HotelBooking).filter_by(conference_id=conference_id).all()


@router.post("/hotels/{booking_id}/confirm", response_model=schemas.HotelOut)
def confirm_hotel(
    booking_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    """Подтверждение заявки на проживание администратором с проверкой лимита мест."""
    booking = db.get(models.HotelBooking, booking_id)
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Бронирование не найдено")
    if booking.status != "requested":
        raise HTTPException(status.HTTP_409_CONFLICT, "Заявка уже обработана")

    occupied = _active_bookings_count(db, booking.conference_id)
    if occupied >= MAX_HOTEL_CAPACITY:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Достигнут лимит мест в гостинице ({MAX_HOTEL_CAPACITY} человек)",
        )

    booking.status = "confirmed"
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/hotels/{booking_id}/checkout", response_model=schemas.HotelOut)
def checkout_hotel(
    booking_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    """Принудительное выселение из гостиницы (освобождает ячейку)."""
    booking = db.get(models.HotelBooking, booking_id)
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Бронирование не найдено")
    if booking.status != "confirmed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Можно выселить только подтверждённое бронирование")

    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking


@router.patch("/hotels/{booking_id}", response_model=schemas.HotelOut)
def update_hotel_status(
    booking_id: int,
    payload: schemas.HotelStatusUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    booking = db.get(models.HotelBooking, booking_id)
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Бронирование не найдено")
    if user.role != "admin" and booking.participant_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
    if user.role != "admin" and payload.status != "cancelled":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Участник может только отменить бронирование")
    booking.status = payload.status
    db.commit()
    db.refresh(booking)
    return booking


@router.delete("/hotels/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hotel(
    booking_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    booking = db.get(models.HotelBooking, booking_id)
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Бронирование не найдено")
    if user.role != "admin" and booking.participant_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
    db.delete(booking)
    db.commit()