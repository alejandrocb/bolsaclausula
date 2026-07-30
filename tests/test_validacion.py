"""Pruebas de la validación cruzada esperado vs registrado."""
from datetime import date

from bolsa.motor import computa_propuesta
from bolsa.modelo import Enlace
from bolsa.validacion import valida_movimientos

from conftest import contrato, movimiento, propuesta

CORTE = date(2026, 7, 2)
LIMITE = date(2026, 12, 31)


def _det(p, contratos=()):
    return computa_propuesta(p, Enlace(propuesta=p, contratos=list(contratos)),
                             CORTE, LIMITE)


def test_coincide_esperado_con_registrado():
    p = propuesta(pid="1", inicio="2026-07-10", fin="2026-07-31")  # 22 días
    d = _det(p)
    m = movimiento(mid="1", pid="1", tipo="NUEVA_SOLICITUD", importe=22)
    r = valida_movimientos([p], [m], [d], LIMITE)
    fila = next(f for f in r.por_propuesta if f.propuesta_id == "1")
    assert fila.esperado_con_tope == 22
    assert fila.registrado_nueva == 22
    assert fila.diferencia == 0
    assert r.resumen["propuestas_con_diferencia"] == 0


def test_detecta_diferencia():
    p = propuesta(pid="2", inicio="2026-07-10", fin="2026-07-31")  # espera 22
    d = _det(p)
    m = movimiento(mid="2", pid="2", tipo="NUEVA_SOLICITUD", importe=20)  # restó 20
    r = valida_movimientos([p], [m], [d], LIMITE)
    fila = next(f for f in r.por_propuesta if f.propuesta_id == "2")
    assert fila.diferencia == -2
    assert r.resumen["propuestas_con_diferencia"] == 1


def test_movimiento_sin_propuesta_es_anomalo():
    m = movimiento(mid="9", pid="99999", tipo="NUEVA_SOLICITUD", importe=5)
    r = valida_movimientos([], [m], [], LIMITE)
    assert len(r.anomalos) == 1
    assert "inexistente" in r.anomalos[0].incidencias


def test_movimiento_clausula_incoherente_es_anomalo():
    p = propuesta(pid="3", clausula="S9b1a")
    d = _det(p)
    m = movimiento(mid="3", pid="3", clausula="N91c", tipo="NUEVA_SOLICITUD", importe=10)
    r = valida_movimientos([p], [m], [d], LIMITE)
    assert any("cláusula" in a.incidencias for a in r.anomalos)


def test_devolucion_registrada_no_pendiente():
    p = propuesta(pid="4", inicio="2026-07-10", fin="2026-09-30")
    c = contrato(inicio="2026-07-10", fin="2026-08-15")   # devol prevista 46
    d = _det(p, [c])
    d.devolucion_registrada = 46
    d.devolucion_pendiente = max(0, d.devolucion_prevista - 46)
    m = movimiento(mid="4", pid="4", tipo="DEVOLUCION_SOLICITUD", importe=-46)
    r = valida_movimientos([p], [m], [d], LIMITE)
    fila = next(f for f in r.por_propuesta if f.propuesta_id == "4")
    assert fila.devolucion_registrada == 46
    assert fila.devolucion_pendiente == 0
