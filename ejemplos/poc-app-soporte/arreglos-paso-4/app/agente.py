"""Agente de soporte al cliente de ACME, con controles (versión corregida)."""
import json
import logging

import chromadb
from llm_guard.input_scanners import PromptInjection
from llm_guard.output_scanners import Sensitive
from openai import OpenAI

from .config import OPENAI_API_KEY

cliente = OpenAI(api_key=OPENAI_API_KEY)
coleccion = chromadb.PersistentClient(path="./kb").get_or_create_collection("base_conocimiento")
registro = logging.getLogger("agente.registro")  # se envía a un destino inmutable (Object Lock)

SISTEMA = "Eres el agente de soporte de ACME. Ayuda al cliente con sus pedidos. Cita siempre la fuente de tu respuesta."
MAX_PASOS = 8
ACCIONES_CRITICAS = {"enviar_correo_cliente", "reembolsar_pedido"}

TOOLS = [
    {"type": "function", "function": {"name": "buscar_en_base_conocimiento", "description": "Busca en la base de conocimiento",
                                      "parameters": {"type": "object", "properties": {"consulta": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "consultar_pedido", "description": "Consulta el estado de un pedido",
                                      "parameters": {"type": "object", "properties": {"id_pedido": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "enviar_correo_cliente", "description": "Envía un correo al cliente (requiere aprobación)",
                                      "parameters": {"type": "object", "properties": {"correo": {"type": "string"}, "texto": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "reembolsar_pedido", "description": "Reembolsa un pedido (requiere aprobación)",
                                      "parameters": {"type": "object", "properties": {"id_pedido": {"type": "string"}, "monto": {"type": "number"}}}}},
]


def buscar_en_base_conocimiento(consulta):
    return coleccion.query(query_texts=[consulta], n_results=3)["documents"]


def consultar_pedido(id_pedido):
    return {"id": id_pedido, "estado": "en camino"}


def enviar_correo_cliente(correo, texto):
    return "enviado"


def reembolsar_pedido(id_pedido, monto):
    return "reembolsado"


def aprobada_por_persona(nombre, argumentos):
    """Una persona del equipo de soporte aprueba o rechaza antes de ejecutar (cola de aprobaciones)."""
    registro.info("aprobacion_solicitada %s %s", nombre, argumentos)
    return False  # por defecto se rechaza hasta que una persona apruebe


def responder(mensaje_usuario):
    PromptInjection().scan(mensaje_usuario)  # guardrail de entrada
    mensajes = [{"role": "system", "content": SISTEMA}, {"role": "user", "content": mensaje_usuario}]
    for _ in range(MAX_PASOS):  # tope de pasos
        r = cliente.chat.completions.create(model="gpt-4o-mini", messages=mensajes, tools=TOOLS, max_tokens=800)
        msg = r.choices[0].message
        registro.info("razonamiento %s", msg.content)  # se guarda el razonamiento
        mensajes.append(msg)
        if not msg.tool_calls:
            return Sensitive().scan(msg.content)  # guardrail de salida
        for llamada in msg.tool_calls:
            nombre = llamada.function.name
            args = json.loads(llamada.function.arguments)
            if nombre in ACCIONES_CRITICAS and not aprobada_por_persona(nombre, args):
                resultado = "Acción pendiente de aprobación humana"
            else:
                resultado = globals()[nombre](**args)
            registro.info("accion %s %s -> %s", nombre, args, resultado)
            mensajes.append({"role": "tool", "tool_call_id": llamada.id, "content": str(resultado)})
    return "No pude resolverlo; un humano continuará."
