# -*- coding: utf-8 -*-
"""Revisa el HTML del informe: etiquetas balanceadas y JavaScript sin errores de sintaxis (usa mini-racer si está instalado)."""
import datetime as dt
import json
import os
import sys
from html.parser import HTMLParser

from pathlib import Path

os.chdir(Path(__file__).resolve().parents[1])  # las rutas son relativas a la raíz del repositorio

from triscan import motor, reporte  # noqa: E402


class P(HTMLParser):
    VOID = {"meta", "br", "img", "input", "link", "circle", "stop", "hr"}

    def __init__(s):
        super().__init__()
        s.st, s.err = [], 0

    def handle_starttag(s, t, a):
        if t not in s.VOID:
            s.st.append(t)

    def handle_startendtag(s, t, a):
        pass

    def handle_endtag(s, t):
        if s.st and s.st[-1] == t:
            s.st.pop()
        else:
            s.err += 1


for nombre in ("proyecto-inseguro", "proyecto-seguro"):
    inf = motor.ejecutar(os.path.join("ejemplos", nombre), hoy=dt.date(2026, 11, 18))
    h = reporte.html_(inf)
    p = P()
    p.feed(h)
    print(nombre, "| etiquetas sin cerrar:", len(p.st), "| errores:", p.err, "| KB:", round(len(h) / 1024))
    if nombre == "proyecto-inseguro":
        os.makedirs("triscan-reporte", exist_ok=True)
        open(os.path.join("triscan-reporte", "demo-inseguro.html"), "w", encoding="utf-8").write(h)
try:
    from py_mini_racer import MiniRacer
    MiniRacer().eval("new Function(" + json.dumps(reporte._JS) + ")")
    print("JavaScript del informe: sintaxis correcta")
except ImportError:
    print("mini-racer no instalado: no se revisó el JavaScript")
sys.stdout.flush()
os._exit(0)
