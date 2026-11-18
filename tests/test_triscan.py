# -*- coding: utf-8 -*-
import datetime as dt
import json
from pathlib import Path

import pytest
import yaml

from triscan import cli, motor
from triscan.reglas import REGLAS

RAIZ = Path(__file__).resolve().parents[1]
EJ = RAIZ / "ejemplos"
HOY = dt.date(2026, 11, 18)


def estado(inf, id_):
    return next(c["estado"] for c in inf["controles"] if c["id"] == id_)


def test_hay_12_controles_con_regla():
    cs = motor.cargar_controles()
    assert len(cs) == 12
    assert len({c["id"] for c in cs}) == 12
    assert all(c["regla"] in REGLAS for c in cs)
    assert {c["pilar"] for c in cs} == set(motor.PILARES)


def test_proyecto_seguro_cumple_todo():
    inf = motor.ejecutar(EJ / "proyecto-seguro", hoy=HOY)
    assert inf["conteo"]["falla"] == 0, [c["id"] for c in inf["controles"] if c["estado"] == "falla"]
    assert inf["conteo"]["pendiente"] == 0
    assert inf["puntaje_total"] == 100


def test_proyecto_inseguro_falla_donde_debe():
    inf = motor.ejecutar(EJ / "proyecto-inseguro", hoy=HOY)
    for id_ in ("GOB-01", "PRIV-01", "SEC-01", "SUM-01", "SEC-02", "PRIV-02", "SEC-03", "SEC-04", "MON-01", "MON-02", "EXP-01", "MON-03"):
        assert estado(inf, id_) == "falla", id_
    assert inf["puntaje_total"] == 0


def test_los_secretos_se_enmascaran():
    inf = motor.ejecutar(EJ / "proyecto-inseguro", hoy=HOY)
    texto = json.dumps(inf, ensure_ascii=False)
    assert "AKIAIOSFODNN7EXAMPLE" not in texto
    assert "sk-test-0000000000000000000000000000" not in texto
    assert "AKIA***" in texto


def test_sin_inventario(tmp_path):
    inf = motor.ejecutar(tmp_path, hoy=HOY)
    assert estado(inf, "GOB-01") == "falla"
    assert estado(inf, "SEC-01") == "pendiente"
    assert estado(inf, "PRIV-02") == "cumple"


def _inv(tmp_path, agente_extra):
    base = {"version": 1, "modelos": [], "agentes": [dict({"id": "a", "dueno": "x@y.com", "modelo": "m"}, **agente_extra)]}
    (tmp_path / "ia-inventario.yaml").write_text(yaml.safe_dump(base), encoding="utf-8")
    return tmp_path


def test_red_team_fecha_vieja_y_reciente(tmp_path):
    inf = motor.ejecutar(_inv(tmp_path, {"ultima_prueba_red_team": "2025-01-01"}), hoy=HOY)
    assert estado(inf, "MON-03") == "falla"
    inf = motor.ejecutar(_inv(tmp_path, {"ultima_prueba_red_team": "2026-10-01"}), hoy=HOY)
    assert estado(inf, "MON-03") == "cumple"


def test_herramienta_critica_exige_aprobacion(tmp_path):
    inf = motor.ejecutar(_inv(tmp_path, {"herramientas": ["borrar_registros"]}), hoy=HOY)
    assert estado(inf, "SEC-04") == "falla"
    inf = motor.ejecutar(_inv(tmp_path, {"herramientas": ["borrar_registros"], "aprobacion_humana": True}), hoy=HOY)
    assert estado(inf, "SEC-04") == "cumple"


def test_pickle_y_trust_remote_code(tmp_path):
    (tmp_path / "x.py").write_text("import pickle\npickle.load(f)\nm.from_pretrained('a/b', trust_remote_code=True)\n", encoding="utf-8")
    inf = motor.ejecutar(tmp_path, hoy=HOY)
    mensajes = " ".join(h["mensaje"] for c in inf["controles"] if c["id"] == "SUM-01" for h in c["hallazgos"])
    assert "pickle" in mensajes and "trust_remote_code" in mensajes
    assert estado(inf, "SUM-01") == "falla"


def test_placeholders_no_son_secretos(tmp_path):
    (tmp_path / "x.py").write_text('api_key = "tu_llave_aqui_123456"\ntoken = os.environ["TOKEN"]\n', encoding="utf-8")
    assert estado(motor.ejecutar(tmp_path, hoy=HOY), "PRIV-02") == "cumple"


