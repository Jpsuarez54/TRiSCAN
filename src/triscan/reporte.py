# -*- coding: utf-8 -*-
"""Salidas del informe: terminal, Markdown, JSON, HTML y SARIF (para GitHub Code Scanning)."""
from __future__ import annotations

import html
import json
import os
import sys
from typing import Dict, List

from .motor import PILARES

ETIQUETA = {"cumple": "OK", "aviso": "AVISO", "falla": "FALLA", "pendiente": "PEND", "no_aplica": "N/A"}
COLOR = {"cumple": "32", "aviso": "33", "falla": "31", "pendiente": "36", "no_aplica": "90"}
NOMBRE_ESTADO = {"cumple": "Cumple", "aviso": "Cumple con avisos", "falla": "Falla", "pendiente": "Pendiente", "no_aplica": "No aplica"}


def _color(txt: str, estado: str) -> str:
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return txt
    return f"\033[{COLOR[estado]}m{txt}\033[0m"


def _barra(p) -> str:
    if p is None:
        return "sin datos"
    llenos = round(p / 10)
    return "#" * llenos + "." * (10 - llenos) + f" {p}/100"


def terminal(inf: Dict, detalle: bool = True) -> str:
    L: List[str] = []
    L.append(f"TRiScan {inf['version']} · {inf['fecha']}")
    L.append(f"Proyecto: {inf['raiz']}")
    L.append(f"Inventario: {inf['inventario'] or 'NO ENCONTRADO (triscan init lo crea)'}")
    L.append("")
    L.append("PILAR            PUNTAJE")
    for p in PILARES:
        d = inf["pilares"][p]
        extra = f"   {d['fallan']} falla(n)" if d["fallan"] else ""
        extra += f"   {d['pendientes']} pendiente(s)" if d["pendientes"] else ""
        L.append(f"{p:<16} {_barra(d['puntaje'])}{extra}")
    total = inf["puntaje_total"]
    L.append(f"{'TOTAL':<16} {_barra(total)}")
    L.append("")
    for c in inf["controles"]:
        et = _color(f"[{ETIQUETA[c['estado']]:<5}]", c["estado"])
        L.append(f"{et} {c['id']:<8} {c['titulo']}  ({c['severidad']})")
        if detalle and c["estado"] != "cumple":
            for h in c["hallazgos"]:
                if h["estado"] in ("cumple", "no_aplica"):
                    continue
                donde = f" [{h['archivo']}{':' + str(h['linea']) if h.get('linea') else ''}]" if h.get("archivo") else ""
                L.append(f"           - {h['mensaje']}{donde}")
            if c["estado"] in ("falla", "pendiente"):
                L.append(f"           Arreglo: {c['arreglo']}")
    L.append("")
    k = inf["conteo"]
    L.append(f"Cumplen: {k['cumple']} · Con avisos: {k['aviso']} · Fallan: {k['falla']} · Pendientes: {k['pendiente']} · No aplican: {k['no_aplica']}")
    if inf.get("truncado"):
        L.append("Aviso: el proyecto es muy grande y solo se revisó una parte de los archivos de texto.")
    L.append("Nota: esta revisión es una primera mirada, no prueba que el sistema sea seguro.")
    return "\n".join(L)


def markdown(inf: Dict) -> str:
    L = [f"# Informe TRiScan", "", f"Fecha: {inf['fecha']} · Versión: {inf['version']}", "",
         f"**Puntaje total:** {inf['puntaje_total'] if inf['puntaje_total'] is not None else 'sin datos'}/100", "",
         "| Pilar | Puntaje | Fallan | Pendientes |", "|---|---|---|---|"]
    for p in PILARES:
        d = inf["pilares"][p]
        L.append(f"| {p} | {d['puntaje'] if d['puntaje'] is not None else '-'} | {d['fallan']} | {d['pendientes']} |")
    L += ["", "## Controles", ""]
    for c in inf["controles"]:
        L.append(f"### {c['id']} · {c['titulo']} — {NOMBRE_ESTADO[c['estado']]} ({c['severidad']})")
        L.append(f"*{c['pilar']} · {c['fase']}*")
        for h in c["hallazgos"]:
            if h["estado"] in ("cumple", "no_aplica") and c["estado"] != "cumple":
                continue
            donde = f" (`{h['archivo']}{':' + str(h['linea']) if h.get('linea') else ''}`)" if h.get("archivo") else ""
            L.append(f"- {h['mensaje']}{donde}")
        if c["estado"] in ("falla", "pendiente"):
            L.append(f"- **Arreglo:** {c['arreglo']}")
        r = c["referencias"]
        L.append(f"- Referencias: OWASP LLM {', '.join(r.get('owasp_llm', []))} · NIST AI RMF {', '.join(r.get('nist_ai_rmf', []))} · ISO/IEC 42001 {r.get('iso_42001', '')}")
        L.append("")
    L.append("> Esta revisión es una primera mirada, no prueba que el sistema sea seguro.")
    return "\n".join(L)


