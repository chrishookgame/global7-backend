"""
Conexión a la base de datos PostgreSQL.

Usa la variable de entorno DATABASE_URL, por ejemplo:
    postgresql://usuario:password@localhost:5432/global7

Recomendación para arrancar sin pagar servidor: crea una base gratuita en
Supabase (https://supabase.com) o Neon (https://neon.tech) y pega la URL
de conexión en tu archivo .env
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/global7",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: entrega una sesión de base de datos por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