def test_umbral():
    inf = motor.ejecutar(EJ / "proyecto-inseguro", hoy=HOY)
    assert motor.supera_umbral(inf, "critica") and motor.supera_umbral(inf, "baja")
    assert not motor.supera_umbral(inf, "nunca")
    assert not motor.supera_umbral(motor.ejecutar(EJ / "proyecto-seguro", hoy=HOY), "baja")


def test_codigos_de_salida(capsys):
    assert cli.main(["scan", str(EJ / "proyecto-inseguro"), "--hoy", "2026-11-18", "--silencioso"]) == 1
    assert cli.main(["scan", str(EJ / "proyecto-inseguro"), "--hoy", "2026-11-18", "--silencioso", "--falla-en", "nunca"]) == 0
    assert cli.main(["scan", str(EJ / "proyecto-seguro"), "--hoy", "2026-11-18", "--silencioso"]) == 0
    assert cli.main(["scan", str(EJ / "no-existe")]) == 2


def test_formatos_de_salida(tmp_path):
    out = tmp_path / "rep"
    args = ["scan", str(EJ / "proyecto-inseguro"), "--hoy", "2026-11-18", "--silencioso", "--falla-en", "nunca", "-o", str(out)]
    for f in ("md", "html", "json", "sarif"):
        args += ["-f", f]
    assert cli.main(args) == 0
    sarif = json.loads((out / "triscan.sarif").read_text(encoding="utf-8"))
    assert sarif["version"] == "2.1.0"
    assert len(sarif["runs"][0]["tool"]["driver"]["rules"]) == 12
    assert sarif["runs"][0]["results"]
    assert all(r["locations"] for r in sarif["runs"][0]["results"])
    assert json.loads((out / "reporte.json").read_text(encoding="utf-8"))["version"]
    html = (out / "reporte.html").read_text(encoding="utf-8")
    assert "<html" in html and "SEC-04" in html
    assert "# Informe TRiScan" in (out / "reporte.md").read_text(encoding="utf-8")


def test_init_crea_inventario_escaneable(tmp_path):
    assert cli.main(["init", str(tmp_path)]) == 0
    assert cli.main(["init", str(tmp_path)]) == 2  # ya existe
    inf = motor.ejecutar(tmp_path, hoy=HOY)
    assert estado(inf, "GOB-01") == "cumple"
    assert estado(inf, "SEC-04") == "cumple"


def test_por_defecto_genera_html_y_lo_abre(tmp_path, monkeypatch):
    abiertos = []
    monkeypatch.setattr(cli.webbrowser, "open", lambda u: abiertos.append(u) or True)
    monkeypatch.delenv("CI", raising=False)
    assert cli.main(["scan", str(EJ / "proyecto-seguro"), "--hoy", "2026-11-18", "-o", str(tmp_path / "r")]) == 0
    assert (tmp_path / "r" / "reporte.html").exists()
    assert len(abiertos) == 1 and abiertos[0].startswith("file:")


def test_sin_abrir_y_en_ci_no_abre(tmp_path, monkeypatch):
    abiertos = []
    monkeypatch.setattr(cli.webbrowser, "open", lambda u: abiertos.append(u) or True)
    monkeypatch.delenv("CI", raising=False)
    cli.main(["scan", str(EJ / "proyecto-seguro"), "--hoy", "2026-11-18", "--sin-abrir", "-o", str(tmp_path / "a")])
    monkeypatch.setenv("CI", "true")
    cli.main(["scan", str(EJ / "proyecto-seguro"), "--hoy", "2026-11-18", "-o", str(tmp_path / "b")])
    assert abiertos == []
    assert (tmp_path / "a" / "reporte.html").exists() and (tmp_path / "b" / "reporte.html").exists()


def test_informe_visual():
    from triscan import reporte
    malo = reporte.html_(motor.ejecutar(EJ / "proyecto-inseguro", hoy=HOY))
    bueno = reporte.html_(motor.ejecutar(EJ / "proyecto-seguro", hoy=HOY))
    for esperado in ("Lo más urgente", "Cómo arreglarlo", 'data-estado="falla"', "<details", "Brecha importante", 'id="SEC-04"', "data-count"):
        assert esperado in malo, esperado
    assert "Buen punto de partida" in bueno and "Lo más urgente" not in bueno
    assert "<script>" in malo and "</html>" in malo
    assert "AKIAIOSFODNN7EXAMPLE" not in malo


