@echo off
rem Demo con doble clic: instala triscan, revisa los dos proyectos de ejemplo y abre el informe visual.
chcp 65001 >nul
cd /d "%~dp0.."
echo.
echo === Paso 1: instalando triscan (solo la primera vez) ===
python -m pip install -e . -q
if errorlevel 1 (
  echo No pude instalar. Revisa que Python este instalado: python --version
  pause
  exit /b 1
)
echo.
echo === Paso 2: revisando el proyecto SEGURO de ejemplo ===
python -m triscan scan ejemplos\proyecto-seguro --resumen --sin-abrir -o triscan-reporte\seguro
echo.
echo === Paso 3: revisando el proyecto INSEGURO de ejemplo (se abre el informe visual) ===
python -m triscan scan ejemplos\proyecto-inseguro --falla-en nunca -o triscan-reporte\inseguro
echo.
echo Listo. Para revisar TU proyecto: python -m triscan scan "C:\ruta\a\tu\proyecto"
pause
