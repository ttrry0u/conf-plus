from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api", tags=["Оргвзносы"])


@router.post("/fees", response_model=schemas.FeeOut, status_code=status.HTTP_201_CREATED)
def create_fee(
    payload: schemas.FeeCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    conf = db.get(models.Conference, payload.conference_id)
    if not conf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Конференция не найдена")

    target_id = payload.participant_id or user.id
    if user.role != "admin" and target_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")

    target = db.get(models.User, target_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")

    if payload.amount <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Сумма оргвзноса должна быть положительной")

    fee = models.Fee(
        conference_id=payload.conference_id,
        participant_id=target_id,
        amount=float(payload.amount),
        status="unpaid",
    )
    db.add(fee)
    db.commit()
    db.refresh(fee)
    return fee


@router.get("/fees/my", response_model=list[schemas.FeeOut])
def my_fees(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.Fee).filter_by(participant_id=user.id).order_by(models.Fee.id.desc()).all()


@router.get("/conferences/{conference_id}/fees", response_model=list[schemas.FeeOut])
def list_fees(
    conference_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    return db.query(models.Fee).filter_by(conference_id=conference_id).all()


@router.post("/fees/{fee_id}/pay", response_model=schemas.FeeOut)
def pay_fee(
    fee_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    fee = db.get(models.Fee, fee_id)
    if not fee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Оргвзнос не найден")
    if user.role != "admin" and fee.participant_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
    if fee.status == "paid":
        raise HTTPException(status.HTTP_409_CONFLICT, "Оргвзнос уже оплачен")

    fee.status = "paid"
    fee.paid_at = models.utcnow()
    db.commit()
    db.refresh(fee)
    return fee