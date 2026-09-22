from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/api", tags=["Доклады (тезисы)"])


@router.post("/abstracts", response_model=schemas.AbstractOut, status_code=status.HTTP_201_CREATED)
def submit_abstract(
    payload: schemas.AbstractCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("speaker", "admin")),
):
    conf = db.get(models.Conference, payload.conference_id)
    if not conf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Конференция не найдена")

    if payload.duration_minutes <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Длительность доклада должна быть положительным числом")

    abstract = models.Abstract(
        conference_id=payload.conference_id,
        author_id=user.id,
        title=payload.title.strip(),
        content=payload.content.strip(),
        duration_minutes=payload.duration_minutes,
        status="pending",
    )
    db.add(abstract)
    db.commit()
    db.refresh(abstract)
    return abstract


@router.get("/conferences/{conference_id}/abstracts", response_model=list[schemas.AbstractOut])
def list_abstracts(conference_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Abstract)
        .filter_by(conference_id=conference_id)
        .order_by(models.Abstract.submitted_at.desc())
        .all()
    )


@router.get("/abstracts/my", response_model=list[schemas.AbstractOut])
def my_abstracts(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return (
        db.query(models.Abstract)
        .filter_by(author_id=user.id)
        .order_by(models.Abstract.submitted_at.desc())
        .all()
    )


@router.get("/abstracts/{abstract_id}", response_model=schemas.AbstractOut)
def get_abstract(abstract_id: int, db: Session = Depends(get_db)):
    abstract = db.get(models.Abstract, abstract_id)
    if not abstract:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Доклад не найден")
    return abstract


@router.patch("/abstracts/{abstract_id}", response_model=schemas.AbstractOut)
def update_abstract(
    abstract_id: int,
    payload: schemas.AbstractUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    abstract = db.get(models.Abstract, abstract_id)
    if not abstract:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Доклад не найден")

    if user.role != "admin" and abstract.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")

    # Правило: изменение возможно только до утверждения администратором
    if abstract.status != "pending" and user.role != "admin":
        raise HTTPException(status.HTTP_409_CONFLICT, "Нельзя изменять доклад после утверждения/отклонения")

    data = payload.model_dump(exclude_unset=True)
    if "duration_minutes" in data and data["duration_minutes"] <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Длительность доклада должна быть положительным числом")

    for key, value in data.items():
        setattr(abstract, key, value)

    db.commit()
    db.refresh(abstract)
    return abstract


@router.post("/abstracts/{abstract_id}/approve", response_model=schemas.AbstractOut)
def approve_abstract(
    abstract_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    abstract = db.get(models.Abstract, abstract_id)
    if not abstract:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Доклад не найден")
    if abstract.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "Доклад уже обработан")
    abstract.status = "approved"
    db.commit()
    db.refresh(abstract)
    return abstract


@router.post("/abstracts/{abstract_id}/reject", response_model=schemas.AbstractOut)
def reject_abstract(
    abstract_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    abstract = db.get(models.Abstract, abstract_id)
    if not abstract:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Доклад не найден")
    if abstract.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "Доклад уже обработан")
    abstract.status = "rejected"
    db.commit()
    db.refresh(abstract)
    return abstract


@router.delete("/abstracts/{abstract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_abstract(
    abstract_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    abstract = db.get(models.Abstract, abstract_id)
    if not abstract:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Доклад не найден")
    if user.role != "admin" and abstract.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
    db.query(models.Rating).filter(models.Rating.abstract_id == abstract_id).delete(synchronize_session=False)
    db.delete(abstract)
    db.commit()