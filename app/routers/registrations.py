from datetime import datetime   # <-- добавьте

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api", tags=["Регистрации на конференцию"])


@router.post("/conferences/{conference_id}/registrations", response_model=schemas.RegistrationOut, status_code=status.HTTP_201_CREATED)
def register_for_conference(
    conference_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    conf = db.get(models.Conference, conference_id)
    if not conf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Конференция не найдена")

    # ИСПРАВЛЕНО: локальное время
    now = datetime.now()
    deadline = conf.registration_deadline or conf.start_date
    if now > deadline:
        raise HTTPException(status.HTTP_409_CONFLICT, "Регистрация на конференцию уже закрыта")
    if now > conf.end_date:
        raise HTTPException(status.HTTP_409_CONFLICT, "Конференция уже завершена")

    existing = (
        db.query(models.Registration)
        .filter_by(conference_id=conference_id, participant_id=user.id)
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Вы уже зарегистрированы на эту конференцию")

    reg = models.Registration(conference_id=conference_id, participant_id=user.id)
    db.add(reg)
    db.commit()
    db.refresh(reg)
    return reg


@router.get("/conferences/{conference_id}/registrations", response_model=list[schemas.RegistrationOut])
def list_registrations(
    conference_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    conf = db.get(models.Conference, conference_id)
    if not conf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Конференция не найдена")

    q = db.query(models.Registration).filter_by(conference_id=conference_id)
    if user.role != "admin":
        q = q.filter(models.Registration.participant_id == user.id)
    return q.order_by(models.Registration.registered_at.desc()).all()


@router.get("/registrations/my", response_model=list[schemas.RegistrationOut])
def my_registrations(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return (
        db.query(models.Registration)
        .filter_by(participant_id=user.id)
        .order_by(models.Registration.registered_at.desc())
        .all()
    )


@router.delete("/registrations/{registration_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    reg = db.get(models.Registration, registration_id)
    if not reg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Регистрация не найдена")
    if user.role != "admin" and reg.participant_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
    db.delete(reg)
    db.commit()