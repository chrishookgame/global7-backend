"""
Global 7 AI Ecosystem - Backend MVP
Punto de entrada de la aplicación FastAPI.

Para correr localmente:
    uvicorn app.main:app --reload
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.routers import users, products, orders, ai, admin

# Crea las tablas en la base de datos si no existen (para desarrollo).
# En producción se recomienda usar migraciones (Alembic) en vez de esto.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Global 7 AI Ecosystem - API",
    description="Backend del MVP: Marketplace + Global AI",
    version="0.1.0",
)

# CORS: en desarrollo permite todo; en producción, restringe al dominio
# real del frontend seteando ALLOWED_ORIGINS (separado por comas) en
# las variables de entorno del backend.
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cada módulo (users, products, orders, ai) es un "servicio interno".
# El día que uno de estos crezca mucho, se puede separar en su propio
# backend sin tocar los demás.
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(products.router, prefix="/products", tags=["Marketplace"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(ai.router, prefix="/ai", tags=["Global AI"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.get("/")
def health_check():
    """Endpoint simple para confirmar que el servidor está vivo."""
    return {"status": "ok", "service": "Global 7 AI Ecosystem API"}
