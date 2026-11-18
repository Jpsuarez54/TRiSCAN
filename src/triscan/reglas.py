# -*- coding: utf-8 -*-
"""Reglas de los 12 controles. Cada regla recibe un Contexto y devuelve una lista de Hallazgo."""
from __future__ import annotations

import datetime as dt
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Tuple

import yaml

CUMPLE, FALLA, PENDIENTE, AVISO, NO_APLICA = "cumple", "falla", "pendiente", "aviso", "no_aplica"

IGNORAR_DIRS = {".git", "node_modules", ".venv", "venv", "env", "__pycache__", "dist", "build", ".mypy_cache",
                ".pytest_cache", ".idea", ".vscode", "site-packages", ".tox", "triscan-reporte"}
EXT_TEXTO = {".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml", ".toml", ".txt", ".md", ".ini", ".cfg",
             ".sh", ".env", ".ipynb", ".java", ".go", ".rb", ".cs", ".php", ".tf", ".properties", ".conf"}
NOMBRES_TEXTO = {".env", "dockerfile", "makefile", "requirements.txt", "pipfile"}
MAX_BYTES = 1_500_000
MAX_TOTAL_BYTES = 150_000_000   # tope de texto en memoria: en repositorios enormes se revisa solo una parte
DIAS_RED_TEAM = 180
CLASES_DATOS = {"publico", "público", "interno", "personal", "sensible", "confidencial"}
HERRAMIENTAS_CRITICAS = ("shell", "bash", "exec", "eval", "sudo", "ssh", "delete", "borrar", "eliminar", "drop", "pago",
                         "pagar", "payment", "transfer", "deploy", "desplegar", "admin", "escribir", "write", "enviar", "send",
                         "mail", "correo", "email", "reembols", "refund", "cancel")
LIBS_GUARDRAILS = ("llm-guard", "llm_guard", "nemoguardrails", "nemo-guardrails", "guardrails-ai", "guardrails_ai", "lakera",
                   "rebuff", "llamafirewall", "prompt-guard", "protectai")
HERRAMIENTAS_RED_TEAM = ("promptfoo", "garak", "pyrit", "giskard", "deepteam")


@dataclass
class Hallazgo:
    estado: str
    mensaje: str
    archivo: Optional[str] = None
    linea: Optional[int] = None


@dataclass
class Contexto:
    raiz: Path
    inventario: Optional[dict] = None
    ruta_inventario: Optional[Path] = None
    hoy: dt.date = field(default_factory=dt.date.today)
    _cache: Optional[List[Tuple[str, str]]] = None
    truncado: bool = False

    def rel(self, p: Path) -> str:
        try:
            return p.relative_to(self.raiz).as_posix()
        except ValueError:
            return p.as_posix()

    def archivos(self) -> Iterator[Path]:
        # os.walk con poda: no entra a .git, node_modules, entornos virtuales, etc. (rápido en repositorios grandes)
        for carpeta, dirs, nombres in os.walk(self.raiz):
            dirs[:] = sorted(d for d in dirs if d not in IGNORAR_DIRS and not d.endswith(".egg-info"))
            for n in sorted(nombres):
                yield Path(carpeta) / n

    def textos(self) -> List[Tuple[str, str]]:
        if self._cache is None:
            out = []
            total = 0
            for p in self.archivos():
                if p.suffix.lower() in EXT_TEXTO or p.name.lower() in NOMBRES_TEXTO:
                    try:
                        if p.stat().st_size > MAX_BYTES:
                            continue
                        txt = p.read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        continue
                    total += len(txt)
                    if total > MAX_TOTAL_BYTES:
                        self.truncado = True
                        break
                    out.append((self.rel(p), txt))
            self._cache = out
        return self._cache

    @property
    def modelos(self) -> List[dict]:
        return [m for m in (self.inventario or {}).get("modelos", []) or [] if isinstance(m, dict)]

    @property
    def agentes(self) -> List[dict]:
        return [a for a in (self.inventario or {}).get("agentes", []) or [] if isinstance(a, dict)]

    @property
    def archivo_inv(self) -> Optional[str]:
        return self.rel(self.ruta_inventario) if self.ruta_inventario else None


