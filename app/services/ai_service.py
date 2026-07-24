"""
Global AI - capa de servicio de IA.

Diseño: cada "habilidad" es una función simple que arma un prompt y llama
a la API de Claude. Nuevos módulos (Jobs, Learn...) importan estas
funciones o agregan las suyas aquí mismo, sin duplicar la lógica de
conexión a la API.
"""
import os
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"


def _llamar_ia(prompt: str, system: str = "") -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def generar_descripcion_producto(titulo: str, categoria: str, detalles: str = "") -> str:
    """Habilidad: escribe una descripción de venta para un producto nuevo."""
    system = (
        "Eres un copywriter experto en e-commerce. Escribes descripciones de "
        "producto persuasivas, claras y breves (máximo 80 palabras), sin "
        "inventar características que el vendedor no mencionó."
    )
    prompt = (
        f"Título del producto: {titulo}\n"
        f"Categoría: {categoria}\n"
        f"Detalles proporcionados por el vendedor: {detalles or 'ninguno'}\n\n"
        "Escribe la descripción de venta."
    )
    return _llamar_ia(prompt, system)
