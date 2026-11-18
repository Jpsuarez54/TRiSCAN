# -*- coding: utf-8 -*-
"""Línea de comandos: triscan scan | init | controles."""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import webbrowser
from importlib import resources
from pathlib import Path

from . import __version__, descubrir, motor, reporte

FORMATOS = {"md": ("reporte.md", reporte.markdown), "html": ("reporte.html", reporte.html_),
            "json": ("reporte.json", reporte.json_), "sarif": ("triscan.sarif", reporte.sarif)}


def _utf8() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def cmd_scan(a: argparse.Namespace) -> int:
    raiz = Path(a.ruta)
    if not raiz.is_dir():
        print(f"No existe la carpeta: {raiz}", file=sys.stderr)
        return 2
    hoy = dt.date.fromisoformat(a.hoy) if a.hoy else None
    inf = motor.ejecutar(raiz, a.inventario, hoy)
    if not a.silencioso:
        print(reporte.terminal(inf, detalle=not a.resumen))
    por_defecto = a.formato is None and not a.silencioso
    formatos = ["html"] if por_defecto else [f for f in (a.formato or []) if f != "terminal"]
    abrir = a.abrir or (por_defecto and not a.sin_abrir and not os.environ.get("CI"))
    if formatos:
        salida = Path(a.salida)
        salida.mkdir(parents=True, exist_ok=True)
        for f in formatos:
            nombre, fn = FORMATOS[f]
            (salida / nombre).write_text(fn(inf), encoding="utf-8")
            print(f"Escribí {salida / nombre}")
        if abrir and "html" in formatos:
            destino = (salida / FORMATOS["html"][0]).resolve()
            print(f"Informe visual: {destino}")
            try:
                webbrowser.open(destino.as_uri())
            except Exception:
                print("No pude abrir el navegador; abre el archivo a mano.")
    if motor.supera_umbral(inf, a.falla_en):
        print(f"\nHay controles que fallan con severidad {a.falla_en} o mayor.", file=sys.stderr)
        return 1
    return 0


def cmd_init(a: argparse.Namespace) -> int:
    destino = Path(a.ruta) / motor.NOMBRE_INVENTARIO
    if destino.exists() and not a.forzar:
        print(f"Ya existe {destino}. Usa --forzar para reemplazarlo.", file=sys.stderr)
        return 2
    texto = (resources.files("triscan") / "plantilla_inventario.yaml").read_text(encoding="utf-8")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8")
    print(f"Creé {destino}. Complétalo y ejecuta: triscan scan {a.ruta}")
    return 0


def cmd_descubrir(a: argparse.Namespace) -> int:
    raiz = Path(a.ruta)
    if not raiz.is_dir():
        print(f"No existe la carpeta: {raiz}", file=sys.stderr)
        return 2
    d = descubrir.analizar(raiz, excluir=a.excluir or (), agrupar=a.agrupar)
    print(descubrir.resumen(d))
    texto = descubrir.borrador_yaml(d, proyecto=raiz.resolve().name)
    if a.stdout:
        print("\n" + texto)
        return 0
    destino = raiz / motor.NOMBRE_INVENTARIO
    if destino.exists() and not a.forzar:
        destino = raiz / "ia-inventario.borrador.yaml"
        print(f"Ya existe {motor.NOMBRE_INVENTARIO}: no lo toqué.")
    destino.write_text(texto, encoding="utf-8")
    faltan = texto.count("COMPLETA")
    print(f"Escribí {destino} (borrador). Tiene {faltan} campo(s) por completar.")
    print(f"Ábrelo, corrige y completa; luego ejecuta: triscan scan {a.ruta}")
    return 0


def cmd_controles(a: argparse.Namespace) -> int:
    for c in motor.cargar_controles():
        print(f"{c['id']:<8} {c['pilar']:<15} {c['fase']:<11} {c['severidad']:<8} {c['titulo']}")
    return 0


def main(argv=None) -> int:
    _utf8()
    p = argparse.ArgumentParser(prog="triscan", description="TRiScan: checklist ejecutable de AI TRiSM.")
    p.add_argument("--version", action="version", version=f"triscan {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="Revisa un proyecto contra los 12 controles")
    s.add_argument("ruta", nargs="?", default=".", help="Carpeta del proyecto (por defecto, la actual)")
    s.add_argument("-i", "--inventario", help="Ruta del inventario (por defecto, <ruta>/ia-inventario.yaml)")
    s.add_argument("-f", "--formato", action="append", choices=["terminal", "md", "html", "json", "sarif"],
                   help="Formato de salida; se puede repetir (-f html -f sarif). Sin -f: terminal + informe visual HTML que se abre solo")
    s.add_argument("-o", "--salida", default="triscan-reporte", help="Carpeta para los archivos del informe")
    s.add_argument("--falla-en", default="alta", choices=["critica", "alta", "media", "baja", "nunca"],
                   help="Código de salida 1 si algo falla con esta severidad o mayor (por defecto: alta)")
    s.add_argument("--resumen", action="store_true", help="En la terminal, no mostrar el detalle de cada hallazgo")
    s.add_argument("--silencioso", action="store_true", help="No imprimir el informe en la terminal")
    s.add_argument("--abrir", action="store_true", help="Abrir el informe HTML en el navegador al terminar")
    s.add_argument("--sin-abrir", action="store_true", help="No abrir el navegador (por defecto se abre el informe visual)")
    s.add_argument("--hoy", help=argparse.SUPPRESS)
    s.set_defaults(fn=cmd_scan)
    i = sub.add_parser("init", help="Crea un ia-inventario.yaml de ejemplo")
    i.add_argument("ruta", nargs="?", default=".")
    i.add_argument("--forzar", action="store_true")
    i.set_defaults(fn=cmd_init)
    d = sub.add_parser("descubrir", help="Detecta dónde usa IA tu proyecto y arma un borrador del inventario")
    d.add_argument("ruta", nargs="?", default=".")
    d.add_argument("--forzar", action="store_true", help="Reemplazar ia-inventario.yaml si ya existe")
    d.add_argument("--stdout", action="store_true", help="Imprimir el borrador en vez de escribir un archivo")
    d.add_argument("--agrupar", choices=["archivo", "carpeta"], default="archivo",
                   help="Una entrada por archivo (por defecto) o por carpeta (menos ruido en proyectos grandes)")
    d.add_argument("--excluir", action="append", metavar="PATRON",
                   help="Ignorar rutas que coincidan (ej.: --excluir 'examples/*'); se puede repetir")
    d.set_defaults(fn=cmd_descubrir)
    c = sub.add_parser("controles", help="Lista los 12 controles")
    c.set_defaults(fn=cmd_controles)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
