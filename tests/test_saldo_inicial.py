"""Saldo inicial 01/01/2026 reconstruido (anclado a PeopleNet).

    saldo_01_01 = postcontrol + consumo al corte
    saldo_corte = postcontrol                 (coincide por construcción)
    saldo_actual = postcontrol − consumo desde el corte
El corte de un contrato se hace por su FECHA DE INICIO respecto al 02/07.
"""
from bolsa.motor import conciliar
from conftest import bolsa, contrato, saldo_inicial


def test_saldo_corte_coincide_con_postcontrol():
    clave, si = saldo_inicial(id_plaza="E071A2", direccion="DEAP",
                              clausula="N91c", base=1000)
    c = contrato(idrh="1H", periodo="1", id_plaza="E071A2", clausula="N91c",
                 inicio="2026-03-01", fin="2026-03-31", division="DEAP")
    res = conciliar({clave: si}, [], [c], [], {},
                    [bolsa(clausula="N91c", contratacion=5000, usados=31)])
    fila = next(f for f in res.saldo_ini_direccion
                if f["direccion"] == "DEAP" and f["clausula"] == "N91c")
    # saldo en el corte = postcontrol (base, sin movimientos que lo alteren)
    assert fila["saldo_corte"] == si.saldo_postcontrol


def test_contrato_previo_al_corte_va_a_consumo_al_corte():
    clave, si = saldo_inicial(id_plaza="E071A2", direccion="DEAP",
                              clausula="N91c", base=1000)
    # contrato marzo (inicio < 02/07) -> consumo al corte; 31 días
    c = contrato(idrh="1H", periodo="1", id_plaza="E071A2", clausula="N91c",
                 inicio="2026-03-01", fin="2026-03-31", division="DEAP")
    res = conciliar({clave: si}, [], [c], [], {},
                    [bolsa(clausula="N91c", contratacion=5000, usados=31)])
    f = next(x for x in res.saldo_ini_direccion
             if x["direccion"] == "DEAP" and x["clausula"] == "N91c")
    assert f["usados_corte"] == 31
    assert f["usados_desde"] == 0
    # saldo inicial 01/01 = corte + consumo al corte
    assert f["saldo_01_01"] == f["saldo_corte"] + 31
    # el consumo previo ya está en el postcontrol -> saldo actual = saldo corte
    assert f["saldo_actual"] == f["saldo_corte"]


def test_contrato_posterior_al_corte_va_a_consumo_desde():
    clave, si = saldo_inicial(id_plaza="E071A2", direccion="DEAP",
                              clausula="N91c", base=1000)
    # contrato agosto (inicio > 02/07) -> consumo desde el corte; 31 días
    c = contrato(idrh="1H", periodo="1", id_plaza="E071A2", clausula="N91c",
                 inicio="2026-08-01", fin="2026-08-31", division="DEAP")
    res = conciliar({clave: si}, [], [c], [], {},
                    [bolsa(clausula="N91c", contratacion=5000, usados=31)])
    f = next(x for x in res.saldo_ini_direccion
             if x["direccion"] == "DEAP" and x["clausula"] == "N91c")
    assert f["usados_corte"] == 0
    assert f["usados_desde"] == 31
    # no altera el saldo inicial (el 01/01 = corte), pero sí el actual
    assert f["saldo_01_01"] == f["saldo_corte"]
    assert f["saldo_actual"] == f["saldo_corte"] - 31


def test_identidad_saldo_actual():
    # saldo_actual == saldo_01_01 − (usados_corte + usados_desde), en cada fila
    clave, si = saldo_inicial(id_plaza="E071A2", direccion="DEAP",
                              clausula="S9b1a", base=2000)
    cs = [
        contrato(idrh="A", periodo="1", id_plaza="E071A2", clausula="S9b1a",
                 inicio="2026-02-01", fin="2026-02-28", division="DEAP"),
        contrato(idrh="B", periodo="1", id_plaza="E071A2", clausula="S9b1a",
                 inicio="2026-09-01", fin="2026-09-30", division="DEAP"),
    ]
    res = conciliar({clave: si}, [], cs, [], {},
                    [bolsa(clausula="S9b1a", contratacion=9000, usados=58)])
    for f in res.saldo_ini_plaza:
        assert f["saldo_actual"] == f["saldo_01_01"] - f["usados_corte"] - f["usados_desde"]
        assert f["saldo_01_01"] == f["saldo_corte"] + f["usados_corte"]
