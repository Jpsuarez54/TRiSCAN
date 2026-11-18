# -*- coding: utf-8 -*-
"""Genera docs/controles.md a partir de src/triscan/controles.yaml. Ejecútalo desde cualquier carpeta."""
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
controles = yaml.safe_load((RAIZ / "src" / "triscan" / "controles.yaml").read_text(encoding="utf-8"))["controles"]
L = ["# Los 12 controles", "",
     "> Este archivo se genera con `python scripts/generar_controles_md.py`. No lo edites a mano: cambia `src/triscan/controles.yaml`.", "",
     "| ID | Pilar | Fase | Severidad | Control |", "|---|---|---|---|---|"]
for c in controles:
    L.append(f"| [{c['id']}](#{c['id'].lower()}) | {c['pilar']} | {c['fase']} | {c['severidad']} | {c['titulo']} |")
for c in controles:
    r = c["referencias"]
    L += ["", f"## {c['id']}", "", f"**{c['titulo']}**", "",
          f"- **Pilar:** {c['pilar']} · **Fase:** {c['fase']} · **Severidad:** {c['severidad']}",
          f"- **Cómo se revisa:** {'leyendo el proyecto' if c['tipo'] == 'auto' else 'con lo que declaras en ia-inventario.yaml'}",
          f"- **Por qué importa:** {c['por_que']}",
          f"- **Cómo arreglarlo:** {c['arreglo']}",
          f"- **En la charla:** {c['caso']}",
          f"- **Referencias:** OWASP LLM {', '.join(r.get('owasp_llm', []))} · NIST AI RMF {', '.join(r.get('nist_ai_rmf', []))} · ISO/IEC 42001 {r.get('iso_42001', '')}"]
(RAIZ / "docs" / "controles.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("Escribí docs/controles.md")
