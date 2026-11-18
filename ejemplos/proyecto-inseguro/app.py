# Ejemplo A PROPÓSITO inseguro. Las llaves de abajo son falsas.
import pickle

from transformers import AutoModel

OPENAI_API_KEY = "sk-test-0000000000000000000000000000"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"

modelo = AutoModel.from_pretrained("org/modelo-soporte", trust_remote_code=True)

with open("modelo.pkl", "rb") as f:
    estado = pickle.load(f)
