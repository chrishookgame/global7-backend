# Global 7 AI Ecosystem — Backend MVP

Backend real y funcional: usuarios + login, publicar productos con
imagen, crear órdenes con pago real vía Mercado Pago, y Global AI
generando descripciones de producto.

## Qué incluye

- Registro y login de usuarios (JWT) — base de "Global ID"
- Publicar y listar productos, con imagen (Cloudflare R2) — base del Marketplace
- Crear órdenes de compra **con pago real vía Mercado Pago**
- Generar descripción de producto con IA (Global AI)
- Panel de vendedor: productos propios y ventas recibidas

## Configurar Cloudflare R2 (almacenamiento de imágenes)

Las imágenes de producto se guardan en R2, no en el disco del servidor
— así sobreviven a cada redeploy en Railway/Render.

1. Crea una cuenta gratuita en https://dash.cloudflare.com/sign-up
2. En el menú lateral, ve a **R2 Object Storage** → "Create bucket"
   → nómbralo `global7-uploads`
3. Dentro del bucket, ve a **Settings** → **Public access** → habilita
   "Allow Access" y copia la URL pública (algo como `https://pub-xxxx.r2.dev`)
   → pégala en `R2_PUBLIC_URL`
4. Ve a **R2 → Manage R2 API Tokens** → "Create API Token" → permisos
   de "Object Read & Write" → copia el `Access Key ID` y el
   `Secret Access Key`
5. Tu `R2_ACCOUNT_ID` está en la URL del dashboard de Cloudflare
   (`dash.cloudflare.com/<ACCOUNT_ID>/r2`) o en la página de resumen de R2

## Configurar Mercado Pago (modo de pruebas, sin cargos reales)

Usamos Mercado Pago en vez de Stripe porque **Stripe no opera
oficialmente en Chile** (en Sudamérica solo tiene soporte directo en
Brasil). Mercado Pago sí es nativo de Chile.

1. Crea una cuenta en https://www.mercadopago.cl (o el sitio de tu país)
2. Ve a https://www.mercadopago.cl/developers/panel/app y crea una aplicación
3. En la pestaña **Credenciales de prueba**, copia el "Access Token" →
   pégalo en `MP_ACCESS_TOKEN` en tu `.env`
4. Para que Mercado Pago pueda avisarle a tu backend que un pago se
   completó (el webhook), tu backend necesita una URL pública. En tu
   computadora local no la tienes por defecto, así que usa **ngrok**:
   ```bash
   # Instala ngrok (https://ngrok.com/download) y luego:
   ngrok http 8000
   ```
   Te da una URL como `https://abc123.ngrok-free.app` — pégala en
   `BACKEND_URL` en tu `.env` y reinicia el servidor.
5. En el panel de pruebas de Mercado Pago, crea un **usuario de prueba
   comprador** (Credenciales de prueba → Usuarios de prueba) para poder
   pagar sin usar tu cuenta real.
6. Para pagar en modo de pruebas, Mercado Pago te muestra tarjetas de
   prueba directamente en su checkout — no necesitas buscarlas aparte.

**Importante:** sin `ngrok` corriendo (o sin una URL pública real en
producción), Mercado Pago no puede avisarle a tu backend que el pago se
completó, y la orden se quedará en estado "pendiente" para siempre
aunque el pago sí se haya procesado. En producción, `BACKEND_URL` pasa
a ser tu URL real de Railway — ahí ya no necesitas ngrok.

## Cómo correrlo en tu computadora

### 1. Requisitos
- Python 3.11 o superior
- Una base de datos PostgreSQL (local con Docker, o gratuita en [Supabase](https://supabase.com) / [Neon](https://neon.tech))

### 2. Instalar dependencias
```bash
cd backend
python -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
```bash
cp .env.example .env
```
Edita `.env` y completa todos los valores (base de datos, IA, R2, Mercado Pago).

### 4. Levantar la base de datos (si usas Docker)
```bash
docker compose up -d
```

### 5. Correr el servidor
```bash
uvicorn app.main:app --reload
```

Abre **http://localhost:8000/docs** — ahí tienes documentación
interactiva de la API, generada automáticamente, donde puedes probar
cada endpoint sin escribir código.

## Flujo de prueba rápido (en /docs)

1. `POST /users/register` — crea tu usuario
2. `POST /users/login` — obtén tu token (úsalo con el botón "Authorize" arriba a la derecha)
3. `POST /products/` — publica un producto
4. `POST /ai/generar-descripcion` — pide a la IA que escriba la descripción
5. `POST /orders/` — devuelve una `checkout_url` de Mercado Pago; ábrela y paga con el usuario de prueba
6. `GET /orders/{order_id}` — confirma que el estado cambió a "pagado" (tras unos segundos, cuando el webhook llega)

## Siguiente paso

Desplegar a producción — ver `DESPLIEGUE.md` en la raíz del proyecto.
