# -*- coding: utf-8 -*-
"""POC del "día 1": cómo se usa triscan en un proyecto REAL, paso a paso.

    python scripts/poc_dia1.py            # con pausas entre pasos
    python scripts/poc_dia1.py --auto     # sin pausas
    python scripts/poc_dia1.py --sin-abrir  # no abre el navegador

Usa la app de ejemplo `ejemplos/poc-app-soporte/app-original` (un agente de soporte con OpenAI, RAG y un clasificador de Hugging Face).
Trabaja en una copia dentro de `poc-trabajo/`; el ejemplo original no se toca.
"""
import argparse
import html
import shutil
import sys
import webbrowser
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from triscan import cli, motor, reporte  # noqa: E402

POC = RAIZ / "ejemplos" / "poc-app-soporte"


def _utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass


def aplicar_respuestas(inventario: Path, respuestas: Path) -> None:
    """Simula a la persona completando el borrador: mezcla sus respuestas en el inventario."""
    inv = yaml.safe_load(inventario.read_text(encoding="utf-8"))
    resp = yaml.safe_load(respuestas.read_text(encoding="utf-8"))
    for seccion in ("modelos", "agentes"):
        for item in inv.get(seccion) or []:
            extra = (resp.get(seccion) or {}).get(item.get("id"))
            if extra:
                item.update(extra)
    inventario.write_text(yaml.safe_dump(inv, sort_keys=False, allow_unicode=True), encoding="utf-8")


def aplicar_arreglos(app: Path, arreglos: Path) -> None:
    for origen in arreglos.rglob("*"):
        if origen.is_file() and origen.name != "ELIMINAR.txt":
            destino = app / origen.relative_to(arreglos)
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origen, destino)
    lista = arreglos / "ELIMINAR.txt"
    if lista.exists():
        for linea in lista.read_text(encoding="utf-8").split():
            (app / linea).unlink(missing_ok=True)


def titulo(txt):
    print("\n" + "=" * 78 + f"\n{txt}\n" + "=" * 78)


def pausa(auto):
    if not auto:
        input("\n[Enter para continuar] ")


def medir(app: Path, trabajo: Path, n: int) -> dict:
    inf = motor.ejecutar(app)
    (trabajo / f"reporte-paso-{n}.html").write_text(reporte.html_(inf), encoding="utf-8")
    k = inf["conteo"]
    return {"n": n, "inf": inf, "cumplen": k["cumple"] + k["aviso"], "fallan": k["falla"], "pendientes": k["pendiente"]}


def mostrar(r: dict):
    print(reporte.terminal(r["inf"], detalle=False))
    urg = sorted([c for c in r["inf"]["controles"] if c["estado"] == "falla"], key=lambda c: -motor.SEVERIDAD[c["severidad"]])[:3]
    if urg:
        print("\nLo más urgente:")
        for c in urg:
            print(f"  {c['id']} ({c['severidad']}): {c['arreglo']}")
    print(f"\n>>> {r['cumplen']} de 12 controles cumplen · {r['fallan']} fallan · {r['pendientes']} pendientes")


