"""El informe HTML local se genera bien-formado y con el JSON embebido."""
import json
import re

from bolsa.exportar_web import _datos, exporta_informe
from bolsa.motor import conciliar
from conftest import bolsa, contrato, movimiento, propuesta, saldo_inicial


def _resultado():
    clave, si = saldo_inicial(id_plaza="E071A2", direccion="DEAP",
                              clausula="N91c", base=100)
    p = propuesta(pid="500", idrh="11111111H", id_plaza="E071A2",
                  direccion="DEAP", clausula="N91c",
                  inicio="2026-07-10", fin="2026-12-31", estado="APROBADA")
    return conciliar({clave: si}, [p], [], [], {}, [bolsa(clausula="N91c")])


def test_datos_tiene_todas_las_claves():
    res = _resultado()
    d = _datos(res)
    assert set(d) >= {"semaforo", "totales", "direcciones",
                      "detalle", "propuestas", "cierres"}


def test_exporta_informe_html_valido(tmp_path):
    res = _resultado()
    ruta = exporta_informe(res, tmp_path / "informe.html", fecha="20260805")
    html = ruta.read_text(encoding="utf-8")
    assert "__DATA__" not in html          # el marcador se sustituyó
    assert html.strip().startswith("<!doctype html>")
    m = re.search(r"const DATA = (\{.*?\});\nconst eur", html, re.S)
    assert m, "no se encontró el bloque DATA"
    datos = json.loads(m.group(1))         # el JSON embebido es válido
    assert datos["fecha"] == "20260805"
