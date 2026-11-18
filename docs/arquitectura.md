# Cómo está hecho

```
triscan scan <carpeta>
        │
        ▼
 cli.py ──► motor.ejecutar()
              │  1. carga controles.yaml (los 12 controles)
              │  2. lee ia-inventario.yaml (si existe)
              │  3. por cada control, llama a su regla en reglas.py
              │  4. calcula puntajes por pilar y total
              ▼
        informe (un diccionario)
              │
              ▼
        reporte.py ──► terminal · HTML · Markdown · JSON · SARIF
```

## Los archivos de `src/triscan/`

| Archivo | Qué hace |
|---|---|
| `controles.yaml` | Los 12 controles: texto, severidad, referencias. **Es el corazón del proyecto.** |
| `reglas.py` | Una función por control. Recibe un `Contexto` (carpeta + inventario) y devuelve hallazgos. |
| `motor.py` | Junta controles y reglas, calcula puntajes y el umbral de severidad para CI. |
| `descubrir.py` | Lee el código (Python y JS/TS), detecta modelos, agentes, herramientas y RAG, y escribe el borrador del inventario. Solo propone: nunca asume que algo es seguro. |
| `reporte.py` | Convierte el informe a terminal, HTML, Markdown, JSON y SARIF. |
| `cli.py` | Comandos `scan`, `descubrir`, `init` y `controles`. |
| `plantilla_inventario.yaml` | Lo que copia `triscan init`. |

## Estados de un control

Una regla devuelve una lista de **hallazgos**, cada uno con estado `cumple`, `aviso`, `falla`, `pendiente` o `no_aplica`. El control toma el peor estado: `falla` > `pendiente` > `aviso` > `cumple`.

## Agregar un control

1. Describe el control en `controles.yaml` (id, pilar, fase, severidad, texto, referencias).
2. Escribe la función en `reglas.py` y regístrala en el diccionario `REGLAS`.
3. Agrega pruebas en `tests/` (un caso que falla y uno que cumple).
4. Actualiza los ejemplos y regenera la lista: `python scripts/generar_controles_md.py`.

## Pruebas y revisiones

```bash
pip install -e ".[dev]"
python -m pytest                               # 16 pruebas
python scripts/revisar_compatibilidad.py       # que el código funcione en Python 3.9
python scripts/revisar_informe.py              # HTML bien formado y JavaScript sin errores
```

## Decisiones de diseño

- **Solo una dependencia** (`PyYAML`) para que sea fácil de instalar y revisar.
- **Sin enviar nada a internet**: todo corre en tu máquina.
- **Resultado repetible**: reglas fijas, no un modelo de IA, para que dos ejecuciones den lo mismo.
- **Los secretos nunca se imprimen completos** (`_mask()` en `reglas.py`).
