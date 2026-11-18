# Publicar en GitHub

Esta guía asume que ya tienes cuenta en GitHub. El repositorio ya tiene git iniciado y un primer commit local.

## Antes de subir (checklist)

- [x] Usuario de GitHub (`Jpsuarez54`) puesto en `README.md`, `CONTRIBUTING.md`, `ejemplos/github-action/triscan.yml` y `src/triscan/reporte.py`.
- [ ] Revisa `LICENSE`: el nombre del titular (ahora "Juan Suárez") y el año.
- [ ] Cambia el correo del commit si no quieres usar el de relleno (`git config user.email`).
- [ ] Ejecuta `python -m pytest` y mira que pasen todas.
- [ ] Las llaves de `ejemplos/proyecto-inseguro/` son falsas a propósito. Si GitHub avisa por ellas al subir, es esperable; puedes permitirlas.

## Subir

1. En GitHub, crea un repositorio vacío llamado `triscan` (sin README ni licencia).
2. En una terminal, dentro de esta carpeta:

```bash
git remote add origin https://github.com/Jpsuarez54/triscan.git
git branch -M main
git push -u origin main
```

## Después de subir

- Activa **Issues** y agrega los temas `ai-trism`, `llm-security`, `owasp`, `espanol`.
- Crea una **versión** (Release) `v0.1.0`.
- Pon el enlace al repositorio en tu charla (código QR en la última diapositiva).
- Opcional: publícalo en PyPI para que se instale con `pip install triscan`.
