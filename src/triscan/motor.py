# -*- coding: utf-8 -*-
"""Carga los controles, corre las reglas y calcula puntajes."""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict
from importlib import resources
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from . import __version__
from .reglas import AVISO, CUMPLE, FALLA, NO_APLICA, PENDIENTE, REGLAS, Contexto, cargar_inventario

PILARES = ["SecOps", "Privacidad", "Gobernanza", "Explicabilidad"]
SEVERIDAD = {"baja": 1, "media": 2, "alta": 3, "critica": 4}
NOMBRE_INVENTARIO = "ia-inventario.yaml"


def cargar_controles() -> List[dict]:
    texto = (resources.files("triscan") / "controles.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(texto)["controles"]


def agregar_estado(hallazgos) -> str:
    estados = {h.estado for h in hallazgos}
    if FALLA in estados:
        return FALLA
    if PENDIENTE in estados:
        return PENDIENTE
    if AVISO in estados:
        return AVISO
    if CUMPLE in estados:
        return CUMPLE
    return NO_APLICA


def puntaje(resultados: List[dict]) -> Optional[int]:
    """Cumplen / (cumplen + fallan). Los avisos cuentan como cumplidos; lo pendiente no entra."""
    ok = sum(1 for r in resultados if r["estado"] in (CUMPLE, AVISO))
    mal = sum(1 for r in resultados if r["estado"] == FALLA)
    return None if ok + mal == 0 else round(100 * ok / (ok + mal))


def ejecutar(raiz, ruta_inventario=None, hoy: Optional[dt.date] = None) -> Dict:
    raiz = Path(raiz).resolve()
    ruta_inv = Path(ruta_inventario).resolve() if ruta_inventario else raiz / NOMBRE_INVENTARIO
    inventario = cargar_inventario(ruta_inv)
    ctx = Contexto(raiz=raiz, inventario=inventario, ruta_inventario=ruta_inv if inventario is not None else None,
                   hoy=hoy or dt.date.today())
    resultados = []
    for c in cargar_controles():
        hallazgos = REGLAS[c["regla"]](ctx)
        r = dict(c)
        r["estado"] = agregar_estado(hallazgos)
        r["hallazgos"] = [asdict(h) for h in hallazgos]
        resultados.append(r)
    pilares = {p: {"puntaje": puntaje([r for r in resultados if r["pilar"] == p]),
                   "fallan": sum(1 for r in resultados if r["pilar"] == p and r["estado"] == FALLA),
                   "pendientes": sum(1 for r in resultados if r["pilar"] == p and r["estado"] == PENDIENTE)} for p in PILARES}
    conteo = {e: sum(1 for r in resultados if r["estado"] == e) for e in (CUMPLE, AVISO, FALLA, PENDIENTE, NO_APLICA)}
    return {"herramienta": "triscan", "version": __version__, "fecha": (hoy or dt.date.today()).isoformat(),
            "raiz": str(raiz), "inventario": ctx.archivo_inv, "puntaje_total": puntaje(resultados), "conteo": conteo,
            "pilares": pilares, "controles": resultados, "truncado": ctx.truncado}


def supera_umbral(informe: Dict, umbral: str) -> bool:
    """True si hay algún control que FALLA con severidad igual o mayor al umbral."""
    if umbral == "nunca":
        return False
    minimo = SEVERIDAD[umbral]
    return any(c["estado"] == FALLA and SEVERIDAD[c["severidad"]] >= minimo for c in informe["controles"])
