"""Agente de soporte al cliente de ACME (ejemplo realista y simplificado)."""
import json

import chromadb
from openai import OpenAI

from .config import OPENAI_API_KEY

cliente = OpenAI(api_key=OPENAI_API_KEY)
coleccion = chromadb.PersistentClient(path="./kb").get_or_create_collection("base_conocimiento")

SISTEMA = "Eres el agente de soporte de ACME. Ayuda al cliente con sus pedidos y resuelve su problema."

TOOLS = [
    {"type": "function", "function": {"name": "buscar_en_base_conocimiento", "description": "Busca en la base de conocimiento",
                                      "parameters": {"type": "object", "properties": {"consulta": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "consultar_pedido", "description": "Consulta el estado de un pedido",
                                      "parameters": {"type": "object", "properties": {"id_pedido": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "enviar_correo_cliente", "description": "Envía un correo al cliente",
                                      "parameters": {"type": "object", "properties": {"correo": {"type": "string"}, "texto": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "reembolsar_pedido", "description": "Reembolsa un pedido",
                                      "parameters": {"type": "object", "properties": {"id_pedido": {"type": "string"}, "monto": {"type": "number"}}}}},
]


def buscar_en_base_conocimiento(consulta):
    return coleccion.query(query_texts=[consulta], n_results=3)["documents"]


def consultar_pedido(id_pedido):
    return {"id": id_pedido, "estado": "en camino"}


def enviar_correo_cliente(correo, texto):
    print(f"Enviando correo a {correo}")
    return "enviado"


def reembolsar_pedido(id_pedido, monto):
    print(f"Reembolsando {monto} del pedido {id_pedido}")
    return "reembolsado"


def responder(mensaje_usuario):
    mensajes = [{"role": "system", "content": SISTEMA}, {"role": "user", "content": mensaje_usuario}]
    while True:
        r = cliente.chat.completions.create(model="gpt-4o-mini", messages=mensajes, tools=TOOLS)
        msg = r.choices[0].message
        mensajes.append(msg)
        if not msg.tool_calls:
            return msg.content
        for llamada in msg.tool_calls:
            funcion = globals()[llamada.function.name]
            resultado = funcion(**json.loads(llamada.function.arguments))
            mensajes.append({"role": "tool", "tool_call_id": llamada.id, "content": str(resultado)})
