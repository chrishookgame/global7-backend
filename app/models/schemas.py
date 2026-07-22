"""
Esquemas Pydantic: definen la forma de los datos que entran y salen de la API.
"""
from pydantic import BaseModel, EmailStr


# ---------- Users ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    nombre: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    nombre: str
    es_vendedor: int
    es_admin: int
    banco_nombre: str | None = None
    banco_tipo_cuenta: str | None = None
    banco_numero_cuenta: str | None = None
    banco_rut: str | None = None
    banco_titular: str | None = None

    class Config:
        from_attributes = True


class DatosBancariosUpdate(BaseModel):
    banco_nombre: str
    banco_tipo_cuenta: str
    banco_numero_cuenta: str
    banco_rut: str
    banco_titular: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Products ----------
class ProductCreate(BaseModel):
    titulo: str
    descripcion: str = ""
    precio: float
    categoria: str = "general"
    stock: int = 1


class ProductOut(BaseModel):
    id: str
    seller_id: str
    titulo: str
    descripcion: str
    precio: float
    categoria: str
    stock: int
    imagen_url: str | None = None

    class Config:
        from_attributes = True


class ProductUpdate(BaseModel):
    titulo: str | None = None
    descripcion: str | None = None
    precio: float | None = None
    categoria: str | None = None
    stock: int | None = None


# ---------- Orders ----------
class OrderCreate(BaseModel):
    product_id: str
    cantidad: int = 1


class OrderOut(BaseModel):
    id: str
    buyer_id: str
    product_id: str
    cantidad: int
    total: float
    estado: str

    class Config:
        from_attributes = True


class OrderConDetalle(BaseModel):
    id: str
    buyer_id: str
    product_id: str
    cantidad: int
    total: float
    monto_vendedor: float
    estado: str
    producto_titulo: str
    comprador_email: str | None = None


class CheckoutResponse(BaseModel):
    checkout_url: str


class PaypalCheckoutResponse(BaseModel):
    approve_url: str
    monto_usd: float


class OrderEstadoUpdate(BaseModel):
    estado: str  # "enviado" o "entregado"


# ---------- Admin ----------
class AdminUserOut(BaseModel):
    id: str
    email: str
    nombre: str
    es_vendedor: int
    es_admin: int

    class Config:
        from_attributes = True


class AdminProductOut(BaseModel):
    id: str
    titulo: str
    precio: float
    stock: int
    categoria: str
    vendedor_email: str


class AdminOrderOut(BaseModel):
    id: str
    producto_titulo: str
    comprador_email: str
    vendedor_email: str
    total: float
    comision_plataforma: float
    monto_vendedor: float
    estado: str
    metodo_pago: str = "mercadopago"
    transferido_vendedor: int = 0
    vendedor_banco_nombre: str | None = None
    vendedor_banco_tipo_cuenta: str | None = None
    vendedor_banco_numero_cuenta: str | None = None
    vendedor_banco_rut: str | None = None
    vendedor_banco_titular: str | None = None


class AdminResumen(BaseModel):
    total_usuarios: int
    total_productos: int
    total_ordenes_pagadas: int
    total_vendido: float
    total_comision_plataforma: float


class AdminUserUpdate(BaseModel):
    nombre: str | None = None
    email: str | None = None
    es_vendedor: int | None = None
    es_admin: int | None = None


class AdminProductUpdate(BaseModel):
    titulo: str | None = None
    descripcion: str | None = None
    precio: float | None = None
    categoria: str | None = None
    stock: int | None = None


class AdminOrderUpdate(BaseModel):
    estado: str | None = None
    comision_plataforma: float | None = None
    monto_vendedor: float | None = None
    transferido_vendedor: int | None = None


# ---------- AI ----------
class GenerarDescripcionRequest(BaseModel):
    titulo: str
    categoria: str = "general"
    detalles: str = ""


class AIResponse(BaseModel):
    respuesta: str
