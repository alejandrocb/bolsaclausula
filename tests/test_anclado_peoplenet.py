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


def test_contrato_con_hueco_de_gfh_no_rompe():
    # contrato 01/08–31/08 pero su tramo GFH solo cubre 01/08–15/08 -> hay
    # días 'sin tramo' que deben caer en la división del contrato (no romper).
    clave, si = saldo_inicial(id_plaza="E071A2", direccion="DEAP",
                              clausula="N91c", base=1000)
    c = contrato(idrh="1H", periodo="1", id_plaza="E071A2", clausula="N91c",
                 inicio="2026-08-01", fin="2026-08-31",
                 tramos=[("2026-08-01", "2026-08-15", "DEAP")])
    res = conciliar({clave: si}, [], [c], [], {},
                    [bolsa(clausula="N91c", contratacion=1000, usados=31)])
    # el usado (31 días) debe quedar todo en DEAP pese al hueco de GFH
    deap = next(a for a in res.anclado_direccion
                if a["direccion"] == "DEAP" and a["clausula"] == "N91c")
    assert deap["usados_real"] == 31


def test_contrato_sin_gfh_se_traza_con_dni():
    # contrato cuyo tramo no tiene división (GFH no mapeado) -> se traza en B3
    clave, si = saldo_inicial(id_plaza="E963A2", direccion="DEAP",
                              clausula="S9b1a", base=100)
    c = contrato(idrh="99999999R", periodo="1", id_plaza="E963A2",
                 clausula="S9b1a", inicio="2026-08-01", fin="2026-08-13",
                 tramos=[("2026-08-01", "2026-08-13", "")])  # división vacía
    res = conciliar({clave: si}, [], [c], [], {},
                    [bolsa(clausula="S9b1a", contratacion=1000, usados=13)])
    assert res.anclado_sin_gfh, "el contrato sin GFH debe quedar trazado"
    x = res.anclado_sin_gfh[0]
    assert x["idrh"] == "99999999R"
    assert x["id_plaza"] == "E963A2"
    assert x["dias"] == 13


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
