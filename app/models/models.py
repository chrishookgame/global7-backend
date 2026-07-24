"""
Modelos de base de datos (SQLAlchemy).

Este es el esquema base descrito en el documento de arquitectura:
users, products, orders, order_items, ai_interactions.
Diseñado para que módulos futuros (Jobs, Learn, Health) puedan
referenciar users.id sin duplicar el sistema de identidad.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    es_vendedor = Column(Integer, default=0)  # 0 = no, 1 = sí
    es_admin = Column(Integer, default=0)  # 0 = no, 1 = sí
    # Datos bancarios del vendedor, para que el admin sepa a qué cuenta
    # transferirle su parte de cada venta.
    banco_nombre = Column(String, nullable=True)
    banco_tipo_cuenta = Column(String, nullable=True)
    banco_numero_cuenta = Column(String, nullable=True)
    banco_rut = Column(String, nullable=True)
    banco_titular = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="seller")


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    seller_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    titulo = Column(String, nullable=False)
    descripcion = Column(Text, default="")
    precio = Column(Float, nullable=False)
    categoria = Column(String, default="general")
    stock = Column(Integer, default=1)
    imagen_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    seller = relationship("User", back_populates="products")


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    buyer_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    product_id = Column(UUID(as_uuid=False), ForeignKey("products.id"), nullable=False)
    cantidad = Column(Integer, default=1)
    total = Column(Float, nullable=False)
    comision_plataforma = Column(Float, default=0)  # lo que te corresponde a ti
    monto_vendedor = Column(Float, default=0)  # lo que le corresponde transferir al vendedor
    estado = Column(String, default="pendiente")  # pendiente, pendiente_confirmacion, pagado, enviado, entregado
    metodo_pago = Column(String, default="mercadopago")  # mercadopago, paypal
    paypal_order_id = Column(String, nullable=True)
    transferido_vendedor = Column(Integer, default=0)  # 0 = fondos retenidos, 1 = ya transferido
    created_at = Column(DateTime, default=datetime.utcnow)


class AIInteraction(Base):
    __tablename__ = "ai_interactions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    tipo = Column(String, nullable=False)  # ej: "generar_descripcion"
    prompt = Column(Text, nullable=False)
    respuesta = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
