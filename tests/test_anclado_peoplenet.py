"""Modo anclado a PeopleNet: disponible = Contratación − Usados_real − Pendiente."""
from bolsa.motor import conciliar
from conftest import bolsa, contrato, propuesta, saldo_inicial


def test_reconcilia_por_clausula_con_el_margen():
    # una plaza con corte, un contrato (usados real) y una propuesta pendiente
    clave, si = saldo_inicial(id_plaza="E071A2", direccion="DEAP",
                              clausula="N91c", base=1000)
    c = contrato(idrh="1H", periodo="1", id_plaza="E071A2", clausula="N91c",
                 inicio="2026-08-01", fin="2026-08-31", division="DEAP")
    res = conciliar({clave: si}, [], [c], [], {},
                    [bolsa(clausula="N91c", contratacion=1000, usados=31)])
    # Σ disponible anclado (por dirección) = Contratación − usados − pendiente = Margen
    total = sum(a["disponible"] for a in res.anclado_direccion)
    margen = next(s["disponible_tras_compromisos"] for s in res.semaforo
                  if s["clausula"] == "N91c")
    assert abs(total - margen) <= 2      # tolerancia por redondeo del reparto


def test_control_por_direccion_marca_rojo():
    # dirección cuyo usado supera su contratación -> ROJO
    clave, si = saldo_inicial(id_plaza="E071A2", direccion="DEAP",
                              clausula="N91c", base=10)
    c = contrato(idrh="1H", periodo="1", id_plaza="E071A2", clausula="N91c",
                 inicio="2026-01-01", fin="2026-12-31", division="DEAP")
    res = conciliar({clave: si}, [], [c], [], {},
                    [bolsa(clausula="N91c", contratacion=100, usados=365)])
    dirs = {(a["direccion"], a["clausula"]): a for a in res.anclado_direccion}
    a = dirs[("DEAP", "N91c")]
    assert a["usados_real"] == 365
    assert a["disponible"] < 0
    assert a["estado"] == "ROJO"
