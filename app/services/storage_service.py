"""
Servicio de almacenamiento de archivos. Sube imágenes a Cloudflare R2,
que es compatible con la API de S3, así que usamos boto3 (el cliente
oficial de AWS) apuntando a los servidores de Cloudflare en vez de a AWS.

Por qué R2 en vez de guardar en el disco del servidor: en Railway/Render
el disco se borra en cada redeploy. R2 es almacenamiento persistente,
separado del servidor, y tiene un tier gratuito generoso (10 GB).
"""
import os
import uuid

import boto3
from botocore.client import Config

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "global7-uploads")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")  # ej: https://pub-xxxx.r2.dev

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _cliente_r2():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def subir_imagen(contenido: bytes, nombre_original: str) -> str:
    """Sube una imagen a R2 y devuelve su URL pública."""
    ext = os.path.splitext(nombre_original or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato de imagen no permitido (usa jpg, png o webp)")
    if len(contenido) > MAX_FILE_SIZE:
        raise ValueError("La imagen no puede superar 5 MB")

    key = f"products/{uuid.uuid4()}{ext}"
    content_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }[ext]

    cliente = _cliente_r2()
    cliente.put_object(
        Bucket=R2_BUCKET_NAME,
        Key=key,
        Body=contenido,
        ContentType=content_type,
    )

    return f"{R2_PUBLIC_URL}/{key}"
