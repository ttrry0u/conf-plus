from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Аутентификация и профиль"])


@router.post("/register", response_model=schemas.TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    """Регистрация пользователя. Пароль хранится только в виде bcrypt-хэша (152-ФЗ)."""
    email = payload.email.lower().strip()
    exists = db.query(models.User).filter(models.User.email == email).first()
    if exists:
        # По ТЗ (Рис 9): 400, а не 409
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Участник с таким email уже существует")

    now = models.utcnow()
    user = models.User(
        full_name=payload.full_name.strip(),
        email=email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        consent_given=True,
        consent_date=now,
        is_online=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.role)
    return schemas.TokenOut(access_token=token, user=schemas.UserOut.model_validate(user))


@router.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")

    user.is_online = True
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.role)
    return schemas.TokenOut(access_token=token, user=schemas.UserOut.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.is_online = False
    db.commit()


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=schemas.UserOut)
def update_me(
    payload: schemas.UserUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    db.commit()
    db.refresh(user)
    return user


@router.get("/me/data")
def export_my_data(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """152-ФЗ: право на доступ к своим персональным данным."""
    registrations = db.query(models.Registration).filter_by(participant_id=user.id).all()
    abstracts = db.query(models.Abstract).filter_by(author_id=user.id).all()
    ratings = db.query(models.Rating).filter_by(user_id=user.id).all()
    fees = db.query(models.Fee).filter_by(participant_id=user.id).all()
    hotels = db.query(models.HotelBooking).filter_by(participant_id=user.id).all()
    invitations = db.query(models.Invitation).filter_by(participant_id=user.id).all()
    return {
        "profile": schemas.UserOut.model_validate(user).model_dump(),
        "registrations": [schemas.RegistrationOut.model_validate(r).model_dump() for r in registrations],
        "abstracts": [schemas.AbstractOut.model_validate(a).model_dump() for a in abstracts],
        "ratings": [schemas.RatingOut.model_validate(r).model_dump() for r in ratings],
        "fees": [schemas.FeeOut.model_validate(f).model_dump() for f in fees],
        "hotels": [schemas.HotelOut.model_validate(h).model_dump() for h in hotels],
        "invitations": [schemas.InvitationOut.model_validate(i).model_dump() for i in invitations],
    }


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """152-ФЗ: право на удаление (забвение) персональных данных."""
    uid = user.id
    db.query(models.Rating).filter(models.Rating.user_id == uid).delete(synchronize_session=False)
    db.query(models.Abstract).filter(models.Abstract.author_id == uid).delete(synchronize_session=False)
    db.query(models.Registration).filter(models.Registration.participant_id == uid).delete(synchronize_session=False)
    db.query(models.Invitation).filter(models.Invitation.participant_id == uid).delete(synchronize_session=False)
    db.query(models.Fee).filter(models.Fee.participant_id == uid).delete(synchronize_session=False)
    db.query(models.HotelBooking).filter(models.HotelBooking.participant_id == uid).delete(synchronize_session=False)
    db.query(models.Mailing).filter(models.Mailing.participant_id == uid).delete(synchronize_session=False)
    db.delete(user)
    db.commit()