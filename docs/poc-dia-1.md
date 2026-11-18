# POC del día 1: cómo se usa en un proyecto real

Esta POC recorre lo que haría una persona el primer día con `triscan`, sobre un proyecto que **ya usa IA y no tiene inventario**: un agente de soporte al cliente con OpenAI, base de conocimiento (Chroma) y un clasificador de Hugging Face.

## Ejecutarla

- Windows: doble clic en `scripts\poc-dia1.bat`.
- Cualquier sistema: `python scripts/poc_dia1.py` (agrega `--auto` para no pausar entre pasos).

Trabaja en una copia dentro de `poc-trabajo/`; el ejemplo original no se modifica. Al final abre `poc-trabajo/resumen.html`.

## Lo que pasa, paso a paso

| Paso | Qué haces | Tiempo | Cumplen | Fallan | Pendientes |
|---|---|---|---|---|---|
| 1 | `triscan scan .` en el proyecto tal cual | 0 min | 1/12 | 3 | 8 |
| 2 | `triscan descubrir .` escribe el borrador del inventario | 2 min | 1/12 | 11 | 0 |
| 3 | Completas el borrador con lo que solo tú sabes | 10 min | 3/12 | 9 | 0 |
| 4 | Arreglas lo que falló y actualizas el inventario | trabajo del equipo | 12/12 | 0 | 0 |

Lo importante de cada paso:

1. **Sin inventario casi nada se puede revisar** (8 pendientes), pero ya aparecen una llave fija en el código y un archivo `.env`.
2. **`descubrir`** lee el código y detecta: 2 modelos (`gpt-4o-mini` y `org/clasificador-tickets`), 1 agente, 4 herramientas (2 críticas: `enviar_correo_cliente` y `reembolsar_pedido`) y que usa RAG. Deja el borrador con `COMPLETA` en cada campo que solo la persona sabe. **No asume nada a favor**: `aprobacion_humana` queda en `false` hasta que la persona confirme.
3. **Completar el borrador revela la verdad**: pasan de 1 a 3 controles porque ahora hay dueños y clases de datos, pero aparecen 9 fallas reales (permisos amplios, sin tope, sin guardrails, sin aprobación humana...). Aquí está el valor: la persona ve lo que antes no veía.
4. **Los arreglos** (carpeta `ejemplos/poc-app-soporte/arreglos-paso-4/`): llave fuera del código, `.env` eliminado, modelo fijado con `revision` y `safetensors`, `llm-guard`, tope de pasos, aprobación humana para acciones críticas, registro del razonamiento y pruebas con promptfoo.

## Qué es de verdad automático y qué no

- **Automático:** detectar modelos, agentes, herramientas y RAG; encontrar llaves, `.env`, `pickle`, `trust_remote_code`; ver librerías de guardrails y pruebas de red team.
- **Lo declara la persona (y no se verifica):** dueños, clases de datos, permisos, aprobación humana, topes, registros inmutables, alertas, razonamiento. El paso 4 de esta POC *simula* que esas declaraciones son ciertas porque el código de ejemplo cambió. En un proyecto real, pide evidencia.

## Límites de `descubrir`

Busca patrones en Python y JavaScript/TypeScript (SDK de OpenAI, Anthropic, Google, LangChain, LlamaIndex, Ollama, LiteLLM, Cohere, Mistral, Bedrock; `from_pretrained`; herramientas con `@tool`, `Tool(name=...)` o definiciones de funciones). Puede equivocarse o dejar cosas fuera. Por eso escribe un **borrador** y nunca pisa un `ia-inventario.yaml` que ya exista (en ese caso crea `ia-inventario.borrador.yaml`).