def json_(inf: Dict) -> str:
    return json.dumps(inf, ensure_ascii=False, indent=2, default=str)


def sarif(inf: Dict) -> str:
    nivel = {"critica": "error", "alta": "error", "media": "warning", "baja": "note"}
    reglas = []
    resultados = []
    for c in inf["controles"]:
        r = c["referencias"]
        reglas.append({"id": c["id"], "name": c["regla"], "shortDescription": {"text": c["titulo"]},
                       "fullDescription": {"text": c["por_que"]}, "help": {"text": c["arreglo"]},
                       "properties": {"tags": [c["pilar"], c["fase"]] + [f"OWASP-{x}" for x in r.get("owasp_llm", [])] +
                                      [f"NIST-{x}" for x in r.get("nist_ai_rmf", [])]}})
        for h in c["hallazgos"]:
            if h["estado"] not in ("falla", "aviso", "pendiente"):
                continue
            archivo = h.get("archivo") or inf.get("inventario") or "ia-inventario.yaml"
            lvl = nivel[c["severidad"]] if h["estado"] == "falla" else "note"
            resultados.append({"ruleId": c["id"], "level": lvl, "message": {"text": h["mensaje"] + " Arreglo: " + c["arreglo"]},
                               "locations": [{"physicalLocation": {"artifactLocation": {"uri": archivo},
                                                                   "region": {"startLine": h.get("linea") or 1}}}]})
    doc = {"$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0",
           "runs": [{"tool": {"driver": {"name": "triscan", "version": inf["version"],
                                         "informationUri": "https://github.com/Jpsuarez54/triscan", "rules": reglas}},
                     "results": resultados}]}
    return json.dumps(doc, ensure_ascii=False, indent=2)


SEV = {"baja": 1, "media": 2, "alta": 3, "critica": 4}
NOMBRE_SEV = {"baja": "Baja", "media": "Media", "alta": "Alta", "critica": "Crítica"}
INICIAL = {"SecOps": "S", "Privacidad": "P", "Gobernanza": "G", "Explicabilidad": "E"}

# Logo de TRiScan (la T con volumen y la línea de escaneo), el mismo de docs/img/triscan-icono.svg
_LOGO = ('<svg viewBox="0 0 120 124" aria-hidden="true"><defs>'
         '<linearGradient id="trs-cara" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#9c9c9c"/></linearGradient>'
         '</defs><path d="M28 26 H100 V44 H74 V104 H54 V44 H28 Z" fill="#2a2a2a"/>'
         '<path d="M22 20 H94 V38 H68 V98 H48 V38 H22 Z" fill="url(#trs-cara)"/>'
         '<line x1="10" y1="64" x2="110" y2="64" stroke="#B9F227" stroke-width="9" stroke-opacity=".2"/>'
         '<line x1="10" y1="64" x2="110" y2="64" stroke="#B9F227" stroke-width="3" stroke-linecap="round"/>'
         '<circle cx="80" cy="12" r="5" fill="#B9F227"/></svg>')
_FAVICON = ("data:image/svg+xml," + _LOGO.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ')
            .replace("#", "%23").replace('"', "'"))

