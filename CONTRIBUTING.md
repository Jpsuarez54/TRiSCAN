# Cómo contribuir

¡Gracias por ayudar! Este proyecto es pequeño a propósito: pocas reglas, bien probadas.

## Preparar el entorno

```bash
git clone https://github.com/Jpsuarez54/triscan
cd triscan
pip install -e ".[dev]"
python -m pytest
```

## Agregar o cambiar una regla

1. Describe el control en `src/triscan/controles.yaml`: `id`, `pilar`, `fase`, `severidad`, `por_que`, `arreglo`, `riesgo` y `referencias`.
2. Escribe la regla en `src/triscan/reglas.py` y regístrala en el diccionario `REGLAS`.
3. Agrega pruebas en `tests/` con **un caso que falla y uno que cumple**. Si encontraste un falso positivo, agrega una prueba que lo evite.
4. Si cambia lo que se declara en el inventario, actualiza `plantilla_inventario.yaml` y los dos ejemplos de `ejemplos/`.

## Criterios

- Cada hallazgo debe decir **qué pasó, dónde y cómo arreglarlo**.
- Nunca imprimas un secreto completo: usa `_mask()`.
- Prefiere pocas reglas con pocos falsos positivos antes que muchas reglas ruidosas.
- Las referencias a marcos (OWASP, NIST, ISO) deben ser verificables. Si no estás seguro de un identificador, usa el nivel general.
- Los textos van en español.

## Antes de abrir un pull request

```bash
python -m pytest
triscan scan ejemplos/proyecto-seguro    # debe seguir cumpliendo
triscan scan ejemplos/proyecto-inseguro  # debe seguir fallando
```

## Seguridad

Si encuentras una vulnerabilidad en `triscan`, escríbeme en privado antes de publicarla.