# ---------------------------------------------------------------- descubrir y POC del día 1
import importlib.util  # noqa: E402
import shutil  # noqa: E402

from triscan import descubrir  # noqa: E402

APP = EJ / "poc-app-soporte" / "app-original"


def test_descubrir_detecta_la_app_real():
    d = descubrir.analizar(APP)
    assert set(d.modelos) == {"gpt-4o-mini", "org/clasificador-tickets"}
    assert d.modelos["gpt-4o-mini"]["origen"] == "api:openai"
    assert d.modelos["org/clasificador-tickets"]["origen"].startswith("huggingface.co/")
    assert len(d.usos) == 1 and d.usos[0].archivo == "app/agente.py"
    assert d.usos[0].agente and d.usos[0].rag
    assert d.herramientas == sorted(["buscar_en_base_conocimiento", "consultar_pedido", "enviar_correo_cliente", "reembolsar_pedido"])
    assert set(d.criticas) == {"enviar_correo_cliente", "reembolsar_pedido"}


def test_borrador_es_yaml_valido_y_conservador():
    d = descubrir.analizar(APP)
    texto = descubrir.borrador_yaml(d, "app")
    data = yaml.safe_load(texto)
    assert len(data["modelos"]) == 2 and len(data["agentes"]) == 1
    ag = data["agentes"][0]
    assert ag["id"] == "app/agente" and ag["modelo"] == "gpt-4o-mini" and ag["usa_rag"] is True
    assert ag["aprobacion_humana"] is False          # por defecto NO se asume que hay aprobación
    assert ag["dueno"] is None and ag["permisos"] is None
    assert "COMPLETA" in texto and "ATENCIÓN" in texto


def test_cli_descubrir_no_pisa_el_inventario(tmp_path):
    shutil.copytree(APP, tmp_path / "p")
    p = tmp_path / "p"
    assert cli.main(["descubrir", str(p)]) == 0
    assert (p / "ia-inventario.yaml").exists()
    original = (p / "ia-inventario.yaml").read_text(encoding="utf-8")
    (p / "ia-inventario.yaml").write_text(original + "\n# editado por la persona\n", encoding="utf-8")
    assert cli.main(["descubrir", str(p)]) == 0
    assert (p / "ia-inventario.borrador.yaml").exists()
    assert "# editado por la persona" in (p / "ia-inventario.yaml").read_text(encoding="utf-8")


def test_descubrir_proyecto_sin_ia(tmp_path):
    (tmp_path / "x.py").write_text("print('hola')\n", encoding="utf-8")
    assert cli.main(["descubrir", str(tmp_path)]) == 0
    data = yaml.safe_load((tmp_path / "ia-inventario.yaml").read_text(encoding="utf-8"))
    assert data["modelos"] == [] and data["agentes"] == []


def test_permisos_vacios_fallan(tmp_path):
    inf = motor.ejecutar(_inv(tmp_path, {"herramientas": ["buscar"], "permisos": None}), hoy=HOY)
    assert estado(inf, "SEC-01") == "falla"


def test_herramientas_de_dinero_son_criticas(tmp_path):
    inf = motor.ejecutar(_inv(tmp_path, {"herramientas": ["reembolsar_pedido"]}), hoy=HOY)
    assert estado(inf, "SEC-04") == "falla"


def test_poc_dia1_mejora_paso_a_paso(tmp_path):
    spec = importlib.util.spec_from_file_location("poc_dia1", RAIZ / "scripts" / "poc_dia1.py")
    poc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(poc)
    pasos = poc.main(["--auto", "--sin-abrir", "--trabajo", str(tmp_path / "w")])
    cumplen = [p["cumplen"] for p in pasos]
    assert cumplen == sorted(cumplen) and cumplen[-1] == 12 and cumplen[0] <= 3
    assert pasos[0]["pendientes"] >= 5            # sin inventario casi nada se puede revisar
    assert pasos[1]["pendientes"] == 0            # el borrador ya permite revisar los 12
    assert (tmp_path / "w" / "resumen.html").exists()


