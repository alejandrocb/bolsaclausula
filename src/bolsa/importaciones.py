"""Registro de importaciones y utilidades de deduplicación.

Las cargas periódicas son exportaciones completas y pueden solaparse. Aquí:
- se registra cada fichero importado (hash SHA-256, filas, fecha) para histórico;
- se deduplican movimientos por ``movimiento_id`` y propuestas por
  ``propuesta_id`` (conservando la versión más reciente).
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from .modelo import Movimiento, Propuesta


def hash_fichero(ruta) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def registra(ruta, tipo: str, filas: int) -> dict:
    p = Path(ruta)
    return {
        "fichero": p.name,
        "tipo": tipo,
        "filas": filas,
        "hash": hash_fichero(p)[:16],
        "fecha_importacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def dedup_movimientos(movimientos: list[Movimiento]) -> list[Movimiento]:
    """Elimina movimientos repetidos por ``movimiento_id`` (regla 13)."""
    vistos: dict[str, Movimiento] = {}
    for m in movimientos:
        vistos[m.movimiento_id] = m
    return list(vistos.values())


def dedup_propuestas(propuestas: list[Propuesta]) -> list[Propuesta]:
    """Conserva una fila por ``propuesta_id`` (la última de la exportación)."""
    vistos: dict[str, Propuesta] = {}
    for p in propuestas:
        vistos[p.propuesta_id] = p
    return list(vistos.values())
