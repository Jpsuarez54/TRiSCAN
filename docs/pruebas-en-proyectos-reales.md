# Pruebas en proyectos reales y límites conocidos

## Qué se probó

Además de las pruebas automáticas (29) y de la POC del día 1, se ejecutó `triscan descubrir` y `triscan scan` sobre **tres repositorios públicos reales** que usan IA:

| Repositorio | Archivos | Resultado |
|---|---|---|
| `anthropics/anthropic-quickstarts` | 767 | 55 usos de modelos detectados, sin errores, ~1 s |
| `crewAIInc/crewAI-examples` | 312 | 62 usos (59 agentes), 12 herramientas, 4 modelos; encontró 4 archivos `.pkl` reales; ~0,5 s |
| `openai/openai-agents-python` | 1703 | 217 usos (192 agentes), 78 herramientas, 3 críticas (`send_email`, `submit_refund`, `write_file`); ~7 s |

En los tres, el borrador de inventario salió como YAML válido y `scan` corrió sin errores sobre él.

## Qué se corrigió gracias a esas pruebas

- **Lentitud:** el recorrido de carpetas entraba a `.git` y `node_modules`. Ahora los salta: 3 a 4 veces más rápido.
- **Falsas alarmas de secretos:** marcaba datos de ejemplo en pruebas y documentación (`TOKEN = "test..."`). Ahora, en pruebas y documentación solo avisa por llaves con formato conocido (AWS, GitHub, `sk-`...), y en el resto exige que el valor *parezca* un secreto (letras y números, longitud, aleatoriedad).
- **Modelos mal detectados:** rutas como `./models/x` o prefijos como `anthropic/` se tomaban por modelos, y `anthropic/claude...` se marcaba como de Hugging Face. Corregido.
- **Demasiadas entradas** en repositorios con muchos ejemplos: se agregaron `--agrupar carpeta` y `--excluir`.

## Cómo usarlo en un proyecto grande

```bash
triscan descubrir . --agrupar carpeta --excluir "examples/*" --excluir "docs/*"
```

## Límites que siguen vigentes

- **Detección por patrones:** `descubrir` y las reglas leen texto con expresiones regulares. No entienden el programa. Puede haber falsos positivos y falsos negativos.
- **Lenguajes:** `descubrir` solo mira Python y JavaScript/TypeScript. Las reglas de carga de modelos (`pickle`, `torch.load`, `trust_remote_code`) son de Python. Java, Go, C# y otros no se detectan.
- **Frameworks nuevos o internos:** si tu equipo usa un SDK o una capa propia sobre los modelos, puede no detectarse. Agrégalo a mano en el inventario.
- **Lo declarado no se verifica:** dueños, permisos, aprobación humana, registros inmutables y alertas son declaraciones. Pide evidencia.
- **Proyectos enormes:** se leen como máximo unos 150 MB de texto; si se pasa, el informe lo avisa.
- **Pruebas de compatibilidad:** el código se valida contra la sintaxis de Python 3.9 y las pruebas se ejecutan en 3.13 aquí; las pruebas con 3.9 y 3.11 corren en GitHub Actions (`.github/workflows/ci.yml`) cuando se publique el repositorio.
- **Aún no se probó** con proyectos de tu empresa. Esa es la prueba que más importa: si encuentras algo raro, abre un *issue* con el ejemplo (sin datos sensibles).
