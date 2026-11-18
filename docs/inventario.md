# El inventario: `ia-inventario.yaml`

`triscan` no puede adivinar algunas cosas (quién es el dueño de un modelo, si un agente pide aprobación humana...). Esas cosas las **declaras tú** en este archivo, que vive en la raíz de tu proyecto.

No lo escribas desde cero: `triscan descubrir .` detecta modelos, agentes y herramientas en tu código y escribe un borrador; tú completas lo marcado con `COMPLETA`. (`triscan init` crea una plantilla vacía.)

> Lo que declaras **no se verifica** contra la realidad. Por eso hay campos de `evidencia`: enlaza el documento o la configuración que lo prueba.

## Modelos

| Campo | Para qué | Lo revisa |
|---|---|---|
| `id` | Nombre del modelo | todos |
| `dueno` | Persona o equipo responsable | GOB-01 |
| `version` | Versión que usas | GOB-01 |
| `origen` | De dónde viene (`huggingface.co/org/modelo` o `interno`) | GOB-01, SUM-01 |
| `revision` | Commit o etiqueta exacta del modelo | SUM-01 |
| `formato` | `safetensors` es lo recomendado; evita `pickle`, `pt`, `bin` | SUM-01 |
| `datos` | Lista de clases: `publico`, `interno`, `personal`, `sensible` | PRIV-01 |

## Agentes

| Campo | Para qué | Lo revisa |
|---|---|---|
| `id`, `dueno`, `modelo` | Identificación y responsable | GOB-01 |
| `datos` | Clases de datos que toca | PRIV-01 |
| `herramientas` | Lista de lo que puede hacer (`buscar_kb`, `enviar_correo`...) | SEC-01, SEC-04 |
| `permisos` | `minimo` o `amplio` | SEC-01 |
| `aprobacion_humana` | `true` si una persona aprueba las acciones críticas | SEC-04 |
| `presupuesto` | `max_tokens`, `max_pasos` o `max_costo_usd` (al menos uno) | SEC-03 |
| `guardrails` | `{entrada: true, salida: true}` | SEC-02 |
| `registros` | `{destino, inmutable: true, evidencia}` | MON-01 |
| `alertas` | `true` si hay alertas por desvíos o abuso | MON-02 |
| `registra_razonamiento` | `true` si guardas el razonamiento del agente | EXP-01 |
| `usa_rag` / `citas` | Si usas RAG, que cite sus fuentes | EXP-01 |
| `ultima_prueba_red_team` | Fecha `AAAA-MM-DD` (máximo 180 días) | MON-03 |

## Qué herramientas se consideran "críticas"

SEC-04 exige aprobación humana si el nombre de una herramienta contiene alguna de estas palabras: `shell`, `bash`, `exec`, `eval`, `sudo`, `ssh`, `delete`, `borrar`, `eliminar`, `drop`, `pago`, `pagar`, `payment`, `transfer`, `deploy`, `desplegar`, `admin`, `escribir`, `write`, `enviar`, `send`, `mail`, `correo`, `email`, `reembols` (reembolso, reembolsar), `refund` y `cancel`.

Ejemplos completos: [`ejemplos/proyecto-seguro/ia-inventario.yaml`](../ejemplos/proyecto-seguro/ia-inventario.yaml) y [`ejemplos/proyecto-inseguro/ia-inventario.yaml`](../ejemplos/proyecto-inseguro/ia-inventario.yaml).