def _linea(texto: str, pos: int) -> int:
    return texto.count("\n", 0, pos) + 1


def _sin_inventario(ctx: Contexto, que: str) -> List[Hallazgo]:
    return [Hallazgo(PENDIENTE, f"No hay ia-inventario.yaml, así que no se puede revisar {que}. Créalo con: triscan init")]


def _id(x: dict) -> str:
    return str(x.get("id", "(sin id)"))


# ---------------------------------------------------------------- AUDITAR
def inventario_completo(ctx: Contexto) -> List[Hallazgo]:
    if ctx.inventario is None:
        return [Hallazgo(FALLA, "No existe ia-inventario.yaml: no hay inventario de modelos ni agentes.")]
    items = [("modelo", m) for m in ctx.modelos] + [("agente", a) for a in ctx.agentes]
    if not items:
        return [Hallazgo(FALLA, "El inventario está vacío: declara al menos un modelo o un agente.", ctx.archivo_inv, 1)]
    out = []
    for tipo, x in items:
        requeridos = ("dueno", "version", "origen") if tipo == "modelo" else ("dueno", "modelo")
        faltan = [k for k in requeridos if not x.get(k)]
        if faltan:
            out.append(Hallazgo(FALLA, f"El {tipo} '{_id(x)}' no declara: {', '.join(sorted(set(faltan)))}.", ctx.archivo_inv))
    return out or [Hallazgo(CUMPLE, f"{len(items)} elemento(s) con dueño, versión u origen declarados.")]


def flujo_de_datos(ctx: Contexto) -> List[Hallazgo]:
    if ctx.inventario is None:
        return _sin_inventario(ctx, "los datos que usa cada sistema")
    items = ctx.modelos + ctx.agentes
    if not items:
        return [Hallazgo(NO_APLICA, "No hay modelos ni agentes declarados.")]
    out = []
    for x in items:
        datos = x.get("datos")
        datos = datos if isinstance(datos, list) else ([datos] if datos else [])
        if not datos:
            out.append(Hallazgo(FALLA, f"'{_id(x)}' no declara qué clase de datos usa (datos: publico, interno, personal, sensible).", ctx.archivo_inv))
        elif any(str(d).lower() not in CLASES_DATOS for d in datos):
            out.append(Hallazgo(FALLA, f"'{_id(x)}' usa una clase de datos desconocida: {datos}.", ctx.archivo_inv))
    return out or [Hallazgo(CUMPLE, "Todos los sistemas declaran la clase de datos que usan.")]


def permisos_declarados(ctx: Contexto) -> List[Hallazgo]:
    if ctx.inventario is None:
        return _sin_inventario(ctx, "los permisos de los agentes")
    if not ctx.agentes:
        return [Hallazgo(NO_APLICA, "No hay agentes declarados.")]
    out = []
    for a in ctx.agentes:
        herr = a.get("herramientas")
        perm = str(a.get("permisos") or "").lower()
        if herr is None or not perm:
            out.append(Hallazgo(FALLA, f"El agente '{_id(a)}' no declara herramientas o permisos.", ctx.archivo_inv))
        elif perm in ("amplio", "admin", "administrador", "total", "*"):
            out.append(Hallazgo(FALLA, f"El agente '{_id(a)}' tiene permisos amplios ('{perm}'). Usa permisos mínimos.", ctx.archivo_inv))
        elif isinstance(herr, list) and any(str(h).strip() in ("*", "all", "todas") or "admin" in str(h).lower() for h in herr):
            out.append(Hallazgo(FALLA, f"El agente '{_id(a)}' usa una herramienta de administrador o con comodín.", ctx.archivo_inv))
    return out or [Hallazgo(CUMPLE, "Todos los agentes declaran herramientas y permisos mínimos.")]


