"""
Router de Global AI. Cada endpoint es una "habilidad" que otros módulos
del ecosistema podrán reusar más adelante.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import AIInteraction, User
from app.models.schemas import GenerarDescripcionRequest, AIResponse
from app.services.ai_service import generar_descripcion_producto

router = APIRouter()


@router.post("/generar-descripcion", response_model=AIResponse)
def generar_descripcion(
    req: GenerarDescripcionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    respuesta = generar_descripcion_producto(req.titulo, req.categoria, req.detalles)

    # Guardamos cada interacción con la IA — útil para mejorar prompts después
    # y, más adelante, para que el usuario vea su historial.
    log = AIInteraction(
        user_id=current_user.id,
        tipo="generar_descripcion",
        prompt=f"{req.titulo} / {req.categoria} / {req.detalles}",
        respuesta=respuesta,
    )
    db.add(log)
    db.commit()

    return AIResponse(respuesta=respuesta)
