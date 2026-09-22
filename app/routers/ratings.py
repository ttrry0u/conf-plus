from datetime import datetime   # <-- добавьте это

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api", tags=["Оценки докладов"])


@router.post("/abstracts/{abstract_id}/ratings", response_model=schemas.RatingOut, status_code=status.HTTP_201_CREATED)
def rate_abstract(
    abstract_id: int,
    payload: schemas.RatingCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("participant", "speaker", "admin")),
):
    abstract = db.get(models.Abstract, abstract_id)
    if not abstract:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Доклад не найден")

    if abstract.author_id == user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Нельзя оценивать собственный доклад")

    conf = db.get(models.Conference, abstract.conference_id)
    if not conf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Конференция не найдена")

    # ИСПРАВЛЕНО: сравниваем локальное время с локальным
    if datetime.now() < conf.end_date:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Оценивать доклады можно только после завершения конференции",
        )

    if payload.score < 1 or payload.score > 5:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Оценка должна быть в диапазоне от 1 до 5")

    existing = (
        db.query(models.Rating)
        .filter_by(abstract_id=abstract_id, user_id=user.id)
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Вы уже оценивали этот доклад")

    rating = models.Rating(
        abstract_id=abstract_id,
        user_id=user.id,
        score=payload.score,
        review=(payload.review or "").strip() or None,
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)
    return rating


@router.get("/abstracts/{abstract_id}/ratings", response_model=list[schemas.RatingOut])
def list_ratings(abstract_id: int, db: Session = Depends(get_db)):
    abstract = db.get(models.Abstract, abstract_id)
    if not abstract:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Доклад не найден")
    return db.query(models.Rating).filter_by(abstract_id=abstract_id).all()


@router.get("/conferences/{conference_id}/ratings/summary")
def ratings_summary(conference_id: int, db: Session = Depends(get_db)):
    conf = db.get(models.Conference, conference_id)
    if not conf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Конференция не найдена")

    rows = (
        db.query(
            models.Abstract.id,
            models.Abstract.title,
            func.avg(models.Rating.score).label("avg_score"),
            func.count(models.Rating.id).label("cnt"),
        )
        .outerjoin(models.Rating, models.Rating.abstract_id == models.Abstract.id)
        .filter(models.Abstract.conference_id == conference_id)
        .group_by(models.Abstract.id, models.Abstract.title)
        .all()
    )
    return [
        {
            "abstract_id": r.id,
            "title": r.title,
            "average_score": round(float(r.avg_score), 2) if r.avg_score is not None else None,
            "ratings_count": int(r.cnt),
        }
        for r in rows
    ]