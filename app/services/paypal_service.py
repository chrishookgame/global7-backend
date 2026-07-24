"""
Servicio de pagos con PayPal.

Por qué existe este archivo separado de payment_service.py: PayPal no
acepta pagos en pesos chilenos (CLP) — solo trabaja con un conjunto
fijo de ~25 monedas, sin incluir CLP. Por eso, cuando alguien paga con
PayPal, convertimos el precio a dólares (USD) automáticamente usando el
tipo de cambio del día, antes de crear la orden en PayPal.

Flujo (parecido al de Mercado Pago, pero con "aprobar" y "capturar"
como dos pasos separados, que es como funciona la API de PayPal):
1. Se pide un token de acceso a PayPal (OAuth2, credenciales de la app).
2. Se crea una "orden" en PayPal con el monto ya convertido a USD.
3. Se redirige al comprador a la URL de aprobación de PayPal.
4. El comprador aprueba el pago en PayPal y vuelve a nuestro sitio.
5. Nuestro backend "captura" el pago (lo confirma de verdad) y recién
   ahí se marca la orden como pagada.
"""
import os
import httpx

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
# "sandbox" mientras pruebas, "live" cuando cobres de verdad
PAYPAL_MODO = os.getenv("PAYPAL_MODO", "sandbox")
PAYPAL_API_BASE = (
    "https://api-m.sandbox.paypal.com" if PAYPAL_MODO == "sandbox" else "https://api-m.paypal.com"
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def obtener_tasa_cambio_clp_a_usd() -> float:
    """Consulta cuántos pesos chilenos equivalen a 1 dólar, usando una
    API pública y gratuita de tipos de cambio. Si falla por cualquier
    razón, usa un valor de respaldo aproximado para no romper la compra."""
    try:
        resp = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=8)
        resp.raise_for_status()
        data = resp.json()
        return float(data["rates"]["CLP"])
    except Exception:
        return 950.0  # valor de respaldo aproximado si la API externa falla


def convertir_clp_a_usd(monto_clp: float) -> float:
    tasa = obtener_tasa_cambio_clp_a_usd()
    return round(monto_clp / tasa, 2)


def _obtener_token_acceso() -> str:
    resp = httpx.post(
        f"{PAYPAL_API_BASE}/v1/oauth2/token",
        auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def crear_orden_paypal(order_id: str, titulo_producto: str, monto_clp: float) -> dict:
    """Crea la orden en PayPal y devuelve la URL de aprobación junto con
    el monto en dólares que se le va a cobrar al comprador."""
    monto_usd = convertir_clp_a_usd(monto_clp)
    token = _obtener_token_acceso()

    resp = httpx.post(
        f"{PAYPAL_API_BASE}/v2/checkout/orders",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": order_id,
                    "description": titulo_producto[:127],
                    "amount": {"currency_code": "USD", "value": f"{monto_usd:.2f}"},
                }
            ],
            "application_context": {
                "return_url": f"{FRONTEND_URL}/pago-exitoso-paypal?order_id={order_id}",
                "cancel_url": f"{FRONTEND_URL}/productos/{order_id}",
                "user_action": "PAY_NOW",
            },
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    approve_url = next(link["href"] for link in data["links"] if link["rel"] == "approve")
    return {"paypal_order_id": data["id"], "approve_url": approve_url, "monto_usd": monto_usd}


def capturar_orden_paypal(paypal_order_id: str) -> dict:
    """Confirma el pago de verdad ante PayPal. Se llama cuando el
    comprador vuelve a nuestro sitio tras aprobar el pago."""
    token = _obtener_token_acceso()
    resp = httpx.post(
        f"{PAYPAL_API_BASE}/v2/checkout/orders/{paypal_order_id}/capture",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
