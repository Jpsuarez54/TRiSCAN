# -*- coding: utf-8 -*-
"""triscan descubrir: lee el proyecto, detecta dónde se usa IA y arma un BORRADOR de ia-inventario.yaml.

Es una detección por patrones (expresiones regulares): se equivoca a veces. Por eso solo propone; la persona corrige y completa.
"""
from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from .reglas import HERRAMIENTAS_CRITICAS, IGNORAR_DIRS, MAX_BYTES

EXT_CODIGO = {".py", ".js", ".ts", ".jsx", ".tsx", ".mjs"}
IGNORAR_EXTRA = {"tests", "test", "__tests__", "docs", "examples_old"}

# proveedor -> patrones que indican que el archivo usa un SDK de modelos de lenguaje
SDKS = {
    "openai": r"\bfrom openai import|\bimport openai\b|\bOpenAI\s*\(|\bAzureOpenAI\s*\(|from ['\"]openai['\"]|require\(['\"]openai['\"]\)",
    "anthropic": r"\bimport anthropic\b|\bfrom anthropic import|\bAnthropic\s*\(|@anthropic-ai/sdk",
    "google": r"google\.generativeai|from google import genai|genai\.Client|GenerativeModel\s*\(|@google/generative-ai",
    "langchain": r"\bfrom langchain|\bimport langchain|langchain_(?:openai|anthropic|community|core|google)",
    "llama_index": r"\bllama_index\b|\bllamaindex\b",
    "ollama": r"\bimport ollama\b|\bfrom ollama import",
    "litellm": r"\blitellm\b",
    "cohere": r"\bimport cohere\b|\bfrom cohere import",
    "mistral": r"\bmistralai\b",
    "bedrock": r"bedrock[-_]runtime|\bBedrockChat\b|\bChatBedrock\b",
}
AGENTES_FW = r"\bAgentExecutor\b|\binitialize_agent\b|\bcreate_react_agent\b|\bcreate_tool_calling_agent\b|\blanggraph\b|\bcrewai\b|\bautogen\b|\bsmolagents\b|from agents import|\bcreate_openai_functions_agent\b"
LLAMA_TOOLS = r"\btools\s*=\s*[\[\w]|\btools\s*:\s*\["
RAG = re.compile(r"\bchromadb\b|\bfaiss\b|\bpinecone\b|\bweaviate\b|\bqdrant\b|\bpgvector\b|\bas_retriever\b|\bsimilarity_search\b|\bVectorStore\b|\bChroma\s*\(", re.I)
RE_MODELO = re.compile(r"""\bmodel(?:_name|_id)?\s*[=:]\s*["']([A-Za-z0-9_\-./:]+)["']""")
RE_PRETRAINED = re.compile(r"""\.from_pretrained\s*\(\s*["']([A-Za-z0-9_\-./]+)["']([^)]*)\)""", re.S)
RE_TOOL_DECORADOR = re.compile(r"@tool(?:\([^)]*\))?\s*\n\s*(?:async\s+)?def\s+(\w+)")
RE_TOOL_CLASE = re.compile(r"""\b(?:Tool|StructuredTool|DynamicTool)\s*(?:\.from_function)?\(\s*(?:[^)]*?)\bname\s*[=:]\s*["']([A-Za-z_][\w\-]*)["']""", re.S)
RE_NOMBRE_FUNCION = re.compile(r"""["']name["']\s*:\s*["']([A-Za-z_][\w\-]*)["']""")
RE_REVISION = re.compile(r"""revision\s*=\s*["']([^"']+)["']""")
PISTAS_MODELO = ("gpt", "claude", "gemini", "llama", "mistral", "mixtral", "qwen", "phi-", "gemma", "deepseek", "command", "titan", "nova",
                 "sonnet", "haiku", "opus", "embedding")
RE_O_SERIE = re.compile(r"^o[134](-|$)")
RE_ORG_NOMBRE = re.compile(r"^[A-Za-z0-9][\w.\-]*/[A-Za-z0-9][\w.\-]*$")
PROVEEDORES_RUTA = {"openai", "anthropic", "gemini", "google", "azure", "bedrock", "vertex_ai", "mistral", "cohere", "ollama", "groq",
                    "openrouter", "together_ai", "xai", "deepseek", "litellm", "litellm_proxy", "any-llm", "fireworks_ai", "perplexity", "watsonx", "sagemaker"}
PROVEEDOR_POR_NOMBRE = (("gpt", "openai"), ("claude", "anthropic"),
                        ("sonnet", "anthropic"), ("haiku", "anthropic"), ("opus", "anthropic"), ("gemini", "google"),
                        ("mistral", "mistral"), ("mixtral", "mistral"), ("command", "cohere"), ("llama", "meta/ollama"))


@dataclass
class Uso:
    archivo: str
    ident: str = ""
    proveedores: Set[str] = field(default_factory=set)
    agente: bool = False
    herramientas: List[str] = field(default_factory=list)
    modelos: List[str] = field(default_factory=list)
    rag: bool = False


