from fastapi import FastAPI

from .agente import responder
from .clasificador import clasificar

app = FastAPI()


@app.post("/chat")
def chat(mensaje: str):
    return {"tema": clasificar(mensaje), "respuesta": responder(mensaje)}
