# -*- coding: utf-8 -*-
"""Revisión rápida de desarrollo: sintaxis de f-strings compatible con Python 3.9 y JavaScript del informe (si hay motor JS)."""
import ast
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
mal = 0
for p in sorted((RAIZ / "src").rglob("*.py")):
    src = p.read_text(encoding="utf-8-sig")
    ast.parse(src, feature_version=(3, 9))
    for n, linea in enumerate(src.splitlines(), 1):
        # contra-barra dentro de las llaves de una f-string: no permitido antes de Python 3.12
        for m in re.finditer(r"""\bf(['"])(.*?)\1""", linea):
            for llave in re.finditer(r"\{([^{}]*)\}", m.group(2)):
                if "\\" in llave.group(1):
                    mal += 1
                    print(f"{p.name}:{n}: contra-barra dentro de una f-string -> {llave.group(0)[:60]}")
print("Problemas de compatibilidad con 3.9:", mal)
sys.exit(1 if mal else 0)