PATRONES_SUMINISTRO = [
    (re.compile(r"\bpickle\.loads?\s*\("), FALLA, "pickle.load puede ejecutar código al cargar datos. Evítalo con datos de terceros."),
    (re.compile(r"trust_remote_code\s*=\s*True"), FALLA, "trust_remote_code=True ejecuta código del repositorio del modelo."),
    (re.compile(r"\bjoblib\.load\s*\("), AVISO, "joblib.load usa pickle por dentro. Verifica el origen del archivo."),
]
RE_TORCH_LOAD = re.compile(r"\btorch\.load\s*\(([^)]*)\)")
RE_FROM_PRETRAINED = re.compile(r"\.from_pretrained\s*\(([^)]*)\)", re.S)
EXT_PICKLE = {".pkl", ".pickle"}
EXT_PESOS = {".pt", ".pth", ".ckpt"}


def cadena_de_suministro(ctx: Contexto) -> List[Hallazgo]:
    out: List[Hallazgo] = []
    for p in ctx.archivos():
        suf = p.suffix.lower()
        if suf in EXT_PICKLE:
            out.append(Hallazgo(FALLA, "Archivo pickle: puede ejecutar código al cargarse. Usa safetensors.", ctx.rel(p)))
        elif suf in EXT_PESOS or (p.name.lower().startswith("pytorch_model") and suf == ".bin"):
            out.append(Hallazgo(AVISO, "Pesos en formato basado en pickle. Prefiere safetensors.", ctx.rel(p)))
    for ruta, txt in ctx.textos():
        if ruta.endswith(".md"):
            continue
        for rx, estado, msg in PATRONES_SUMINISTRO:
            for m in rx.finditer(txt):
                out.append(Hallazgo(estado, msg, ruta, _linea(txt, m.start())))
        for m in RE_TORCH_LOAD.finditer(txt):
            if "weights_only=True" not in m.group(1).replace(" ", ""):
                out.append(Hallazgo(AVISO, "torch.load sin weights_only=True (en versiones anteriores a PyTorch 2.6 el valor por defecto es False).",
                                    ruta, _linea(txt, m.start())))
        for m in RE_FROM_PRETRAINED.finditer(txt):
            if "revision" not in m.group(1):
                out.append(Hallazgo(AVISO, "from_pretrained sin revision=: el modelo puede cambiar sin que lo notes. Fija la revisión.", ruta, _linea(txt, m.start())))
    for m in ctx.modelos:
        formato = str(m.get("formato", "")).lower()
        if formato in ("pickle", "pkl", "pt", "pth", "bin", "ckpt"):
            out.append(Hallazgo(FALLA, f"El modelo '{_id(m)}' declara formato {formato}. Prefiere safetensors.", ctx.archivo_inv))
        origen = str(m.get("origen", "")).lower()
        if ("huggingface" in origen or "hf.co" in origen) and not m.get("revision"):
            out.append(Hallazgo(AVISO, f"El modelo '{_id(m)}' viene de un hub público y no fija revision.", ctx.archivo_inv))
    if not out:
        return [Hallazgo(CUMPLE, "No se encontraron cargas inseguras de modelos.")]
    return out


