from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api", tags=["Рассылки"])


@router.post("/mailings", response_model=list[schemas.MailingOut], status_code=status.HTTP_201_CREATED)
def create_mailing(
    payload: schemas.MailingCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    conf = db.get(models.Conference, payload.conference_id)
    if not conf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Конференция не найдена")

    if payload.participant_id is not None:
        targets = [payload.participant_id]
    else:
        targets = [
            r.participant_id
            for r in db.query(models.Registration).filter_by(conference_id=payload.conference_id).all()
        ]
        if not targets:
            raise HTTPException(status.HTTP_409_CONFLICT, "Нет зарегистрированных участников для рассылки")

    created = []
    now = models.utcnow()
    for pid in targets:
        m = models.Mailing(
            conference_id=payload.conference_id,
            participant_id=pid,
            subject=payload.subject.strip(),
            body=payload.body.strip(),
            status="sent",
            sent_at=now,
        )
        db.add(m)
        created.append(m)

    db.commit()
    for m in created:
        db.refresh(m)
    return created


@router.get("/mailings/my", response_model=list[schemas.MailingOut])
def my_mailings(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return (
        db.query(models.Mailing)
        .filter_by(participant_id=user.id)
        .order_by(models.Mailing.id.desc())
        .all()
    )


@router.get("/conferences/{conference_id}/mailings", response_model=list[schemas.MailingOut])
def list_mailings(
    conference_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    return db.query(models.Mailing).filter_by(conference_id=conference_id).all()