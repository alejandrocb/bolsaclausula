"""Control A13: 'Días Usados' de PeopleNet vs días comprometidos por contrato."""
from bolsa.motor import conciliar
from conftest import bolsa, contrato


def _por_clausula(res):
    return {x["clausula"]: x for x in res.usados_vs_contratos}


def test_cuadra_cuando_usados_igual_a_comprometido():
    # contrato N91c del 01/08 al 31/08 (inclusive) = 31 días
    c = contrato(idrh="1H", periodo="1", id_plaza="E071A2", clausula="N91c",
                 inicio="2026-08-01", fin="2026-08-31", division="DEAP")
    res = conciliar({}, [], [c], [], {}, [bolsa(clausula="N91c",
                                               contratacion=1000, usados=31)])
    x = _por_clausula(res)["N91c"]
    assert x["comprometido_contratos"] == 31
    assert x["dias_usados_peoplenet"] == 31
    assert x["diferencia"] == 0
    assert x["estado"] == "OK"


def test_marca_revisar_si_descuadra():
    c = contrato(idrh="1H", periodo="1", id_plaza="E071A2", clausula="N91c",
                 inicio="2026-08-01", fin="2026-08-31", division="DEAP")
    # PeopleNet dice 500 usados pero los contratos solo suman 31 -> REVISAR
    res = conciliar({}, [], [c], [], {}, [bolsa(clausula="N91c",
                                               contratacion=1000, usados=500)])
    x = _por_clausula(res)["N91c"]
    assert x["comprometido_contratos"] == 31
    assert x["diferencia"] == 31 - 500
    assert x["estado"] == "REVISAR"


def test_contrato_sin_fin_cuenta_hasta_limite():
    # contrato abierto (sin fin) desde 01/12 -> cuenta hasta 31/12 = 31 días
    c = contrato(idrh="1H", periodo="1", id_plaza="E071A2", clausula="N91c",
                 inicio="2026-12-01", fin=None, division="DEAP")
    res = conciliar({}, [], [c], [], {}, [bolsa(clausula="N91c",
                                               contratacion=1000, usados=31)])
    assert _por_clausula(res)["N91c"]["comprometido_contratos"] == 31
