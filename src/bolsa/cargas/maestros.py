"""Carga de maestros de referencia (Divisiones/Plazas/GFH)."""
from __future__ import annotations

from ..config import CONFIG
from . import dicts_desde_filas, lee_tabla


def carga_divisiones(ruta, config=CONFIG) -> dict[tuple[str, str], str]:
    """Maestro (ID Plaza, ID GFH) -> División asignada (dirección real).

    Verificado como función (una división por combinación).
    """
    m = config.mapeo["divisiones"]
    col = m["columnas"]
    filas = lee_tabla(ruta, m.get("hoja"))
    out: dict[tuple[str, str], str] = {}
    for r in dicts_desde_filas(filas):
        plaza = str(r.get(col["id_plaza"], "") or "").strip()
        gfh = str(r.get(col["gfh_id"], "") or "").strip()
        division = str(r.get(col["division"], "") or "").strip()
        if plaza and gfh and division:
            out[(plaza, gfh)] = division
    return out