# ---------------------------------------------------------------- ASEGURAR
def guardrails(ctx: Contexto) -> List[Hallazgo]:
    libs = set()
    for ruta, txt in ctx.textos():
        nombre = ruta.lower().rsplit("/", 1)[-1]
        if nombre.startswith("requirements") or nombre in ("pyproject.toml", "package.json", "pipfile", "environment.yml"):
            low = txt.lower()
            libs.update(x for x in LIBS_GUARDRAILS if x in low)
    if ctx.inventario is None:
        if libs:
            return [Hallazgo(AVISO, f"Se encontró librería de guardrails ({', '.join(sorted(libs))}), pero no hay inventario para confirmar entrada y salida.")]
        return [Hallazgo(PENDIENTE, "No se encontró ninguna librería de guardrails ni inventario que declare guardrails.")]
    if not ctx.agentes and not ctx.modelos:
        return [Hallazgo(NO_APLICA, "No hay modelos ni agentes declarados.")]
    sin = []
    for a in ctx.agentes:
        g = a.get("guardrails") or {}
        if not (isinstance(g, dict) and g.get("entrada") is True and g.get("salida") is True):
            sin.append(a)
    if not sin and ctx.agentes:
        return [Hallazgo(CUMPLE, "Todos los agentes declaran guardrails de entrada y de salida.")]
    if not ctx.agentes:
        return [Hallazgo(CUMPLE if libs else PENDIENTE, "Solo hay modelos declarados; revisa guardrails en la aplicación que los usa.")]
    estado = AVISO if libs else FALLA
    pre = f"Hay librería de guardrails ({', '.join(sorted(libs))}), pero " if libs else ""
    return [Hallazgo(estado, f"{pre}el agente '{_id(a)}' no declara guardrails de entrada y de salida.", ctx.archivo_inv) for a in sin]


PATRONES_SECRETOS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "Llave de acceso de AWS"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), "Llave de API (estilo sk-)"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}"), "Token de GitHub"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "Llave de API de Google"),
    (re.compile(r"xox[baprs]-[0-9A-Za-z\-]{10,}"), "Token de Slack"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"), "Llave privada"),
]
RE_ASIGNACION = re.compile(r"""(?i)\b(api[_\-]?key|secret|token|password|passwd|contrase[nñ]a|clave)\b\s*[:=]\s*["']([^"'\s]{12,})["']""")
PLACEHOLDERS = ("example", "ejemplo", "tu_", "your", "changeme", "xxxx", "<", ">", "${", "{{", "placeholder", "dummy",
                "aqui", "aquí", "secret_here", "environ", "getenv")


DIRS_PRUEBA = {"tests", "test", "__tests__", "spec", "fixtures", "mocks", "docs", "doc"}


def es_prueba_o_doc(ruta: str) -> bool:
    """Archivos de pruebas y documentación: ahí los valores fijos casi siempre son datos de ejemplo."""
    partes = ruta.lower().split("/")
    nombre = partes[-1]
    return (any(p in DIRS_PRUEBA for p in partes[:-1]) or nombre.startswith("test_")
            or nombre.endswith(("_test.py", ".test.ts", ".test.js", ".test.tsx", ".spec.ts", ".spec.js", ".md", ".rst")))


def _entropia(s: str) -> float:
    return -sum((s.count(ch) / len(s)) * math.log2(s.count(ch) / len(s)) for ch in set(s)) if s else 0.0


def _parece_secreto(valor: str) -> bool:
    """Un secreto real mezcla letras y números y no parece una palabra: evita falsas alarmas como api_key="provider-key"."""
    return (len(valor) >= 16 and any(ch.isdigit() for ch in valor) and any(ch.isalpha() for ch in valor)
            and _entropia(valor) >= 3.2)


def _mask(s: str) -> str:
    return s[:4] + "***"


def secretos(ctx: Contexto) -> List[Hallazgo]:
    out: List[Hallazgo] = []
    for p in ctx.archivos():
        if p.name == ".env":
            out.append(Hallazgo(FALLA, "Archivo .env en el proyecto: no lo subas al repositorio (usa .env.example sin valores).", ctx.rel(p)))
    for ruta, txt in ctx.textos():
        for rx, nombre in PATRONES_SECRETOS:
            for m in rx.finditer(txt):
                out.append(Hallazgo(FALLA, f"{nombre} expuesta ({_mask(m.group(0))}). Rótala y muévela a una variable de entorno.", ruta, _linea(txt, m.start())))
        if es_prueba_o_doc(ruta):
            continue  # en pruebas y documentación solo se buscan llaves con formato conocido (arriba)
        for m in RE_ASIGNACION.finditer(txt):
            valor = m.group(2)
            if any(ph in valor.lower() for ph in PLACEHOLDERS) or not _parece_secreto(valor):
                continue
            out.append(Hallazgo(FALLA, f"Valor fijo para '{m.group(1)}' ({_mask(valor)}). Usa una variable de entorno.", ruta, _linea(txt, m.start())))
    return out or [Hallazgo(CUMPLE, "No se encontraron llaves, tokens ni contraseñas fijas.")]


