from datetime import datetime, timedelta   # <-- добавьте datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api/conferences", tags=["Конференции"])


@router.get("", response_model=list[schemas.ConferenceOut])
def list_conferences(db: Session = Depends(get_db)):
    return db.query(models.Conference).order_by(models.Conference.start_date.desc()).all()


@router.get("/{conference_id}", response_model=schemas.ConferenceOut)
def get_conference(conference_id: int, db: Session = Depends(get_db)):
    conf = db.get(models.Conference, conference_id)
    if not conf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Конференция не найдена")
    return conf


@router.post("", response_model=schemas.ConferenceOut, status_code=status.HTTP_201_CREATED)
def create_conference(
    payload: schemas.ConferenceCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_roles("admin")),
):
    conf = models.Conference(**payload.model_dump(), created_by=admin.id)
    db.add(conf)
    db.commit()
    db.refresh(conf)
    return conf


@router.patch("/{conference_id}", response_model=schemas.ConferenceOut)
def update_conference(
    conference_id: int,
    payload: schemas.ConferenceUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    conf = db.get(models.Conference, conference_id)
    if not conf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Конференция не найдена")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(conf, key, value)

    if conf.end_date <= conf.start_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Дата окончания конференции должна быть позже даты начала")
    if conf.registration_deadline and conf.registration_deadline > conf.end_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Дата окончания регистрации не может быть позже окончания конференции")

    db.commit()
    db.refresh(conf)
    return conf


@router.post("/{conference_id}/finish", response_model=schemas.ConferenceOut)
def finish_conference(
    conference_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    """Принудительное завершение конференции администратором."""
    conf = db.get(models.Conference, conference_id)
    if not conf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Конференция не найдена")

    # ИСПРАВЛЕНО: локальное время
    now = datetime.now()
    if conf.end_date <= now:
        raise HTTPException(status.HTTP_409_CONFLICT, "Конференция уже завершена")

    new_end = now - timedelta(seconds=1)
    if new_end <= conf.start_date:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Нельзя завершить конференцию до даты её начала",
        )
    conf.end_date = new_end

    if conf.registration_deadline and conf.registration_deadline > new_end:
        conf.registration_deadline = new_end

    db.commit()
    db.refresh(conf)
    return conf


@router.delete("/{conference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conference(
    conference_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    conf = db.get(models.Conference, conference_id)
    if not conf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Конференция не найдена")
    db.delete(conf)
    db.commit()