# Empezar en 5 minutos

Necesitas **Python 3.9 o superior** (`python --version`).

## Opción A: demo con doble clic (Windows)

1. Abre la carpeta `scripts/`.
2. Haz doble clic en `probar.bat`.
3. Se revisan dos proyectos de ejemplo y se abre un informe en el navegador.

## Opción B: con comandos

```bash
# 1. Instalar (desde la carpeta del repositorio)
pip install -e .

# 2. Probar con los ejemplos
triscan scan ejemplos/proyecto-inseguro     # falla los 12 controles
triscan scan ejemplos/proyecto-seguro       # cumple los 12
```

Cada `scan` imprime un resumen en la terminal y abre el **informe visual** (`triscan-reporte/reporte.html`).

Si `triscan` no se reconoce, usa `python -m triscan` en su lugar.

## Revisar tu propio proyecto

```bash
cd ruta/a/tu/proyecto
triscan descubrir .   # lee tu código y escribe un BORRADOR de ia-inventario.yaml
# abre ia-inventario.yaml y completa lo marcado con COMPLETA (ver inventario.md)
triscan scan .        # resumen en la terminal + informe visual en el navegador
```

Si tu proyecto no usa IA todavía, o prefieres empezar de cero, `triscan init` crea una plantilla vacía en lugar del borrador.

¿Quieres ver este recorrido completo en un proyecto real? Ejecuta la POC: [poc-dia-1.md](poc-dia-1.md).

## Qué significan los resultados

| Estado | Significa |
|---|---|
| **Cumple** | El control está bien |
| **Con avisos** | Cumple, pero hay algo que conviene revisar |
| **Falla** | Falta el control o hay un problema. Mira "Cómo arreglarlo" |
| **Pendiente** | No se pudo revisar: falta información (normalmente, el inventario) |

El puntaje es `cumplen / (cumplen + fallan)`. Lo pendiente no suma ni resta, pero cuenta como trabajo por hacer.

## Usarlo en cada cambio de código

Copia [`ejemplos/github-action/triscan.yml`](../ejemplos/github-action/triscan.yml) a `.github/workflows/` de tu proyecto. Si un control importante falla, el cambio se bloquea.
