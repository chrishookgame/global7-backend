"""
Router de usuarios: registro, login.
Esta es la semilla del futuro "Global ID" (Fase 14 del plan original) —
un solo sistema de identidad que todos los módulos reutilizan.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user
from app.models.models import User
from app.models.schemas import UserCreate, UserOut, Token, DatosBancariosUpdate

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")

    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        nombre=user_in.nombre,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    token = create_access_token({"sub": user.id})
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me/banco", response_model=UserOut)
def actualizar_datos_bancarios(
    datos: DatosBancariosUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """El vendedor registra sus propios datos bancarios, para que el
    administrador sepa a qué cuenta transferirle su parte de cada venta."""
    current_user.banco_nombre = datos.banco_nombre
    current_user.banco_tipo_cuenta = datos.banco_tipo_cuenta
    current_user.banco_numero_cuenta = datos.banco_numero_cuenta
    current_user.banco_rut = datos.banco_rut
    current_user.banco_titular = datos.banco_titular
    db.commit()
    db.refresh(current_user)
    return current_user
