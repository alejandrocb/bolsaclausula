"""Pruebas de los 10 casos críticos de negocio."""
from datetime import date

from bolsa.enlace import enlaza_todas
from bolsa.equivalencias import Equivalencias
from bolsa.importaciones import dedup_movimientos, dedup_propuestas
from bolsa.modelo import Enlace
from bolsa.motor import computa_propuesta, conciliar

from conftest import (
    bolsa, contrato, movimiento, propuesta, saldo_inicial,
)

CORTE = date(2026, 7, 2)
LIMITE = date(2026, 12, 31)


def _enlace(prop, contratos=()):
    return Enlace(propuesta=prop, contratos=list(contratos))


# 1) Propuesta pendiente sin contrato -> reserva pendiente que consume
def test_caso1_pendiente_sin_contrato():
    p = propuesta(inicio="2026-07-10", fin="2026-07-31", sub_estado="APROBADA_GESTION_PRESUPUESTARIA")
    det = computa_propuesta(p, _enlace(p), CORTE, LIMITE)
    assert det.computa
    assert not det.enlazada
    assert det.consumo_neto == 22

    clave, si = saldo_inicial(base=1000)
    res = conciliar({clave: si}, [p], [], [], [], [bolsa("S9b1a")])
    fila = next(f for f in res.detalle if f.clausula == "S9b1a")
    assert fila.reserva_pendiente == 22
    assert fila.saldo_calculado == 1000 - 22


# 2) Contrato cerrado antes del fin reservado -> devolución prevista
def test_caso2_contrato_cerrado_antes():
    p = propuesta(inicio="2026-07-10", fin="2026-09-30")
    c = contrato(inicio="2026-07-10", fin="2026-08-15")
    det = computa_propuesta(p, _enlace(p, [c]), CORTE, LIMITE)
    assert det.contrato_cerrado
    assert det.efectivo_fin == date(2026, 8, 15)
    assert det.consumo_bruto == 83   # 10/07..30/09
    assert det.consumo_neto == 37    # 10/07..15/08
    assert det.devolucion_prevista == 46


# 3) Propuesta que llega a 2027 -> se recorta a 31/12/2026
def test_caso3_llega_a_2027():
    p = propuesta(inicio="2026-07-10", fin="2027-06-30")
    det = computa_propuesta(p, _enlace(p), CORTE, LIMITE)
    assert det.reserva_fin == LIMITE
    assert det.efectivo_fin == LIMITE
    assert det.consumo_neto == (LIMITE - date(2026, 7, 10)).days + 1


# 4) Continuidad: varias propuestas sucesivas para un mismo contrato
def test_caso4_continuidad_varias_propuestas():
    c = contrato(idrh="99999999R", inicio="2026-07-01", fin=None)
    p1 = propuesta(pid="10", idrh="99999999R", inicio="2026-07-05", fin="2026-07-20")
    p2 = propuesta(pid="11", idrh="99999999R", inicio="2026-07-21", fin="2026-08-10")
    enlaces = enlaza_todas([p1, p2], [c], Equivalencias(), LIMITE)
    assert all(e.enlazada for e in enlaces)   # ambas enlazan al mismo contrato


# 5) Cláusula distinta: la real de PeopleNet manda
def test_caso5_clausula_distinta():
    p = propuesta(clausula="S9b1a", inicio="2026-07-10", fin="2026-07-31")
    c = contrato(clausula="N91c", inicio="2026-07-10", fin=None)
    det = computa_propuesta(p, _enlace(p, [c]), CORTE, LIMITE)
    assert det.clausula_efectiva == "N91c"
    assert det.clausula_distinta

    _, si_s = saldo_inicial(clausula="S9b1a", base=500)
    _, si_n = saldo_inicial(clausula="N91c", base=500)
    ks = si_s.clave
    kn = si_n.clave
    res = conciliar({ks: si_s, kn: si_n}, [p], [c], [], [],
                    [bolsa("S9b1a"), bolsa("N91c")])
    fs = next(f for f in res.detalle if f.clausula == "S9b1a")
    fn = next(f for f in res.detalle if f.clausula == "N91c")
    # el consumo NO afecta a S9b1a (se devuelve por ajuste) y sí a N91c
    assert fs.saldo_calculado == 500
    assert fn.saldo_calculado == 500 - 22


