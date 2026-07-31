"""Enlace propuesta <-> contrato PeopleNet (reglas 9 y 10).

Enlace por: idrh (con equivalencias NIE/DNI) + solape de fechas + plaza.
Un contrato puede corresponder a varias propuestas sucesivas (no 1:1).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from .equivalencias import Equivalencias
from .fechas import solapan
from .modelo import Contrato, Enlace, Propuesta


def indexa_contratos(
    contratos: list[Contrato], equivalencias: Equivalencias
) -> dict[str, list[Contrato]]:
    """Indexa contratos por idrh canónico."""
    idx: dict[str, list[Contrato]] = defaultdict(list)
    for c in contratos:
        idx[equivalencias.canonico(c.idrh)].append(c)
    return idx


def enlaza_propuesta(
    prop: Propuesta,
    idx_contratos: dict[str, list[Contrato]],
    equivalencias: Equivalencias,
    fecha_limite: date,
    plazas_equiv: Equivalencias | None = None,
) -> Enlace:
    """Enlaza una propuesta con los contratos compatibles.

    Criterio (regla 10): mismo idrh canónico + **misma plaza (o plaza
    equivalente)** + solape de fechas. Las equivalencias de plaza permiten
    tratar dos códigos como la misma categoría (p.ej. E071A2 ↔ E073A2), de forma
    explícita y auditable, sin sobre-enlazar plazas no relacionadas.
    Los candidatos se ordenan por proximidad de la fecha de inicio.
    """
    enlace = Enlace(propuesta=prop)
    if not prop.idrh:
        return enlace  # sin idrh no se puede enlazar (excepción)
    canon = equivalencias.canonico(prop.idrh)

    def plaza_compatible(c: Contrato) -> bool:
        if not c.id_plaza or not prop.id_plaza:
            return True
        if c.id_plaza == prop.id_plaza:
            return True
        return bool(plazas_equiv and plazas_equiv.mismos(c.id_plaza, prop.id_plaza))

    candidatos = []
    for c in idx_contratos.get(canon, []):
        if not plaza_compatible(c):
            continue
        if not solapan(prop.fecha_inicio, prop.fecha_fin,
                       c.fecha_inicio, c.fecha_fin, fecha_limite):
            continue
        candidatos.append(c)

    def distancia(c: Contrato):
        if c.fecha_inicio and prop.fecha_inicio:
            return abs((c.fecha_inicio - prop.fecha_inicio).days)
        return 10 ** 9

    candidatos.sort(key=distancia)
    enlace.contratos = candidatos
    enlace.plaza_distinta = bool(
        candidatos and candidatos[0].id_plaza and prop.id_plaza
        and candidatos[0].id_plaza != prop.id_plaza
    )
    return enlace


def enlaza_todas(
    propuestas: list[Propuesta],
    contratos: list[Contrato],
    equivalencias: Equivalencias,
    fecha_limite: date,
    plazas_equiv: Equivalencias | None = None,
) -> list[Enlace]:
    idx = indexa_contratos(contratos, equivalencias)
    return [
        enlaza_propuesta(p, idx, equivalencias, fecha_limite, plazas_equiv)
        for p in propuestas
    ]


def contratos_sin_propuesta(
    enlaces: list[Enlace],
    contratos: list[Contrato],
    clausulas_prioritarias: list[str],
) -> list[Contrato]:
    """Contratos prioritarios que no han quedado enlazados a ninguna propuesta
    (regla 11: excepción obligatoria)."""
    usados = set()
    for e in enlaces:
        for c in e.contratos:
            usados.add((c.idrh, c.num_periodo))
    return [
        c for c in contratos
        if c.clausula in clausulas_prioritarias
        and (c.idrh, c.num_periodo) not in usados
    ]
