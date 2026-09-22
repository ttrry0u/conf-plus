from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api", tags=["Приглашения"])


@router.post("/invitations", response_model=schemas.InvitationOut, status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: schemas.InvitationCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    conf = db.get(models.Conference, payload.conference_id)
    if not conf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Конференция не найдена")
    user = db.get(models.User, payload.participant_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")

    invitation = models.Invitation(conference_id=payload.conference_id, participant_id=payload.participant_id)
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.get("/invitations/my", response_model=list[schemas.InvitationOut])
def my_invitations(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return (
        db.query(models.Invitation)
        .filter_by(participant_id=user.id)
        .order_by(models.Invitation.sent_at.desc())
        .all()
    )


@router.get("/conferences/{conference_id}/invitations", response_model=list[schemas.InvitationOut])
def list_invitations(
    conference_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    return db.query(models.Invitation).filter_by(conference_id=conference_id).all()


@router.patch("/invitations/{invitation_id}", response_model=schemas.InvitationOut)
def update_invitation(
    invitation_id: int,
    payload: schemas.InvitationStatusUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    inv = db.get(models.Invitation, invitation_id)
    if not inv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Приглашение не найдено")
    if user.role != "admin" and inv.participant_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
    inv.status = payload.status
    db.commit()
    db.refresh(inv)
    return inv