# 6) NIE/DNI equivalente
def test_caso6_equivalencia_nie_dni():
    eq = Equivalencias()
    eq.añade("X1234567L", "12345678Z", motivo="test")
    p = propuesta(idrh="X1234567L", inicio="2026-07-10", fin="2026-07-31")
    c = contrato(idrh="12345678Z", inicio="2026-07-10", fin=None)
    enlaces = enlaza_todas([p], [c], eq, LIMITE)
    assert enlaces[0].enlazada


# 7) Plaza laboral: no consume
def test_caso7_plaza_laboral_no_consume():
    p = propuesta(id_plaza="L084C2", inicio="2026-07-10", fin="2026-07-31")
    det = computa_propuesta(p, _enlace(p), CORTE, LIMITE)
    assert not det.computa
    assert det.motivo_no_computa.startswith("plaza laboral")

    clave, si = saldo_inicial(id_plaza="L084C2", base=300)
    res = conciliar({clave: si}, [p], [], [], [], [bolsa("S9b1a")])
    fila = next(f for f in res.detalle if f.id_plaza == "L084C2")
    assert fila.saldo_calculado == 300   # conserva su saldo histórico, sin consumo


# 8) Saldo negativo por plaza pero no por dirección
def test_caso8_negativo_por_plaza_no_por_direccion():
    k1, s1 = saldo_inicial(id_plaza="E071A2", base=-100)
    k2, s2 = saldo_inicial(id_plaza="E084C2", base=300)
    res = conciliar({k1: s1, k2: s2}, [], [], [], [], [bolsa("S9b1a")])
    # a nivel plaza hay negativo
    assert any(f.saldo_calculado < 0 for f in res.detalle)
    # a nivel dirección + cláusula, positivo
    resumen = next(r for r in res.resumen_direccion if r["clausula"] == "S9b1a")
    assert resumen["saldo_calculado"] == 200


# 9) Importaciones solapadas: no duplicar por id
def test_caso9_importaciones_solapadas_dedup():
    m1 = movimiento(mid="500", pid="1", importe=-10)
    m1b = movimiento(mid="500", pid="1", importe=-10)   # misma id, export solapado
    m2 = movimiento(mid="501", pid="2", importe=-5)
    assert len(dedup_movimientos([m1, m1b, m2])) == 2

    p1 = propuesta(pid="1")
    p1b = propuesta(pid="1", fin="2026-08-31")   # versión más reciente
    assert len(dedup_propuestas([p1, p1b])) == 1


# 10) Devolución ya registrada: no se duplica
def test_caso10_devolucion_registrada_no_duplica():
    p = propuesta(pid="77", inicio="2026-07-10", fin="2026-09-30")
    c = contrato(inicio="2026-07-10", fin="2026-08-15")   # cierra antes -> devol prevista 46
    m = movimiento(mid="900", pid="77", tipo="DEVOLUCION_SOLICITUD", importe=-46)
    clave, si = saldo_inicial(base=1000)
    res = conciliar({clave: si}, [p], [c], [m], [], [bolsa("S9b1a")])
    det = next(d for d in res.detalle_propuestas if d.propuesta_id == "77")
    assert det.devolucion_prevista == 46
    assert det.devolucion_registrada == 46
    assert det.devolucion_pendiente == 0
    # el saldo calculado usa el consumo NETO; los movimientos solo verifican
    fila = next(f for f in res.detalle if f.clausula == "S9b1a")
    assert fila.saldo_calculado == 1000 - det.consumo_neto
