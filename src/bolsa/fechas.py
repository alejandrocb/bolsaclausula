"""Utilidades de fechas: parseo tolerante, conteo inclusivo y topes."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

_FORMATOS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d/%m/%Y %H:%M:%S",
)


def parse_fecha(valor, formato: Optional[str] = None) -> Optional[date]:
    """Convierte texto a ``date``. Devuelve ``None`` si está vacío o es inválido.

    Acepta varios formatos habituales; si se indica ``formato`` se prueba primero.
    """
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    txt = str(valor).strip()
    if txt == "":
        return None
    formatos = ([formato] if formato else []) + list(_FORMATOS)
    for fmt in formatos:
        try:
            return datetime.strptime(txt, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def dias_inclusivos(inicio: Optional[date], fin: Optional[date]) -> int:
    """Días = fin - inicio + 1 (incluye fines de semana y festivos).

    Si el intervalo es inválido (falta un extremo o fin < inicio) devuelve 0.
    """
    if inicio is None or fin is None:
        return 0
    delta = (fin - inicio).days + 1
    return delta if delta > 0 else 0


def fin_computable(
    fin_propuesta: Optional[date],
    fin_contrato: Optional[date],
    contrato_cerrado: bool,
    fecha_limite: date,
) -> date:
    """Fin computable de una reserva/consumo (reglas 6 y 7).

    - Abierto (sin contrato cerrado): tope = fecha_limite (31/12/2026).
    - Contrato cerrado: min(fin propuesta, fin real contrato, fecha_limite).
    """
    candidatos = [fecha_limite]
    if fin_propuesta is not None:
        candidatos.append(fin_propuesta)
    if contrato_cerrado and fin_contrato is not None:
        candidatos.append(fin_contrato)
    return min(candidatos)


def solapan(
    ini_a: Optional[date], fin_a: Optional[date],
    ini_b: Optional[date], fin_b: Optional[date],
    fecha_limite: date,
) -> bool:
    """¿Se solapan dos intervalos? Un fin vacío se trata como abierto (fecha_limite)."""
    if ini_a is None or ini_b is None:
        return False
    fa = fin_a or fecha_limite
    fb = fin_b or fecha_limite
    return ini_a <= fb and ini_b <= fa