_CSS = """
:root{--bg:#0B0A12;--card:rgba(255,255,255,.05);--line:rgba(255,255,255,.14);--tx:#f4f2fa;--mut:#aaa4c0;--ok:#B6F23C;--fail:#FF7043;--warn:#FFC857;--pen:#7fd6ff;--ease:cubic-bezier(.16,1,.3,1)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;color:var(--tx);font:16px/1.55 Inter,"Segoe UI",system-ui,-apple-system,sans-serif;background:
 radial-gradient(900px 600px at -8% 108%,rgba(255,122,47,.45),transparent 62%),
 radial-gradient(900px 650px at 108% -10%,rgba(139,61,255,.45),transparent 60%),var(--bg);background-attachment:fixed;min-height:100vh}
main{max-width:1080px;margin:0 auto;padding:28px 22px 90px}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:12px;font-weight:700;font-size:18px}
.brand svg{width:40px;height:41px;display:block}
.brand .i{color:#B9F227}
.meta{color:var(--mut);font-size:13px}
h1{font-size:clamp(30px,5vw,46px);line-height:1.08;margin:26px 0 6px;letter-spacing:-.02em}
h1 span{background:linear-gradient(90deg,#FF8A3D,#8B3DFF);-webkit-background-clip:text;background-clip:text;color:transparent}
.lead{color:var(--mut);max-width:680px;margin:0}
.hero{display:grid;grid-template-columns:260px 1fr;gap:26px;align-items:center;margin:26px 0 8px;padding:26px;border-radius:30px;background:var(--card);border:1px solid var(--line);backdrop-filter:blur(10px)}
.gauge{position:relative;width:240px;height:240px}
.gauge svg{width:100%;height:100%;transform:rotate(-90deg)}
.gauge .bg{fill:none;stroke:rgba(255,255,255,.12);stroke-width:16}
.gauge .arc{fill:none;stroke-width:16;stroke-linecap:round;stroke-dasharray:0 440;animation:fill 1.8s var(--ease) .3s forwards}
@keyframes fill{from{stroke-dasharray:0 440}to{stroke-dasharray:var(--len) 440}}
.gauge .num{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.gauge .num b{font-size:64px;line-height:1;letter-spacing:-.03em}
.gauge .num>span{color:var(--mut);font-size:14px}
.hero h2{margin:0 0 6px;font-size:28px;letter-spacing:-.01em}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.chip{display:inline-flex;align-items:center;gap:8px;padding:7px 14px;border-radius:99px;border:1px solid var(--line);background:rgba(255,255,255,.06);font-size:14px}
.chip b{font-size:18px}.chip i{width:10px;height:10px;border-radius:50%;display:block}
.sec{margin:34px 0 12px;font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--mut);font-weight:700}
.urg{display:grid;gap:10px}
.urg a{display:flex;gap:14px;align-items:flex-start;text-decoration:none;color:inherit;padding:14px 18px;border-radius:18px;background:rgba(255,112,67,.10);border:1px solid rgba(255,112,67,.45);transition:transform .3s var(--ease),background .3s}
.urg a:hover{transform:translateY(-2px);background:rgba(255,112,67,.16)}
.urg .n{flex:none;width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,#FF8A3D,#8B3DFF);display:flex;align-items:center;justify-content:center;font-weight:800}
.urg b{display:block}.urg small{color:var(--mut)}
.pilares{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.pil{padding:18px;border-radius:22px;background:var(--card);border:1px solid var(--line)}
.pil .ic{width:38px;height:38px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-weight:800;color:#0B0A12;background:linear-gradient(135deg,#C6F432,#1FBF7A)}
.pil.mal .ic{background:linear-gradient(135deg,#FF8A3D,#8B3DFF);color:#fff}.pil.med .ic{background:linear-gradient(135deg,#FFC857,#FF7043);color:#0B0A12}
.pil h3{margin:10px 0 0;font-size:15px}.pil .v{font-size:38px;font-weight:800;letter-spacing:-.02em;line-height:1.1}
.pil .bar{height:8px;border-radius:9px;background:rgba(255,255,255,.12);overflow:hidden;margin:6px 0 8px}
.pil .bar i{display:block;height:100%;width:0;border-radius:9px;background:linear-gradient(90deg,#C6F432,#1FBF7A);animation:grow 1.4s var(--ease) .5s forwards}
.pil.mal .bar i{background:linear-gradient(90deg,#FF8A3D,#8B3DFF)}.pil.med .bar i{background:linear-gradient(90deg,#FFC857,#FF7043)}
@keyframes grow{to{width:var(--w)}}
.pil small{color:var(--mut)}
.filtros{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 14px}
.filtros button{font:inherit;color:var(--tx);background:rgba(255,255,255,.06);border:1px solid var(--line);border-radius:99px;padding:7px 16px;cursor:pointer;transition:all .25s}
.filtros button:hover{border-color:#fff}
.filtros button.on{background:linear-gradient(135deg,#FF8A3D,#8B3DFF);border-color:transparent}
.filtros .sep{width:1px;background:var(--line);margin:0 4px}
.ctl{margin:10px 0;border-radius:22px;background:var(--card);border:1px solid var(--line);border-left:7px solid var(--mut);overflow:hidden;animation:rise .8s var(--ease) both}
.ctl.cumple{border-left-color:var(--ok)}.ctl.aviso{border-left-color:var(--warn)}.ctl.falla{border-left-color:var(--fail)}.ctl.pendiente{border-left-color:var(--pen)}
@keyframes rise{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
.ctl[hidden]{display:none}
.ctl summary{list-style:none;cursor:pointer;padding:16px 20px;display:flex;gap:14px;align-items:center}
.ctl summary::-webkit-details-marker{display:none}
.ctl summary::after{content:"+";margin-left:auto;font-size:24px;color:var(--mut);transition:transform .3s}
.ctl[open] summary::after{transform:rotate(45deg)}
.id{flex:none;font:700 13px ui-monospace,Consolas,monospace;padding:4px 10px;border-radius:9px;background:rgba(255,255,255,.1)}
.tt{font-weight:700}.tt small{display:block;font-weight:400;color:var(--mut)}
.est{flex:none;font-size:13px;font-weight:700;padding:3px 12px;border-radius:99px}
.est.cumple{background:rgba(182,242,60,.15);color:var(--ok)}.est.aviso{background:rgba(255,200,87,.15);color:var(--warn)}
.est.falla{background:rgba(255,112,67,.18);color:var(--fail)}.est.pendiente{background:rgba(127,214,255,.15);color:var(--pen)}
.cuerpo{padding:0 20px 20px 20px}
.cuerpo p{margin:0 0 10px;color:var(--mut)}
.hall{margin:10px 0;padding:0;list-style:none;display:grid;gap:6px}
.hall li{padding:9px 14px;border-radius:12px;background:rgba(255,255,255,.05)}
.hall code,.cuerpo code{font:13px ui-monospace,Consolas,monospace;background:rgba(0,0,0,.35);padding:2px 8px;border-radius:7px;color:#e5def9;white-space:nowrap}
.fix{margin:12px 0;padding:13px 16px;border-radius:14px;background:rgba(182,242,60,.09);border:1px solid rgba(182,242,60,.4)}
.fix b{color:var(--ok)}
.caso{margin:12px 0;padding:11px 16px;border-left:4px solid #8B3DFF;color:var(--mut);font-style:italic}
.refs{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.refs span{font-size:12px;padding:3px 11px;border-radius:99px;border:1px solid var(--line);color:var(--mut)}
.tags{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.tags span{font-size:12px;padding:2px 10px;border-radius:99px;background:rgba(255,255,255,.08);color:var(--mut)}
.sev-critica{color:#ff8a8a}.sev-alta{color:var(--fail)}.sev-media{color:var(--warn)}.sev-baja{color:var(--mut)}
.vacio{padding:22px;text-align:center;color:var(--mut)}
footer{margin-top:44px;color:var(--mut);font-size:13px;border-top:1px solid var(--line);padding-top:18px}
.nota{margin-top:26px;padding:14px 18px;border-radius:16px;border:1px dashed var(--line);color:var(--mut)}
@media(max-width:860px){.hero{grid-template-columns:1fr;justify-items:center;text-align:center}.pilares{grid-template-columns:repeat(2,1fr)}.chips{justify-content:center}}
@media(prefers-reduced-motion:reduce){*{animation-duration:.01ms!important;animation-delay:0s!important}}
@media print{body{background:#fff;color:#111}:root{--card:#fff;--line:#d6d2e2;--mut:#555;--tx:#111}.hero,.pil,.ctl,.chip{backdrop-filter:none;background:#fff}.filtros{display:none}.gauge .num span,.meta{color:#555}.ctl{break-inside:avoid}.hall code,.cuerpo code{background:#eee;color:#111}}
"""

