"""Auditoría de contratos con inicio posterior al corte (control de mecanización)."""
from datetime import date

from bolsa.motor import conciliar
from conftest import bolsa, contrato, propuesta, saldo_inicial


def test_contrato_posterior_sin_propuesta_se_marca():
    # contrato con inicio > 02/07 y SIN propuesta -> aparece como incidencia
    c = contrato(idrh="99999999R", id_plaza="E071A2", clausula="S9b1a",
                 inicio="2026-08-01", fin=None, division="DEAP")
    _, si = saldo_inicial(clausula="S9b1a", base=100)
    res = conciliar({si.clave: si}, [], [c], [], [], [bolsa("S9b1a")])
    assert len(res.contratos_post_corte) == 1
    fila = res.contratos_post_corte[0]
    assert fila["enlazado_a_propuesta"] is False
    assert "sin propuesta" in fila["incidencia"]


def test_contrato_posterior_con_propuesta_no_es_incidencia():
    p = propuesta(pid="7", id_plaza="E071A2", direccion="DEAP", clausula="S9b1a",
                  idrh="99999999R", autorizacion="2026-08-01",
                  inicio="2026-08-01", fin="2026-12-31")
    c = contrato(idrh="99999999R", id_plaza="E071A2", clausula="S9b1a",
                 inicio="2026-08-01", fin=None, division="DEAP")
    _, si = saldo_inicial(clausula="S9b1a", base=100)
    res = conciliar({si.clave: si}, [p], [c], [], [], [bolsa("S9b1a")])
    fila = res.contratos_post_corte[0]
    assert fila["enlazado_a_propuesta"] is True
    assert fila["incidencia"] == ""


def test_contrato_inicio_anterior_al_corte_no_se_audita():
    c = contrato(idrh="99999999R", id_plaza="E071A2", clausula="S9b1a",
                 inicio="2026-01-01", fin=None, division="DEAP")
    _, si = saldo_inicial(clausula="S9b1a", base=100)
    res = conciliar({si.clave: si}, [], [c], [], [], [bolsa("S9b1a")])
    assert res.contratos_post_corte == []