@dataclass
class Descubrimiento:
    usos: List[Uso] = field(default_factory=list)
    modelos: Dict[str, dict] = field(default_factory=dict)
    archivos_revisados: int = 0

    @property
    def herramientas(self) -> List[str]:
        return sorted({h for u in self.usos for h in u.herramientas})

    @property
    def criticas(self) -> List[str]:
        return [h for h in self.herramientas if _es_critica(h)]


def _es_critica(nombre: str) -> bool:
    return any(c in nombre.lower() for c in HERRAMIENTAS_CRITICAS)


def _parece_modelo(s: str) -> bool:
    low = s.lower()
    if len(s) < 3 or s.startswith((".", "/", "~")) or s.endswith("/") or "\\" in s:
        return False
    if any(p in low for p in PISTAS_MODELO) or RE_O_SERIE.match(low):
        return True
    return bool(RE_ORG_NOMBRE.match(s)) and not low.endswith((".py", ".json", ".pkl", ".pt", ".bin", ".txt", ".yaml", ".yml", ".md"))


def _origen(mid: str, provs: Set[str], texto: str) -> str:
    primero = mid.split("/")[0].lower()
    if "/" in mid and primero in PROVEEDORES_RUTA:
        return f"api:{primero}"
    if "/" in mid:
        if RE_ORG_NOMBRE.match(mid) and re.search(r"huggingface|transformers|from_pretrained|sentence_transformers", texto):
            return f"huggingface.co/{mid}"
        return "api:desconocido"
    return f"api:{_proveedor(mid, provs)}"


def _proveedor(modelo: str, en_archivo: Set[str]) -> str:
    low = modelo.lower()
    for pista, prov in PROVEEDOR_POR_NOMBRE:
        if low.startswith(pista) or pista in low:
            return prov
    return sorted(en_archivo - {"langchain"})[0] if en_archivo - {"langchain"} else "desconocido"


def _linea(texto: str, pos: int) -> int:
    return texto.count("\n", 0, pos) + 1


def _excluido(rel: str, patrones) -> bool:
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(rel, p.rstrip("/") + "/*") for p in patrones)


def _archivos_de_codigo(raiz: Path):
    for carpeta, dirs, nombres in os.walk(raiz):
        dirs[:] = sorted(x for x in dirs if x not in IGNORAR_DIRS and x not in IGNORAR_EXTRA and not x.endswith(".egg-info"))
        for n in sorted(nombres):
            p = Path(carpeta) / n
            if p.suffix.lower() in EXT_CODIGO:
                yield p


def _agrupar_por_carpeta(usos: List[Uso]) -> List[Uso]:
    grupos: Dict[str, Uso] = {}
    for u in usos:
        carpeta = u.archivo.rsplit("/", 1)[0] if "/" in u.archivo else ""
        g = grupos.setdefault(carpeta, Uso(archivo=(carpeta + "/") if carpeta else "(raíz)", ident=carpeta or "raiz"))
        g.proveedores |= u.proveedores
        g.agente = g.agente or u.agente
        g.rag = g.rag or u.rag
        g.herramientas = list(dict.fromkeys(g.herramientas + u.herramientas))
        g.modelos = list(dict.fromkeys(g.modelos + u.modelos))
    return list(grupos.values())


def analizar(raiz, excluir=(), agrupar: str = "archivo") -> Descubrimiento:
    raiz = Path(raiz).resolve()
    d = Descubrimiento()
    for p in _archivos_de_codigo(raiz):
        rel = p.relative_to(raiz).as_posix()
        try:
            if p.stat().st_size > MAX_BYTES or _excluido(rel, excluir):
                continue
            texto = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        d.archivos_revisados += 1
        # modelos del hub (from_pretrained): aunque el archivo no use un SDK de lenguaje
        for m in RE_PRETRAINED.finditer(texto):
            mid = m.group(1)
            if _parece_modelo(mid) or "/" in mid:
                rev = RE_REVISION.search(m.group(2))
                info = d.modelos.setdefault(mid, {"origen": f"huggingface.co/{mid}", "archivos": set()})
                info["archivos"].add(rel)
                if rev:
                    info["revision"] = rev.group(1)
        provs = {k for k, rx in SDKS.items() if re.search(rx, texto)}
        agente_fw = bool(re.search(AGENTES_FW, texto))
        if not provs and not agente_fw:
            continue
        uso = Uso(archivo=rel, proveedores=provs)
        for rx in (RE_TOOL_DECORADOR, RE_TOOL_CLASE):
            uso.herramientas += [m.group(1) for m in rx.finditer(texto)]
        if re.search(LLAMA_TOOLS, texto) or '"type": "function"' in texto or "'type': 'function'" in texto:
            uso.herramientas += [m.group(1) for m in RE_NOMBRE_FUNCION.finditer(texto)]
            uso.agente = True
        uso.herramientas = list(dict.fromkeys(uso.herramientas))
        uso.agente = uso.agente or agente_fw or bool(uso.herramientas)
        uso.rag = bool(RAG.search(texto))
        for m in RE_MODELO.finditer(texto):
            mid = m.group(1)
            if _parece_modelo(mid) and mid not in uso.modelos:
                uso.modelos.append(mid)
                if mid not in d.modelos:
                    d.modelos[mid] = {"origen": _origen(mid, provs, texto), "archivos": {rel}}
                else:
                    d.modelos[mid]["archivos"].add(rel)
        d.usos.append(uso)
    if agrupar == "carpeta":
        d.usos = _agrupar_por_carpeta(d.usos)
    return d