_JS = """
(function(){
var q=function(s){return Array.prototype.slice.call(document.querySelectorAll(s));};
var est='todos',pil='todos';
function aplicar(){
  var visibles=0;
  q('.ctl').forEach(function(c){
    var ok=(est==='todos'||c.dataset.estado===est)&&(pil==='todos'||c.dataset.pilar===pil);
    c.hidden=!ok; if(ok)visibles++;
  });
  document.getElementById('vacio').hidden=visibles>0;
}
q('[data-f]').forEach(function(b){b.onclick=function(){est=b.dataset.f;q('[data-f]').forEach(function(x){x.classList.toggle('on',x===b);});aplicar();};});
q('[data-p]').forEach(function(b){b.onclick=function(){pil=b.dataset.p;q('[data-p]').forEach(function(x){x.classList.toggle('on',x===b);});aplicar();};});
q('[data-count]').forEach(function(e){
  var fin=parseInt(e.dataset.count,10),t0=null;
  function paso(t){if(t0===null)t0=t;var k=Math.min(1,(t-t0)/1400),v=1-Math.pow(1-k,4);e.textContent=Math.round(fin*v);if(k<1)requestAnimationFrame(paso);}
  requestAnimationFrame(paso);
});
q('.urg a').forEach(function(a){a.addEventListener('click',function(){var d=document.querySelector(a.getAttribute('href'));if(d){d.open=true;}});});
window.addEventListener('beforeprint',function(){q('.ctl').forEach(function(c){c.open=true;c.hidden=false;});});
})();
"""


