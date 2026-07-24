"""
Servicio de pagos con Mercado Pago Checkout Pro.

Por qué Mercado Pago y no Stripe: Stripe no opera oficialmente en Chile
(en Sudamérica solo tiene soporte directo en Brasil). Mercado Pago sí
es nativo de Chile y del resto de Latinoamérica.

Flujo (equivalente al de Stripe Checkout, solo cambia el proveedor):
1. Se crea una "preferencia" de pago con el producto y el total.
2. Se redirige al comprador a la URL de pago de Mercado Pago (init_point).
3. Mercado Pago paga y notifica a nuestro webhook.
4. El webhook consulta el pago por su ID y, si está aprobado, confirma la orden.
"""
import os
import mercadopago

ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

sdk = mercadopago.SDK(ACCESS_TOKEN)


def crear_preferencia_pago(order_id: str, titulo_producto: str, cantidad: int, precio_unitario: float) -> str:
    """Crea una preferencia de pago y devuelve la URL de checkout."""
    preference_data = {
        "items": [
            {
                "title": titulo_producto,
                "quantity": cantidad,
                "unit_price": precio_unitario,
                "currency_id": "CLP",  # Cambia a tu moneda si no es Chile
            }
        ],
        "back_urls": {
            "success": f"{FRONTEND_URL}/pago-exitoso?order_id={order_id}",
            "failure": f"{FRONTEND_URL}/productos",
            "pending": f"{FRONTEND_URL}/pago-exitoso?order_id={order_id}",
        },
        "auto_return": "approved",
        "external_reference": order_id,
        "notification_url": f"{BACKEND_URL}/orders/webhook/mercadopago",
    }
    result = sdk.preference().create(preference_data)
    preference = result["response"]
    return preference["init_point"]


def obtener_pago(payment_id: str) -> dict:
    """Consulta el estado real de un pago directamente con Mercado Pago
    (nunca confiamos ciegamente en lo que dice la notificación del webhook)."""
    result = sdk.payment().get(payment_id)
    return result["response"]
