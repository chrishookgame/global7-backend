"""
Dependencias compartidas: obtener el usuario actual a partir del token JWT.
Cualquier módulo futuro (Jobs, Learn, Health...) puede reusar esta misma
función para saber "quién está haciendo esta petición".
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Exige que el usuario logueado sea administrador. Se usa en todos
    los endpoints del panel de administración."""
    if current_user.es_admin != 1:
        raise HTTPException(status_code=403, detail="Requiere permisos de administrador")
    return current_user