def _num(v):
    return "-" if v is None else '<span data-count="%s">%s</span>' % (v, v)


def _mensaje(tot):
    if tot is None:
        return "Sin datos suficientes", "Todavía no hay controles que se puedan revisar. Crea el inventario con triscan init y vuelve a ejecutar."
    if tot >= 90:
        return "Buen punto de partida", "Cumples casi todo lo que revisamos. Mantén los controles y repite la revisión con cada cambio."
    if tot >= 60:
        return "Hay trabajo por hacer", "Tienes bases, pero faltan controles importantes. Empieza por lo más urgente."
    return "Brecha importante", "Faltan controles básicos. Empieza por lo más urgente: es lo que más riesgo reduce."


def _clase_puntaje(p):
    return "mal" if p is not None and p < 60 else ("med" if p is not None and p < 85 else "bien")


def html_(inf: Dict) -> str:
    e = html.escape
    tot = inf["puntaje_total"]
    titulo, bajada = _mensaje(tot)
    clase = _clase_puntaje(tot)
    grad = {"mal": ("#FF8A3D", "#8B3DFF"), "med": ("#FFC857", "#FF7043"), "bien": ("#C6F432", "#1FBF7A")}[clase]
    largo = round(439.8 * (tot or 0) / 100, 1)
    k = inf["conteo"]
    chips = "".join(f'<span class="chip"><i style="background:{col}"></i><b>{k[key]}</b> {txt}</span>' for key, txt, col in
                    (("cumple", "cumplen", "#B6F23C"), ("aviso", "con avisos", "#FFC857"), ("falla", "fallan", "#FF7043"), ("pendiente", "pendientes", "#7fd6ff")))
    urg = sorted([c for c in inf["controles"] if c["estado"] == "falla"], key=lambda c: (-SEV[c["severidad"]], c["id"]))[:3]
    urg_html = "".join(
        f'<a href="#{e(c["id"])}"><span class="n">{i + 1}</span><span><b>{e(c["id"])} · {e(c["titulo"])}</b><small>{e(c["arreglo"])}</small></span></a>'
        for i, c in enumerate(urg))
    urg_blk = f'<div class="sec">Lo más urgente</div><div class="urg">{urg_html}</div>' if urg else ""
    pil_html = ""
    for p in PILARES:
        d = inf["pilares"][p]
        v = d["puntaje"]
        cl = _clase_puntaje(v)
        det = []
        if d["fallan"]:
            det.append(f'{d["fallan"]} falla(n)')
        if d["pendientes"]:
            det.append(f'{d["pendientes"]} pendiente(s)')
        pil_html += (f'<div class="pil {cl}"><div class="ic">{INICIAL[p]}</div><h3>{e(p)}</h3>'
                     f'<div class="v">{_num(v)}</div>'
                     f'<div class="bar"><i style="--w:{v or 0}%"></i></div><small>{e(", ".join(det) or "todo en orden")}</small></div>')
    cards = []
    for c in inf["controles"]:
        items = []
        for h in c["hallazgos"]:
            if c["estado"] != "cumple" and h["estado"] in ("cumple", "no_aplica"):
                continue
            donde = f' <code>{e(h["archivo"])}{":" + str(h["linea"]) if h.get("linea") else ""}</code>' if h.get("archivo") else ""
            items.append(f'<li>{e(h["mensaje"])}{donde}</li>')
        r = c["referencias"]
        refs = ([f"OWASP LLM {x}" for x in r.get("owasp_llm", [])] + [f"NIST AI RMF · {x}" for x in r.get("nist_ai_rmf", [])]
                + [f"ISO/IEC 42001 · {r.get('iso_42001', '')}"])
        fix = (f'<div class="fix"><b>Cómo arreglarlo.</b> {e(c["arreglo"])}</div>' if c["estado"] in ("falla", "pendiente", "aviso") else "")
        abierto = " open" if c["estado"] in ("falla", "pendiente") else ""
        cards.append(
            f'<details class="ctl {c["estado"]}" id="{e(c["id"])}" data-estado="{c["estado"]}" data-pilar="{e(c["pilar"])}"{abierto}>'
            f'<summary><span class="id">{e(c["id"])}</span><span class="tt">{e(c["titulo"])}<small>{e(c["pilar"])} · {e(c["fase"])} · '
            f'severidad <span class="sev-{c["severidad"]}">{NOMBRE_SEV[c["severidad"]]}</span></small></span>'
            f'<span class="est {c["estado"]}">{NOMBRE_ESTADO[c["estado"]]}</span></summary>'
            f'<div class="cuerpo"><p>{e(c["por_que"])}</p><ul class="hall">{"".join(items)}</ul>{fix}'
            f'<div class="caso">En la charla: {e(c["caso"])}</div>'
            f'<div class="refs">{"".join(f"<span>{e(x)}</span>" for x in refs)}</div></div></details>')
    filtros = ("".join(f'<button data-f="{f}"{" class=on" if f == "todos" else ""}>{t}</button>' for f, t in
                       (("todos", "Todos"), ("falla", "Fallan"), ("pendiente", "Pendientes"), ("aviso", "Con avisos"), ("cumple", "Cumplen")))
               + '<span class="sep"></span>'
               + "".join(f'<button data-p="{x}"{" class=on" if x == "todos" else ""}>{y}</button>' for x, y in
                         [("todos", "Todos los pilares")] + [(p, p) for p in PILARES]))
    return (
        f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Informe TRiScan</title><link rel="icon" href="{_FAVICON}"><style>{_CSS}</style></head><body><main>'
        f'<div class="top"><div class="brand">{_LOGO}<span>TR<span class="i">i</span>Scan</span></div>'
        f'<div class="meta">TRiScan {e(inf["version"])} · {e(inf["fecha"])} · inventario: {e(inf["inventario"] or "no encontrado")}</div></div>'
        f'<h1>Informe de <span>AI TRiSM</span></h1><p class="lead">Revisión de tu proyecto contra 12 controles de seguridad, privacidad, gobernanza y explicabilidad.</p>'
        f'<section class="hero"><div class="gauge"><svg viewBox="0 0 160 160"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{grad[0]}"/><stop offset="1" stop-color="{grad[1]}"/></linearGradient></defs>'
        f'<circle class="bg" cx="80" cy="80" r="70"/><circle class="arc" cx="80" cy="80" r="70" stroke="url(#g)" style="--len:{largo}"/></svg>'
        f'<div class="num"><b>{_num(tot)}</b><span>de 100</span></div></div>'
        f'<div><h2>{e(titulo)}</h2><p class="lead">{e(bajada)}</p><div class="chips">{chips}</div></div></section>'
        f'{urg_blk}<div class="sec">Por pilar</div><div class="pilares">{pil_html}</div>'
        f'<div class="sec">Los 12 controles</div><div class="filtros">{filtros}</div>{"".join(cards)}'
        f'<div class="vacio" id="vacio" hidden>No hay controles con ese filtro.</div>'
        f'<div class="nota">Esta revisión es una primera mirada: encuentra problemas comunes y deja evidencia, pero no prueba que el sistema sea seguro.</div>'
        f'<footer>Generado por TRiScan {e(inf["version"])} · Proyecto: {e(inf["raiz"])}</footer></main><script>{_JS}</script></body></html>')
