"""Clasifica los tickets de soporte por tema (modelo propio publicado en Hugging Face)."""
from transformers import AutoModelForSequenceClassification, AutoTokenizer

REVISION = "9f1c2ab"  # commit exacto del modelo revisado por seguridad

modelo = AutoModelForSequenceClassification.from_pretrained(
    "org/clasificador-tickets", revision=REVISION, use_safetensors=True, trust_remote_code=False)
tokenizer = AutoTokenizer.from_pretrained("org/clasificador-tickets", revision=REVISION)


def clasificar(texto):
    entradas = tokenizer(texto, return_tensors="pt")
    return modelo(**entradas).logits.argmax().item()