def topes(ctx: Contexto) -> List[Hallazgo]:
    if ctx.inventario is None:
        return _sin_inventario(ctx, "los topes de los agentes")
    if not ctx.agentes:
        return [Hallazgo(NO_APLICA, "No hay agentes declarados.")]
    out = []
    for a in ctx.agentes:
        p = a.get("presupuesto")
        ok = isinstance(p, dict) and any(isinstance(p.get(k), (int, float)) and p.get(k) > 0 for k in ("max_tokens", "max_pasos", "max_costo_usd"))
        if not ok:
            out.append(Hallazgo(FALLA, f"El agente '{_id(a)}' no declara tope (max_tokens, max_pasos o max_costo_usd).", ctx.archivo_inv))
    return out or [Hallazgo(CUMPLE, "Todos los agentes declaran un tope de presupuesto.")]


def _criticas(a: dict) -> List[str]:
    herr = a.get("herramientas") or []
    return [str(h) for h in herr if any(c in str(h).lower() for c in HERRAMIENTAS_CRITICAS)] if isinstance(herr, list) else []


def aprobacion_humana(ctx: Contexto) -> List[Hallazgo]:
    if ctx.inventario is None:
        return _sin_inventario(ctx, "la aprobación humana")
    if not ctx.agentes:
        return [Hallazgo(NO_APLICA, "No hay agentes declarados.")]
    out = []
    revisados = 0
    for a in ctx.agentes:
        crit = _criticas(a)
        if not crit:
            continue
        revisados += 1
        if a.get("aprobacion_humana") is not True:
            out.append(Hallazgo(FALLA, f"El agente '{_id(a)}' tiene herramientas críticas ({', '.join(crit)}) sin aprobación humana.", ctx.archivo_inv))
    if out:
        return out
    if revisados == 0:
        return [Hallazgo(CUMPLE, "Ningún agente declara herramientas críticas.")]
    return [Hallazgo(CUMPLE, "Los agentes con herramientas críticas exigen aprobación humana.")]


# ---------------------------------------------------------------- MONITOREAR
def registros(ctx: Contexto) -> List[Hallazgo]:
    if ctx.inventario is None:
        return _sin_inventario(ctx, "los registros")
    if not ctx.agentes:
        return [Hallazgo(NO_APLICA, "No hay agentes declarados.")]
    out = []
    for a in ctx.agentes:
        r = a.get("registros")
        if not isinstance(r, dict) or not r.get("destino"):
            out.append(Hallazgo(FALLA, f"El agente '{_id(a)}' no declara a dónde envía sus registros.", ctx.archivo_inv))
        elif r.get("inmutable") is not True:
            out.append(Hallazgo(FALLA, f"Los registros de '{_id(a)}' no son inmutables: el agente podría alterarlos.", ctx.archivo_inv))
        elif not r.get("evidencia"):
            out.append(Hallazgo(AVISO, f"'{_id(a)}' declara registros inmutables pero sin evidencia (enlace o documento).", ctx.archivo_inv))
    return out or [Hallazgo(CUMPLE, "Todos los agentes declaran registros inmutables con evidencia.")]


