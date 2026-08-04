"""Enlace con equivalencia de plaza (regla 10)."""
from datetime import date

from bolsa.enlace import enlaza_todas
from bolsa.equivalencias import Equivalencias
from conftest import contrato, propuesta

LIM = date(2026, 12, 31)


def test_sin_equivalencia_no_enlaza_plaza_distinta():
    # propuesta E073A2, contrato E071A2, misma persona y fechas -> NO enlaza
    p = propuesta(id_plaza="E073A2", inicio="2026-07-25", fin=None)
    c = contrato(id_plaza="E071A2", inicio="2026-07-25", fin=None)
    enl = enlaza_todas([p], [c], Equivalencias(), LIM)
    assert not enl[0].enlazada


def test_con_equivalencia_enlaza_y_marca_plaza_distinta():
    pe = Equivalencias()
    pe.añade("E071A2", "E073A2", motivo="variante enfermería")
    p = propuesta(id_plaza="E073A2", inicio="2026-07-25", fin=None)
    c = contrato(id_plaza="E071A2", inicio="2026-07-25", fin=None)
    enl = enlaza_todas([p], [c], Equivalencias(), LIM, plazas_equiv=pe)
    assert enl[0].enlazada
    assert enl[0].plaza_distinta


def test_equivalencia_no_enlaza_plazas_no_relacionadas():
    # E084C2 (Aux. Enfermería) NO equivale a E079C1 (Téc. Laboratorio)
    pe = Equivalencias()
    pe.añade("E071A2", "E073A2")
    p = propuesta(id_plaza="E084C2", inicio="2026-07-25", fin=None)
    c = contrato(id_plaza="E079C1", inicio="2026-07-25", fin=None)
    enl = enlaza_todas([p], [c], Equivalencias(), LIM, plazas_equiv=pe)
    assert not enl[0].enlazada