def _id_agente(u: "Uso") -> str:
    return u.ident or re.sub(r"\.(py|js|ts|jsx|tsx|mjs)$", "", u.archivo)


def borrador_yaml(d: Descubrimiento, proyecto: str = "mi-proyecto") -> str:
    L = ["# ia-inventario.yaml · BORRADOR generado por `triscan descubrir`.",
         "# Detecta patrones en el código: puede equivocarse o dejar cosas fuera. Revísalo.",
         "# Lo marcado con 'COMPLETA' solo lo puedes saber tú. Cuando termines: triscan scan .",
         "version: 1", f"proyecto: {proyecto}", "", "modelos:"]
    if not d.modelos:
        L.append("  []                        # no detecté modelos; agrégalos a mano si usas alguno")
    for mid, info in sorted(d.modelos.items()):
        L += [f"  - id: {mid}", f"    dueno:                      # COMPLETA: persona o equipo responsable",
              "    version:                    # COMPLETA: versión o fecha del modelo",
              f"    origen: {info['origen']}"]
        if info["origen"].startswith("huggingface"):
            L.append(f"    revision: {info.get('revision', '')}   # " + ("fijada en el código" if info.get("revision") else "COMPLETA: commit exacto del modelo"))
            L.append("    formato:                    # COMPLETA: safetensors (recomendado), pickle, pt...")
        L += ["    datos: []                   # COMPLETA: publico | interno | personal | sensible",
              f"    # visto en: {', '.join(sorted(info['archivos']))}"]
    L += ["", "agentes:"]
    if not d.usos:
        L.append("  []                        # no detecté agentes ni aplicaciones que usen modelos de lenguaje")
    for u in d.usos:
        criticas = [h for h in u.herramientas if _es_critica(h)]
        L += [f"  - id: {_id_agente(u)}", f"    tipo: {'agente' if u.agente else 'aplicacion'}", f"    archivo: {u.archivo}",
              "    dueno:                      # COMPLETA: persona o equipo responsable",
              f"    modelo: {u.modelos[0] if u.modelos else ''}" + ("" if u.modelos else "   # COMPLETA: id de un modelo de la lista de arriba"),
              "    datos: []                   # COMPLETA: publico | interno | personal | sensible"]
        if u.herramientas:
            L.append("    herramientas: [" + ", ".join(u.herramientas) + "]")
        else:
            L.append("    herramientas: []")
        L.append("    permisos:                   # COMPLETA: minimo | amplio")
        if criticas:
            L.append(f"    aprobacion_humana: false    # ATENCIÓN: herramientas críticas ({', '.join(criticas)}). ¿Una persona aprueba cada acción? Cambia a true solo si es cierto")
        else:
            L.append("    aprobacion_humana: false    # cámbialo a true si una persona aprueba las acciones del agente")
        if u.rag:
            L += ["    usa_rag: true", "    citas:                      # COMPLETA: true si las respuestas citan sus fuentes"]
        L += ["    # Faltan por declarar (ver docs/inventario.md): presupuesto, guardrails, registros, alertas, registra_razonamiento",
              "    presupuesto: {}             # COMPLETA: max_tokens, max_pasos o max_costo_usd",
              "    guardrails: {entrada: false, salida: false}   # COMPLETA",
              "    registros: {}               # COMPLETA: destino, inmutable, evidencia",
              "    alertas: false              # COMPLETA", "    registra_razonamiento: false   # COMPLETA", ""]
    return "\n".join(L).rstrip() + "\n"


def resumen(d: Descubrimiento) -> str:
    n_ag = sum(1 for u in d.usos if u.agente)
    n_ap = len(d.usos) - n_ag
    crit = d.criticas
    lineas = [f"Revisé {d.archivos_revisados} archivo(s) de código.",
              f"Encontré: {len(d.modelos)} modelo(s) · {n_ag} agente(s) · {n_ap} aplicación(es) que usan modelos de lenguaje.",
              f"Herramientas de agentes: {len(d.herramientas)}" + (f" ({len(crit)} crítica(s): {', '.join(crit)})" if crit else "") + ".",
              f"Usa RAG (base de conocimiento): {'sí' if any(u.rag for u in d.usos) else 'no'}."]
    return "\n".join(lineas)
