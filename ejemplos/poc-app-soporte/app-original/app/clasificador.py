"""Clasifica los tickets de soporte por tema (modelo propio publicado en Hugging Face)."""
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

modelo = AutoModelForSequenceClassification.from_pretrained("org/clasificador-tickets")
tokenizer = AutoTokenizer.from_pretrained("org/clasificador-tickets")
pesos_extra = torch.load("pesos_extra.pt")


def clasificar(texto):
    entradas = tokenizer(texto, return_tensors="pt")
    return modelo(**entradas).logits.argmax().item()
