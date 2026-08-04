"""Devolución por cierre de contrato posterior al corte (reservas pre-corte)."""
from datetime import date

from bolsa.motor import conciliar
from conftest import bolsa, contrato, propuesta, saldo_inicial


# Caso A — sin renovación: el saldo se libera
def test_cierre_sin_renovacion_libera_saldo():
    # propuesta PRE-corte (autorizada 01/05), abierta -> reservada a 31/12 en la base
    p = propuesta(pid="1", id_plaza="E071A2", direccion="DEAE", clausula="N91c",
                  autorizacion="2026-05-01", inicio="2026-01-01", fin=None)
    # contrato que cierra el 31/08
    c = contrato(idrh="12345678Z", id_plaza="E071A2", clausula="N91c",
                 inicio="2026-01-01", fin="2026-08-31", division="DEAE")
    _, si = saldo_inicial(id_plaza="E071A2", direccion="DEAE", clausula="N91c", base=1000)
    res = conciliar({si.clave: si}, [p], [c], [], [], [bolsa("N91c")])
    fila = next(f for f in res.detalle if f.clausula == "N91c")
    # 01/09 -> 31/12 = 122 días vuelven
    assert fila.devolucion_cierre == 122
    assert fila.saldo_calculado == 1000 + 122
    assert len(res.devoluciones_cierre) == 1


# Caso B — con renovación: se compensa (neto 0)
def test_cierre_con_renovacion_se_compensa():
    p = propuesta(pid="1", id_plaza="E071A2", direccion="DEAE", clausula="N91c",
                  autorizacion="2026-05-01", inicio="2026-01-01", fin=None)
    c = contrato(idrh="12345678Z", id_plaza="E071A2", clausula="N91c",
                 inicio="2026-01-01", fin="2026-08-31", division="DEAE")
    # renovación POSTERIOR sin contrato, cubre 01/09 -> 31/12 (reserva pendiente)
    reno = propuesta(pid="2", id_plaza="E071A2", direccion="DEAE", clausula="N91c",
                     estado="APROBADA", sub_estado="APROBADA_DIRECCION",
                     autorizacion="2026-07-10", inicio="2026-09-01", fin="2026-12-31",
                     idrh="12345678Z")
    _, si = saldo_inicial(id_plaza="E071A2", direccion="DEAE", clausula="N91c", base=1000)
    res = conciliar({si.clave: si}, [p, reno], [c], [], [], [bolsa("N91c")])
    fila = next(f for f in res.detalle if f.clausula == "N91c")
    assert fila.devolucion_cierre == 122      # devuelve el contrato viejo
    assert fila.reserva_pendiente == 122      # reserva la renovación
    assert fila.saldo_calculado == 1000       # NETO 0: la persona sigue ocupando


# Una propuesta POSTERIOR al corte NO genera devolución por cierre
# (su cierre ya se trata como devolución prevista en el consumo neto)
def test_cierre_no_aplica_a_posteriores():
    p = propuesta(pid="1", id_plaza="E071A2", direccion="DEAE", clausula="N91c",
                  autorizacion="2026-07-10", inicio="2026-07-10", fin="2026-12-31")
    c = contrato(idrh="12345678Z", id_plaza="E071A2", clausula="N91c",
                 inicio="2026-07-10", fin="2026-08-31", division="DEAE")
    _, si = saldo_inicial(id_plaza="E071A2", direccion="DEAE", clausula="N91c", base=1000)
    res = conciliar({si.clave: si}, [p], [c], [], [], [bolsa("N91c")])
    assert res.devoluciones_cierre == []
