"""Carga de los tres ficheros del corte inicial (base inmutable 02/07/2026)."""
from __future__ import annotations

from pathlib import Path

from ..config import CONFIG
from ..modelo import ClavePlaza, SaldoInicial
from . import entero, lee_csv


def _ids_maestro(txt: str) -> tuple[str, ...]:
    if not txt:
        return ()
    return tuple(x.strip() for x in txt.split(",") if x.strip())


def carga_saldo_inicial(ruta_auditoria, config=CONFIG) -> dict[ClavePlaza, SaldoInicial]:
    """Carga el fichero de auditoría (detalle completo del corte).

    Es la fuente aritmética de partida. Devuelve un dict indexado por ClavePlaza.
    """
    m = config.mapeo["inicial_auditoria"]
    col = m["columnas"]
    filas = lee_csv(ruta_auditoria, m["delimitador"])
    resultado: dict[ClavePlaza, SaldoInicial] = {}
    for r in filas:
        clave = ClavePlaza(
            id_plaza=r[col["id_plaza"]].strip(),
            direccion_codigo=r[col["direccion_codigo"]].strip(),
            clausula=r[col["clausula"]].strip(),
        )
        resultado[clave] = SaldoInicial(
            clave=clave,
            direccion_id=r[col["direccion_id"]].strip(),
            direccion_nombre=r.get(col["direccion_nombre"], "").strip(),
            descripcion_categoria=r.get(col["descripcion_categoria"], "").strip(),
            saldo_postcontrol=entero(r[col["saldo"]]),
            saldo_base_02_07=entero(r[col["saldo_base_02_07"]]),
            nuevos_control=entero(r[col["nuevos_control"]]),
            recuperados_control=entero(r[col["recuperados_control"]]),
            origen_ajustes=r.get(col["origen_ajustes"], "").strip(),
            categoria_ids_maestro=_ids_maestro(r.get(col["categoria_ids_maestro"], "")),
        )
    return resultado


def carga_postcontrol(ruta_postcontrol, config=CONFIG) -> dict[ClavePlaza, int]:
    """Carga el post_control (solo saldo final) para verificación cruzada."""
    m = config.mapeo["inicial_postcontrol"]
    col = m["columnas"]
    filas = lee_csv(ruta_postcontrol, m["delimitador"])
    out: dict[ClavePlaza, int] = {}
    for r in filas:
        clave = ClavePlaza(
            id_plaza=r[col["id_plaza"]].strip(),
            direccion_codigo=r[col["direccion_codigo"]].strip(),
            clausula=r[col["clausula"]].strip(),
        )
        out[clave] = entero(r[col["saldo"]])
    return out


def carga_diario(ruta_diario, config=CONFIG) -> list[dict]:
    """Carga el diario postcontrol 30/06->02/07 (trazabilidad de ajustes)."""
    m = config.mapeo["inicial_diario"]
    col = m["columnas"]
    filas = lee_csv(ruta_diario, m["delimitador"])
    out = []
    for r in filas:
        out.append({
            "fecha_registro": r.get(col["fecha_registro"], "").strip(),
            "fila_origen": r.get(col["fila_origen"], "").strip(),
            "propuesta_id": r.get(col["propuesta_id"], "").strip(),
            "direccion_codigo": r.get(col["direccion_codigo"], "").strip(),
            "id_plaza": r.get(col["id_plaza"], "").strip(),
            "clausula": r.get(col["clausula"], "").strip(),
            "dias_nuevos": entero(r.get(col["dias_nuevos"])),
            "dias_recuperados": entero(r.get(col["dias_recuperados"])),
            "clasificacion": r.get(col["clasificacion"], "").strip(),
        })
    return out
