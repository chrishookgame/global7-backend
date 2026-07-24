"""
Router de órdenes: crear una compra y procesar el pago con Mercado Pago.

Flujo:
1. POST /orders/  -> crea la orden en estado "pendiente" y devuelve una
   URL de checkout de Mercado Pago a la que el frontend redirige al comprador.
2. El comprador paga en la página de Mercado Pago.
3. Mercado Pago llama a POST /orders/webhook/mercadopago para avisar
   que hay un pago nuevo. Ahí (y solo ahí, tras confirmar el estado
   real con la API) la orden pasa a "pagado".
"""
from typing import List
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Order, Product, User
from app.models.schemas import (
    OrderCreate,
    OrderOut,
    OrderConDetalle,
    CheckoutResponse,
    OrderEstadoUpdate,
    PaypalCheckoutResponse,
)
from app.services.payment_service import crear_preferencia_pago, obtener_pago
from app.services.paypal_service import crear_orden_paypal, capturar_orden_paypal

router = APIRouter()

# Porcentaje de comisión de la plataforma sobre cada venta. Configurable
# por variable de entorno sin tener que tocar código.
COMISION_PORCENTAJE = float(os.getenv("COMISION_PORCENTAJE", "8"))  # 8% por defecto


@router.post("/", response_model=CheckoutResponse, status_code=201)
def crear_orden(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == order_in.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if product.stock < order_in.cantidad:
        raise HTTPException(status_code=400, detail="Stock insuficiente")

    total = product.precio * order_in.cantidad
    order = Order(
        buyer_id=current_user.id,
        product_id=product.id,
        cantidad=order_in.cantidad,
        total=total,
        estado="pendiente",
    )
    # El stock se descuenta recién cuando el pago se confirma (ver
    # webhook abajo), para no restar stock de compras que nunca se pagan.
    db.add(order)
    db.commit()
    db.refresh(order)

    checkout_url = crear_preferencia_pago(order.id, product.titulo, order.cantidad, product.precio)
    return CheckoutResponse(checkout_url=checkout_url)


@router.post("/paypal", response_model=PaypalCheckoutResponse, status_code=201)
def crear_orden_con_paypal(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea una orden y la sesión de pago con PayPal. El precio se
    muestra en pesos en el sitio, pero PayPal cobra en dólares (no
    acepta CLP), así que se convierte automáticamente al tipo de
    cambio del día antes de crear la orden."""
    product = db.query(Product).filter(Product.id == order_in.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if product.stock < order_in.cantidad:
        raise HTTPException(status_code=400, detail="Stock insuficiente")

    total = product.precio * order_in.cantidad
    order = Order(
        buyer_id=current_user.id,
        product_id=product.id,
        cantidad=order_in.cantidad,
        total=total,
        estado="pendiente",
        metodo_pago="paypal",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    try:
        resultado = crear_orden_paypal(order.id, product.titulo, total)
    except Exception as e:
        import traceback

        print(f"ERROR AL CREAR ORDEN PAYPAL: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=502, detail="No se pudo conectar con PayPal. Intenta de nuevo en un momento.")

    order.paypal_order_id = resultado["paypal_order_id"]
    db.commit()

    return PaypalCheckoutResponse(approve_url=resultado["approve_url"], monto_usd=resultado["monto_usd"])


@router.post("/paypal/capturar", response_model=OrderOut)
def capturar_pago_paypal(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Se llama cuando el comprador vuelve a nuestro sitio después de
    aprobar el pago en PayPal. Confirma el pago de verdad ante PayPal
    antes de marcar la orden como pagada — nunca confiamos solo en que
    el comprador haya vuelto a esta página."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="No eres el comprador de esta orden")
    if not order.paypal_order_id:
        raise HTTPException(status_code=400, detail="Esta orden no tiene un pago de PayPal asociado")

    if order.estado == "pendiente":
        try:
            resultado = capturar_orden_paypal(order.paypal_order_id)
        except Exception:
            raise HTTPException(status_code=502, detail="No se pudo confirmar el pago con PayPal")

        if resultado.get("status") == "COMPLETED":
            order.estado = "pagado"
            order.comision_plataforma = round(order.total * COMISION_PORCENTAJE / 100, 2)
            order.monto_vendedor = round(order.total - order.comision_plataforma, 2)
            product = db.query(Product).filter(Product.id == order.product_id).first()
            if product:
                product.stock = max(0, product.stock - order.cantidad)
            db.commit()
            db.refresh(order)

    return order


@router.post("/webhook/mercadopago", include_in_schema=False)
async def mercadopago_webhook(request: Request, db: Session = Depends(get_db)):
    """Mercado Pago llama aquí cuando hay novedades en un pago. Nunca lo
    llama el frontend directamente, y nunca confiamos en el estado que
    venga en la notificación: siempre lo verificamos consultando la API."""
    body = await request.json()
    payment_id = body.get("data", {}).get("id") or request.query_params.get("id")

    if not payment_id:
        return {"received": True}  # Notificación que no es de un pago; se ignora

    try:
        pago = obtener_pago(payment_id)
    except Exception:
        return {"received": True}

    order_id = pago.get("external_reference")
    estado_pago = pago.get("status")  # "approved", "pending", "rejected", etc.

    if order_id and estado_pago == "approved":
        order = db.query(Order).filter(Order.id == order_id).first()
        if order and order.estado == "pendiente":
            order.estado = "pagado"
            order.comision_plataforma = round(order.total * COMISION_PORCENTAJE / 100, 2)
            order.monto_vendedor = round(order.total - order.comision_plataforma, 2)
            product = db.query(Product).filter(Product.id == order.product_id).first()
            if product:
                product.stock = max(0, product.stock - order.cantidad)
            db.commit()

    return {"received": True}


@router.get("/{order_id}", response_model=OrderOut)
def obtener_orden(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Usado por la página 'pago exitoso' del frontend para confirmar el estado."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta orden")
    return order


@router.get("/me/todas", response_model=List[OrderOut])
def mis_ordenes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Order).filter(Order.buyer_id == current_user.id).all()


@router.get("/vendedor/recibidas", response_model=List[OrderConDetalle])
def ordenes_recibidas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Órdenes de productos que este usuario vendió (panel de vendedor)."""
    filas = (
        db.query(Order, Product.titulo, User.email)
        .join(Product, Order.product_id == Product.id)
        .join(User, Order.buyer_id == User.id)
        .filter(Product.seller_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [
        OrderConDetalle(
            id=order.id,
            buyer_id=order.buyer_id,
            product_id=order.product_id,
            cantidad=order.cantidad,
            total=order.total,
            monto_vendedor=order.monto_vendedor,
            estado=order.estado,
            producto_titulo=titulo,
            comprador_email=email,
        )
        for order, titulo, email in filas
    ]


@router.patch("/{order_id}/estado", response_model=OrderOut)
def actualizar_estado_orden(
    order_id: str,
    cambio: OrderEstadoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """El vendedor marca una orden como 'enviado'. La confirmación de
    'entregado' la hace el comprador (ver /confirmar-recepcion), no el
    vendedor, para que el pago se retenga hasta que el comprador
    confirme que de verdad recibió el producto."""
    if cambio.estado != "enviado":
        raise HTTPException(status_code=400, detail="El vendedor solo puede marcar 'enviado'")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    product = db.query(Product).filter(Product.id == order.product_id).first()
    if not product or product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="No eres el vendedor de este producto")

    if order.estado != "pagado":
        raise HTTPException(status_code=400, detail="Solo se puede marcar como enviada una orden ya pagada")

    order.estado = "enviado"
    db.commit()
    db.refresh(order)
    return order


@router.patch("/{order_id}/confirmar-recepcion", response_model=OrderOut)
def confirmar_recepcion(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """El COMPRADOR confirma que recibió el producto. Solo después de
    esto la orden queda lista para que el administrador transfiera el
    dinero al vendedor — el pago se retiene hasta este momento."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="No eres el comprador de esta orden")
    if order.estado != "enviado":
        raise HTTPException(status_code=400, detail="Solo puedes confirmar una orden que ya fue marcada como enviada")

    order.estado = "entregado"
    db.commit()
    db.refresh(order)
    return order

