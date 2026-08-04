"""Enlace directo por el comentario del contrato ('Solicitud contratacion N')."""
from datetime import date

from bolsa.cargas.periodicas import propuesta_de_comentario
from bolsa.enlace import enlaza_todas
from bolsa.equivalencias import Equivalencias
from bolsa.modelo import Contrato, TramoGFH
from conftest import propuesta

LIM = date(2026, 12, 31)


def test_parser_comentario():
    assert propuesta_de_comentario("Solicitud contratacion 64008") == "64008"
    assert propuesta_de_comentario("PROPUESTA 91239") == "91239"
    assert propuesta_de_comentario("89495") == "89495"
    assert propuesta_de_comentario("JOJECABX: 23/11/23 PRESENTA MOD145") == ""
    assert propuesta_de_comentario("") == ""


def _contrato(idrh, plaza, clausula, ini, fin, division, prop_ref=""):
    return Contrato(
        idrh=idrh, num_periodo="1", id_plaza=plaza, clausula=clausula,
        fecha_inicio=date.fromisoformat(ini),
        fecha_fin=date.fromisoformat(fin) if fin else None, motivo_inicio="X",
        tramos=[TramoGFH(date.fromisoformat(ini),
                         date.fromisoformat(fin) if fin else None,
                         "G", "g", division)],
        propuesta_ref=prop_ref,
    )


def test_enlace_directo_manda_sobre_heuristico():
    # la propuesta NO casaría por fechas/plaza, pero el contrato la referencia
    p = propuesta(pid="93720", id_plaza="E084C2", direccion="DEAE",
                  clausula="", idrh="42910568C",
                  inicio="2026-07-01", fin="2026-07-03")
    # contrato con fechas que NO solapan con la propuesta y plaza distinta,
    # pero con propuesta_ref al id -> debe enlazar igualmente
    c = _contrato("42910568C", "E999X", "N91c", "2025-01-01", "2025-02-01",
                  "DEAE", prop_ref="93720")
    enl = enlaza_todas([p], [c], Equivalencias(), LIM)
    assert enl[0].enlazada
    assert enl[0].enlace_directo
    assert enl[0].clausula_efectiva == "N91c"


def test_sin_referencia_usa_heuristico():
    p = propuesta(pid="500", id_plaza="E071A2", direccion="DEAP",
                  clausula="S9b1a", idrh="12345678Z",
                  inicio="2026-07-10", fin="2026-07-31")
    c = _contrato("12345678Z", "E071A2", "S9b1a", "2026-07-10", "2026-08-31",
                  "DEAP")  # sin prop_ref
    enl = enlaza_todas([p], [c], Equivalencias(), LIM)
    assert enl[0].enlazada
    assert not enl[0].enlace_directo
