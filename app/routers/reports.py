from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_roles

router = APIRouter(prefix="/api", tags=["Отчёты"])


@router.get("/conferences/{conference_id}/report")
def conference_report(
    conference_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    conf = db.get(models.Conference, conference_id)
    if not conf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Конференция не найдена")

    participants_count = db.query(func.count(models.Registration.id)).filter_by(conference_id=conference_id).scalar() or 0

    abstracts_q = db.query(models.Abstract).filter_by(conference_id=conference_id)
    abstracts_total = abstracts_q.count()
    abstracts_approved = abstracts_q.filter(models.Abstract.status == "approved").count()
    abstracts_pending = abstracts_q.filter(models.Abstract.status == "pending").count()
    abstracts_rejected = abstracts_q.filter(models.Abstract.status == "rejected").count()

    avg_score = (
        db.query(func.avg(models.Rating.score))
        .join(models.Abstract, models.Abstract.id == models.Rating.abstract_id)
        .filter(models.Abstract.conference_id == conference_id)
        .scalar()
    )
    ratings_count = (
        db.query(func.count(models.Rating.id))
        .join(models.Abstract, models.Abstract.id == models.Rating.abstract_id)
        .filter(models.Abstract.conference_id == conference_id)
        .scalar()
        or 0
    )

    fees_paid = db.query(func.count(models.Fee.id)).filter_by(conference_id=conference_id, status="paid").scalar() or 0
    fees_pending = db.query(func.count(models.Fee.id)).filter_by(conference_id=conference_id, status="pending").scalar() or 0
    fees_total_amount = (
        db.query(func.coalesce(func.sum(models.Fee.amount), 0.0))
        .filter_by(conference_id=conference_id, status="paid")
        .scalar()
    )

    hotel_requests = db.query(func.count(models.HotelBooking.id)).filter_by(conference_id=conference_id).scalar() or 0
    invitations_sent = db.query(func.count(models.Invitation.id)).filter_by(conference_id=conference_id).scalar() or 0
    mailings_sent = db.query(func.count(models.Mailing.id)).filter_by(conference_id=conference_id).scalar() or 0

    return {
        "conference": schemas.ConferenceOut.model_validate(conf).model_dump(),
        "participants_count": int(participants_count),
        "abstracts_total": int(abstracts_total),
        "abstracts_approved": int(abstracts_approved),
        "abstracts_pending": int(abstracts_pending),
        "abstracts_rejected": int(abstracts_rejected),
        "ratings_count": int(ratings_count),
        "average_score": round(float(avg_score), 2) if avg_score is not None else None,
        "fees_paid": int(fees_paid),
        "fees_pending": int(fees_pending),
        "fees_total_amount": float(fees_total_amount or 0.0),
        "hotel_requests": int(hotel_requests),
        "invitations_sent": int(invitations_sent),
        "mailings_sent": int(mailings_sent),
    }