def alertas(ctx: Contexto) -> List[Hallazgo]:
    if ctx.inventario is None:
        return _sin_inventario(ctx, "las alertas")
    if not ctx.agentes:
        return [Hallazgo(NO_APLICA, "No hay agentes declarados.")]
    out = [Hallazgo(FALLA, f"El agente '{_id(a)}' no declara alertas por desvíos o abuso.", ctx.archivo_inv)
           for a in ctx.agentes if not a.get("alertas")]
    return out or [Hallazgo(CUMPLE, "Todos los agentes declaran alertas.")]


def razonamiento_y_citas(ctx: Contexto) -> List[Hallazgo]:
    if ctx.inventario is None:
        return _sin_inventario(ctx, "el razonamiento y las citas")
    if not ctx.agentes:
        return [Hallazgo(NO_APLICA, "No hay agentes declarados.")]
    out = []
    for a in ctx.agentes:
        if a.get("registra_razonamiento") is not True:
            out.append(Hallazgo(FALLA, f"El agente '{_id(a)}' no guarda su razonamiento (registra_razonamiento).", ctx.archivo_inv))
        if a.get("usa_rag") is True and a.get("citas") is not True:
            out.append(Hallazgo(FALLA, f"El agente '{_id(a)}' usa RAG pero no cita sus fuentes (citas).", ctx.archivo_inv))
    return out or [Hallazgo(CUMPLE, "Los agentes guardan su razonamiento y citan sus fuentes cuando usan RAG.")]


def _fecha(v) -> Optional[dt.date]:
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v))
    except (TypeError, ValueError):
        return None


def red_team(ctx: Contexto) -> List[Hallazgo]:
    encontrados = []
    for ruta, txt in ctx.textos():
        low = txt.lower()
        nombre = ruta.lower().rsplit("/", 1)[-1]
        if nombre.startswith("promptfooconfig"):
            encontrados.append((ruta, "promptfoo"))
        elif ruta.lower().startswith(".github/workflows/") or nombre.startswith("requirements") or nombre in ("pyproject.toml", "package.json"):
            for h in HERRAMIENTAS_RED_TEAM:
                if h in low:
                    encontrados.append((ruta, h))
    fechas = [(a, _fecha(a.get("ultima_prueba_red_team"))) for a in ctx.agentes if a.get("ultima_prueba_red_team")]
    out: List[Hallazgo] = []
    if encontrados:
        r, h = encontrados[0]
        out.append(Hallazgo(CUMPLE, f"Se encontró {h} en el proyecto.", r))
    for a, f in fechas:
        if f is None:
            out.append(Hallazgo(FALLA, f"La fecha de la última prueba de '{_id(a)}' no es válida (usa AAAA-MM-DD).", ctx.archivo_inv))
        elif (ctx.hoy - f).days > DIAS_RED_TEAM:
            out.append(Hallazgo(FALLA, f"La última prueba de red team de '{_id(a)}' fue hace más de {DIAS_RED_TEAM} días ({f}).", ctx.archivo_inv))
        else:
            out.append(Hallazgo(CUMPLE, f"Última prueba de red team de '{_id(a)}': {f}.", ctx.archivo_inv))
    if any(h.estado == FALLA for h in out):
        return [h for h in out if h.estado == FALLA]
    if out:
        return out
    return [Hallazgo(FALLA, "No hay pruebas de red team: ni herramienta (promptfoo, garak, PyRIT...) ni fecha declarada en el inventario.")]


REGLAS: Dict[str, Callable[[Contexto], List[Hallazgo]]] = {
    "inventario_completo": inventario_completo, "flujo_de_datos": flujo_de_datos, "permisos_declarados": permisos_declarados,
    "cadena_de_suministro": cadena_de_suministro, "guardrails": guardrails, "secretos": secretos, "topes": topes,
    "aprobacion_humana": aprobacion_humana, "registros": registros, "alertas": alertas,
    "razonamiento_y_citas": razonamiento_y_citas, "red_team": red_team,
}


def cargar_inventario(ruta: Path) -> Optional[dict]:
    if not ruta.is_file():
        return None
    data = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}