# ---------------------------------------------------------------- robustez en proyectos reales
def test_no_entra_a_node_modules_ni_git(tmp_path):
    (tmp_path / "node_modules" / "paquete").mkdir(parents=True)
    (tmp_path / "node_modules" / "paquete" / "x.js").write_text('const k = "AKIAIOSFODNN7EXAMPLE";\n', encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config.txt").write_text("AKIAIOSFODNN7EXAMPLE\n", encoding="utf-8")
    assert estado(motor.ejecutar(tmp_path, hoy=HOY), "PRIV-02") == "cumple"


def test_secretos_en_pruebas_y_docs_no_son_alarma_pero_las_llaves_reales_si(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text('TOKEN = "test-token-value-123456"\nsecret = "integration-secret"\n', encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guia.md").write_text('api_key = "provider-key-abcdef123456"\n', encoding="utf-8")
    assert estado(motor.ejecutar(tmp_path, hoy=HOY), "PRIV-02") == "cumple"
    (tmp_path / "tests" / "test_y.py").write_text('K = "AKIAIOSFODNN7EXAMPLE"\n', encoding="utf-8")  # formato real de llave: siempre se avisa
    assert estado(motor.ejecutar(tmp_path, hoy=HOY), "PRIV-02") == "falla"


def test_valores_que_parecen_palabras_no_son_secretos(tmp_path):
    (tmp_path / "app.py").write_text('api_key = "provider-key-no-es-secreto"\ntoken = "una-palabra-larga-sin-numeros"\n', encoding="utf-8")
    assert estado(motor.ejecutar(tmp_path, hoy=HOY), "PRIV-02") == "cumple"
    (tmp_path / "app.py").write_text('api_key = "a8F3kL9x2QpZ7mR4tY6w"\n', encoding="utf-8")
    assert estado(motor.ejecutar(tmp_path, hoy=HOY), "PRIV-02") == "falla"


def test_descubrir_no_confunde_rutas_con_modelos(tmp_path):
    (tmp_path / "a.py").write_text(
        'from openai import OpenAI\nc = OpenAI()\nc.chat(model="gpt-4o-mini")\nx = dict(model="./models/mi/archivo")\n'
        'y = dict(model="anthropic/")\nz = dict(model="litellm/anthropic/claude-3-5-sonnet")\nw = dict(model="o1-mini")\nv = dict(model="demo1")\n', encoding="utf-8")
    d = descubrir.analizar(tmp_path)
    assert set(d.modelos) == {"gpt-4o-mini", "litellm/anthropic/claude-3-5-sonnet", "o1-mini"}
    assert d.modelos["litellm/anthropic/claude-3-5-sonnet"]["origen"] == "api:litellm"
    assert d.modelos["gpt-4o-mini"]["origen"] == "api:openai"


def test_descubrir_agrupar_por_carpeta_y_excluir(tmp_path):
    for nombre in ("uno", "dos"):
        (tmp_path / "svc" / nombre).mkdir(parents=True)
        for i in range(2):
            (tmp_path / "svc" / nombre / f"m{i}.py").write_text('from openai import OpenAI\nOpenAI().chat(model="gpt-4o")\n', encoding="utf-8")
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "demo.py").write_text('from openai import OpenAI\nOpenAI()\n', encoding="utf-8")
    assert len(descubrir.analizar(tmp_path).usos) == 5
    assert len(descubrir.analizar(tmp_path, agrupar="carpeta").usos) == 3
    assert len(descubrir.analizar(tmp_path, excluir=["examples/*"]).usos) == 4
    ids = [yaml.safe_load(descubrir.borrador_yaml(descubrir.analizar(tmp_path, agrupar="carpeta")))["agentes"][i]["id"] for i in range(3)]
    assert set(ids) == {"svc/uno", "svc/dos", "examples"}


def test_borrador_yaml_es_valido_con_nombres_raros(tmp_path):
    (tmp_path / "mi app").mkdir()
    (tmp_path / "mi app" / "agente bueno.py").write_text('from openai import OpenAI\nOpenAI().chat(model="gpt-oss:20b")\n', encoding="utf-8")
    data = yaml.safe_load(descubrir.borrador_yaml(descubrir.analizar(tmp_path)))
    assert data["modelos"][0]["id"] == "gpt-oss:20b" and len(data["agentes"]) == 1