def resumen_html(trabajo: Path, pasos: list) -> Path:
    textos = [
        ("Sin inventario", "Ejecutas triscan en el proyecto tal cual. Sin inventario casi nada se puede revisar, pero ya aparecen las llaves expuestas.", "0 min"),
        ("triscan descubrir", "Detecta modelos, agentes, herramientas y RAG, y escribe el borrador del inventario. Aún falta completarlo.", "2 min"),
        ("Completas el borrador", "Respondes lo que solo tú sabes (dueños, datos, permisos), siendo honesto con el estado actual.", "10 min"),
        ("Arreglas lo que falló", "Quitas la llave, fijas el modelo, agregas guardrails, tope de pasos, aprobación humana, registros y pruebas.", "trabajo del equipo"),
    ]
    cards = ""
    for r, (t, d, tiempo) in zip(pasos, textos):
        ok = r["cumplen"]
        cards += (f'<a class="paso" href="reporte-paso-{r["n"]}.html"><span class="n">Paso {r["n"]} · {html.escape(tiempo)}</span>'
                  f'<b>{ok}<small>/12</small></b><div class="bar"><i style="width:{round(ok / 12 * 100)}%"></i></div>'
                  f'<h3>{html.escape(t)}</h3><p>{html.escape(d)}</p>'
                  f'<span class="chips"><em>{r["fallan"]} fallan</em><em>{r["pendientes"]} pendientes</em></span></a>')
    css = reporte._CSS + """
    .pasos{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:26px}
    .paso{display:block;text-decoration:none;color:inherit;padding:20px;border-radius:24px;background:var(--card);border:1px solid var(--line);transition:transform .3s}
    .paso:hover{transform:translateY(-4px)}.paso .n{color:var(--mut);font-size:13px}
    .paso b{display:block;font-size:56px;line-height:1.1;margin:8px 0 4px;letter-spacing:-.03em}.paso b small{font-size:22px;color:var(--mut)}
    .paso .bar{height:9px;border-radius:9px;background:rgba(255,255,255,.12);overflow:hidden}.paso .bar i{display:block;height:100%;background:linear-gradient(90deg,#FF8A3D,#8B3DFF)}
    .paso:last-child .bar i{background:linear-gradient(90deg,#C6F432,#1FBF7A)}
    .paso h3{margin:14px 0 6px}.paso p{color:var(--mut);margin:0 0 12px;font-size:14px}
    .chips em{font-style:normal;font-size:12px;border:1px solid var(--line);border-radius:99px;padding:2px 10px;margin-right:6px;color:var(--mut)}
    @media(max-width:900px){.pasos{grid-template-columns:1fr 1fr}}"""
    doc = (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>POC día 1 · triscan</title><style>{css}</style></head><body><main>'
           f'<div class="top"><div class="brand"><i></i>IA sin Control</div><div class="meta">POC del día 1</div></div>'
           f'<h1>De <span>{pasos[0]["cumplen"]}/12</span> a <span>{pasos[-1]["cumplen"]}/12</span> en 4 pasos</h1>'
           f'<p class="lead">Un agente de soporte real (OpenAI + base de conocimiento + clasificador de Hugging Face), revisado desde cero. '
           f'Haz clic en cada paso para ver su informe.</p><div class="pasos">{cards}</div>'
           f'<div class="nota">Es una simulación con un proyecto de ejemplo. Lo que se declara en el inventario no se verifica contra la realidad.</div>'
           f'</main></body></html>')
    destino = trabajo / "resumen.html"
    destino.write_text(doc, encoding="utf-8")
    return destino


def main(argv=None) -> list:
    _utf8()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--auto", action="store_true", help="sin pausas entre pasos")
    p.add_argument("--sin-abrir", action="store_true", help="no abrir el navegador")
    p.add_argument("--trabajo", default=str(RAIZ / "poc-trabajo"), help="carpeta de trabajo (por defecto poc-trabajo/)")
    a = p.parse_args(argv)
    trabajo = Path(a.trabajo)
    if trabajo.exists():
        shutil.rmtree(trabajo)
    app = trabajo / "app-soporte"
    shutil.copytree(POC / "app-original", app)
    pasos = []

    titulo("PASO 1 · Llegas a un proyecto que ya usa IA y ejecutas:  triscan scan .")
    print("(Es un agente de soporte con OpenAI, base de conocimiento y un clasificador de Hugging Face. Nadie escribió un inventario.)")
    pasos.append(medir(app, trabajo, 1))
    mostrar(pasos[-1])
    pausa(a.auto)

    titulo("PASO 2 · En vez de escribir el inventario a mano, ejecutas:  triscan descubrir .")
    cli.main(["descubrir", str(app)])
    inv = app / motor.NOMBRE_INVENTARIO
    print("\n--- así se ve el borrador (primeras líneas) ---")
    print("\n".join(inv.read_text(encoding="utf-8").splitlines()[:34]))
    pasos.append(medir(app, trabajo, 2))
    mostrar(pasos[-1])
    pausa(a.auto)

    titulo("PASO 3 · Completas lo que solo tú sabes (dueños, datos, permisos) y vuelves a revisar")
    aplicar_respuestas(inv, POC / "respuestas-paso-3.yaml")
    pasos.append(medir(app, trabajo, 3))
    mostrar(pasos[-1])
    pausa(a.auto)

    titulo("PASO 4 · Arreglas lo que falló (llave fuera del código, modelo fijado, guardrails, tope, aprobación, registros, pruebas)")
    aplicar_arreglos(app, POC / "arreglos-paso-4")
    aplicar_respuestas(inv, POC / "respuestas-paso-4.yaml")
    pasos.append(medir(app, trabajo, 4))
    mostrar(pasos[-1])

    resumen = resumen_html(trabajo, pasos)
    titulo("RESULTADO")
    print(f"{'Paso':<6}{'Cumplen':>9}{'Fallan':>8}{'Pendientes':>12}")
    for r in pasos:
        print(f"{r['n']:<6}{str(r['cumplen']) + '/12':>9}{r['fallan']:>8}{r['pendientes']:>12}")
    print(f"\nResumen visual: {resumen}")
    if not a.sin_abrir:
        webbrowser.open(resumen.resolve().as_uri())
    return pasos


if __name__ == "__main__":
    main()
