"""
Router de productos: el corazón del Marketplace (Fase 1, Módulo 1).
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Product, User, Order
from app.models.schemas import ProductCreate, ProductOut, ProductUpdate
from app.services.storage_service import subir_imagen as subir_imagen_r2

router = APIRouter()


@router.post("/", response_model=ProductOut, status_code=201)
def crear_producto(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cualquier usuario logueado puede publicar un producto (se vuelve vendedor)."""
    product = Product(seller_id=current_user.id, **product_in.dict())
    db.add(product)
    db.commit()
    db.refresh(product)

    if current_user.es_vendedor == 0:
        current_user.es_vendedor = 1
        db.commit()

    return product


@router.get("/", response_model=List[ProductOut])
def listar_productos(
    categoria: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Lista pública de productos, con filtro opcional por categoría."""
    query = db.query(Product)
    if categoria:
        query = query.filter(Product.categoria == categoria)
    return query.order_by(Product.created_at.desc()).all()


@router.post("/{product_id}/imagen", response_model=ProductOut)
def subir_imagen(
    product_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sube una imagen para un producto propio a Cloudflare R2.
    Reemplaza la imagen anterior si existía (la anterior queda huérfana
    en R2; limpiarla automáticamente es una mejora futura, no crítica)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="No eres el dueño de este producto")

    contents = file.file.read()
    try:
        url = subir_imagen_r2(contents, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    product.imagen_url = url
    db.commit()
    db.refresh(product)
    return product


@router.get("/mios/todos", response_model=List[ProductOut])
def mis_productos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Productos publicados por el usuario logueado (panel de vendedor)."""
    return (
        db.query(Product)
        .filter(Product.seller_id == current_user.id)
        .order_by(Product.created_at.desc())
        .all()
    )


@router.get("/{product_id}", response_model=ProductOut)
def obtener_producto(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def editar_producto(
    product_id: str,
    cambios: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edita un producto propio. Solo actualiza los campos que se envíen."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="No eres el dueño de este producto")

    datos = cambios.dict(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(product, campo, valor)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
def eliminar_producto(
    product_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina un producto propio (solo si nadie lo ha comprado)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="No eres el dueño de este producto")

    tiene_ordenes = db.query(Order).filter(Order.product_id == product_id).first()
    if tiene_ordenes:
        raise HTTPException(
            status_code=400,
            detail="No puedes eliminar un producto que ya tiene compras. Puedes poner el stock en 0 en su lugar.",
        )

    db.delete(product)
    db.commit()
    return None
