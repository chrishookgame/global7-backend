"""
Router de administración. Todos los endpoints aquí requieren que el
usuario tenga es_admin=1 (ver app.core.deps.get_current_admin).

Para convertir tu propia cuenta en administrador, ejecuta en la base de
datos (Supabase → SQL Editor):
    UPDATE users SET es_admin = 1 WHERE email = 'tu-email@aqui.com';
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.models.models import User, Product, Order
from app.models.schemas import (
    AdminUserOut,
    AdminProductOut,
    AdminOrderOut,
    AdminResumen,
    AdminUserUpdate,
    AdminProductUpdate,
    AdminOrderUpdate,
)

router = APIRouter()


# ---------- Control total sobre usuarios ----------
@router.patch("/usuarios/{user_id}", response_model=AdminUserOut)
def editar_usuario(
    user_id: str,
    cambios: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """El admin puede editar cualquier usuario: nombre, email, si es
    vendedor, e incluso otorgar/quitar permisos de administrador."""
    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    datos = cambios.dict(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(usuario, campo, valor)

    db.commit()
    db.refresh(usuario)
    return usuario


@router.delete("/usuarios/{user_id}", status_code=204)
def eliminar_usuario(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Elimina una cuenta de usuario permanentemente. No se puede eliminar
    tu propia cuenta de administrador, ni una cuenta que ya tenga
    productos u órdenes (rompería el historial) — en esos casos,
    suspende el acceso editando la cuenta en vez de eliminarla."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta de administrador")

    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    tiene_productos = db.query(Product).filter(Product.seller_id == user_id).first()
    tiene_ordenes = db.query(Order).filter(Order.buyer_id == user_id).first()
    if tiene_productos or tiene_ordenes:
        raise HTTPException(
            status_code=400,
            detail="Este usuario ya tiene productos u órdenes asociadas y no se puede eliminar sin perder ese historial. Puedes editarlo para revocar sus permisos en su lugar.",
        )

    db.delete(usuario)
    db.commit()
    return None


# ---------- Control total sobre productos ----------
@router.patch("/productos/{product_id}", response_model=AdminProductOut)
def editar_producto_admin(
    product_id: str,
    cambios: AdminProductUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """El admin puede editar cualquier producto de cualquier vendedor
    (por ejemplo, para moderar contenido inapropiado)."""
    producto = db.query(Product).filter(Product.id == product_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    datos = cambios.dict(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(producto, campo, valor)

    db.commit()
    db.refresh(producto)

    vendedor = db.query(User).filter(User.id == producto.seller_id).first()
    return AdminProductOut(
        id=producto.id,
        titulo=producto.titulo,
        precio=producto.precio,
        stock=producto.stock,
        categoria=producto.categoria,
        vendedor_email=vendedor.email if vendedor else "?",
    )


@router.delete("/productos/{product_id}", status_code=204)
def eliminar_producto_admin(
    product_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """El admin puede eliminar cualquier producto sin órdenes asociadas.
    Si ya tiene compras, no se puede borrar (rompería el historial
    financiero) — en ese caso, edítalo (por ejemplo, stock en 0) en vez
    de eliminarlo."""
    producto = db.query(Product).filter(Product.id == product_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    tiene_ordenes = db.query(Order).filter(Order.product_id == product_id).first()
    if tiene_ordenes:
        raise HTTPException(
            status_code=400,
            detail="Este producto ya tiene órdenes asociadas y no se puede eliminar sin perder ese historial. Puedes editarlo y poner el stock en 0 en su lugar.",
        )

    db.delete(producto)
    db.commit()
    return None


# ---------- Control total sobre órdenes ----------
@router.patch("/ordenes/{order_id}", response_model=AdminOrderOut)
def editar_orden_admin(
    order_id: str,
    cambios: AdminOrderUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """El admin puede corregir manualmente el estado o los montos de
    cualquier orden — por ejemplo, para resolver una disputa o corregir
    un error de cálculo."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    datos = cambios.dict(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(order, campo, valor)

    db.commit()
    db.refresh(order)

    producto = db.query(Product).filter(Product.id == order.product_id).first()
    vendedor = db.query(User).filter(User.id == producto.seller_id).first() if producto else None
    comprador = db.query(User).filter(User.id == order.buyer_id).first()

    return AdminOrderOut(
        id=order.id,
        producto_titulo=producto.titulo if producto else "?",
        comprador_email=comprador.email if comprador else "?",
        vendedor_email=vendedor.email if vendedor else "?",
        total=order.total,
        comision_plataforma=order.comision_plataforma,
        monto_vendedor=order.monto_vendedor,
        estado=order.estado,
        metodo_pago=order.metodo_pago,
        transferido_vendedor=order.transferido_vendedor,
        vendedor_banco_nombre=vendedor.banco_nombre if vendedor else None,
        vendedor_banco_tipo_cuenta=vendedor.banco_tipo_cuenta if vendedor else None,
        vendedor_banco_numero_cuenta=vendedor.banco_numero_cuenta if vendedor else None,
        vendedor_banco_rut=vendedor.banco_rut if vendedor else None,
        vendedor_banco_titular=vendedor.banco_titular if vendedor else None,
    )


