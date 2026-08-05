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


def test_incluye_aprobada_vigente_que_no_computa():
    # propuesta APROBADA autorizada ANTES del corte (ya en base) pero con fin
    # posterior: no computa, pero debe poder buscarse en el informe.
    clave, si = saldo_inicial(id_plaza="E071A2", direccion="DEAP",
                              clausula="N91c", base=100)
    p = propuesta(pid="93301", idrh="43572433Z", id_plaza="E071A2",
                  direccion="DEAP", clausula="N91c", estado="APROBADA",
                  autorizacion="2026-06-18", inicio="2026-06-19", fin="2026-07-19")
    res = conciliar({clave: si}, [p], [], [], {}, [bolsa(clausula="N91c")])
    d = _datos(res)
    fila = [x for x in d["propuestas"] if x["propuesta_id"] == "93301"]
    assert fila, "la APROBADA vigente debe aparecer en el índice del informe"
    assert fila[0]["computa"] is False
    assert "corte" in fila[0]["motivo"]


def test_excluye_aprobada_historica_terminada():
    # propuesta APROBADA ya terminada mucho antes del corte: NO se incluye.
    clave, si = saldo_inicial(id_plaza="E071A2", direccion="DEAP",
                              clausula="N91c", base=100)
    p = propuesta(pid="50000", idrh="11111111H", id_plaza="E071A2",
                  direccion="DEAP", clausula="N91c", estado="APROBADA",
                  autorizacion="2023-05-01", inicio="2023-05-02", fin="2023-06-01")
    res = conciliar({clave: si}, [p], [], [], {}, [bolsa(clausula="N91c")])
    d = _datos(res)
    assert not [x for x in d["propuestas"] if x["propuesta_id"] == "50000"]


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
