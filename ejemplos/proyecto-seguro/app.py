# Ejemplo de buenas prácticas: revisión fija, sin código remoto y llaves en variables de entorno.
import os

from transformers import AutoModel

API_KEY = os.environ["API_KEY"]

modelo = AutoModel.from_pretrained(
    "org/modelo-soporte",
    revision="a1b2c3d4e5f6",
    trust_remote_code=False,
    use_safetensors=True,
)