@router.patch("/ordenes/{order_id}/marcar-transferido", response_model=AdminOrderOut)
def marcar_transferido(
    order_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Marca que ya transferiste manualmente el dinero al vendedor. Solo
    se puede marcar sobre órdenes que el comprador ya confirmó como
    'entregado' — así el dinero se retiene hasta que el comprador
    confirme la recepción."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if order.estado != "entregado":
        raise HTTPException(
            status_code=400,
            detail="Solo puedes marcar como transferido una orden que el comprador ya confirmó como entregada",
        )

    order.transferido_vendedor = 1
    db.commit()

    producto = db.query(Product).filter(Product.id == order.product_id).first()
    vendedor = db.query(User).filter(User.id == producto.seller_id).first()
    comprador = db.query(User).filter(User.id == order.buyer_id).first()

    return AdminOrderOut(
        id=order.id,
        producto_titulo=producto.titulo,
        comprador_email=comprador.email,
        vendedor_email=vendedor.email,
        total=order.total,
        comision_plataforma=order.comision_plataforma,
        monto_vendedor=order.monto_vendedor,
        estado=order.estado,
        metodo_pago=order.metodo_pago,
        transferido_vendedor=order.transferido_vendedor,
        vendedor_banco_nombre=vendedor.banco_nombre if vendedor else None,
        vendedor_banco_tipo_cuenta=vendedor.banco_tipo_cuenta if vendedor else None,
        vendedor_banco_numero_cuenta=vendedor.banco_numero_cuenta if vendedor else None,
        vendedor_banco_rut=vendedor.banco_rut if vendedor else None,
        vendedor_banco_titular=vendedor.banco_titular if vendedor else None,
    )


@router.get("/resumen", response_model=AdminResumen)
def resumen(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """Números generales de toda la plataforma, para el dashboard principal."""
    total_usuarios = db.query(User).count()
    total_productos = db.query(Product).count()
    ordenes_pagadas = db.query(Order).filter(Order.estado.in_(["pagado", "enviado", "entregado"])).all()
    total_vendido = sum(o.total for o in ordenes_pagadas)
    total_comision = sum(o.comision_plataforma for o in ordenes_pagadas)

    return AdminResumen(
        total_usuarios=total_usuarios,
        total_productos=total_productos,
        total_ordenes_pagadas=len(ordenes_pagadas),
        total_vendido=round(total_vendido, 2),
        total_comision_plataforma=round(total_comision, 2),
    )


@router.get("/usuarios", response_model=List[AdminUserOut])
def listar_usuarios(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.get("/productos", response_model=List[AdminProductOut])
def listar_productos(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    filas = (
        db.query(Product, User.email)
        .join(User, Product.seller_id == User.id)
        .order_by(Product.created_at.desc())
        .all()
    )
    return [
        AdminProductOut(
            id=p.id,
            titulo=p.titulo,
            precio=p.precio,
            stock=p.stock,
            categoria=p.categoria,
            vendedor_email=email,
        )
        for p, email in filas
    ]


@router.get("/ordenes", response_model=List[AdminOrderOut])
def listar_ordenes(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """Todas las órdenes de la plataforma, con comprador, vendedor y producto."""
    Comprador = User
    filas = (
        db.query(Order, Product.titulo, Comprador.email)
        .join(Product, Order.product_id == Product.id)
        .join(Comprador, Order.buyer_id == Comprador.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    resultado = []
    for order, titulo_producto, email_comprador in filas:
        vendedor = db.query(User).join(Product, Product.seller_id == User.id).filter(Product.id == order.product_id).first()
        resultado.append(
            AdminOrderOut(
                id=order.id,
                producto_titulo=titulo_producto,
                comprador_email=email_comprador,
                vendedor_email=vendedor.email if vendedor else "?",
                total=order.total,
                comision_plataforma=order.comision_plataforma,
                monto_vendedor=order.monto_vendedor,
                estado=order.estado,
                metodo_pago=order.metodo_pago,
                transferido_vendedor=order.transferido_vendedor,
                vendedor_banco_nombre=vendedor.banco_nombre if vendedor else None,
                vendedor_banco_tipo_cuenta=vendedor.banco_tipo_cuenta if vendedor else None,
                vendedor_banco_numero_cuenta=vendedor.banco_numero_cuenta if vendedor else None,
                vendedor_banco_rut=vendedor.banco_rut if vendedor else None,
                vendedor_banco_titular=vendedor.banco_titular if vendedor else None,
            )
        )
    return resultado
