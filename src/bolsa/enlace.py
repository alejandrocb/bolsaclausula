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
) -> Enlace:
    """Enlaza una propuesta con los contratos compatibles.

    Criterio: mismo idrh canónico + misma plaza + solape de fechas.
    Devuelve el enlace con los contratos candidatos ordenados por proximidad
    de la fecha de inicio (el más ajustado primero -> manda su cláusula).
    """
    enlace = Enlace(propuesta=prop)
    if not prop.idrh:
        return enlace  # sin idrh no se puede enlazar (excepción)
    canon = equivalencias.canonico(prop.idrh)
    candidatos = []
    for c in idx_contratos.get(canon, []):
        if c.id_plaza and prop.id_plaza and c.id_plaza != prop.id_plaza:
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
    return enlace


def enlaza_todas(
    propuestas: list[Propuesta],
    contratos: list[Contrato],
    equivalencias: Equivalencias,
    fecha_limite: date,
) -> list[Enlace]:
    idx = indexa_contratos(contratos, equivalencias)
    return [
        enlaza_propuesta(p, idx, equivalencias, fecha_limite)
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
