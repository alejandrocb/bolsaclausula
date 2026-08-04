"""Registro auditable de equivalencias NIE <-> DNI.

Permite tratar dos identificadores como la misma persona al enlazar
propuestas con contratos. Se mantiene por uniones (union-find) para que las
equivalencias sean transitivas y consultables.
"""
from __future__ import annotations

from pathlib import Path

from .cargas import lee_csv
from .config import DIR_CONFIG


class Equivalencias:
    def __init__(self):
        self._padre: dict[str, str] = {}
        self.registro: list[dict] = []

    def _find(self, x: str) -> str:
        self._padre.setdefault(x, x)
        raiz = x
        while self._padre[raiz] != raiz:
            raiz = self._padre[raiz]
        # compresión de caminos
        while self._padre[x] != raiz:
            self._padre[x], x = raiz, self._padre[x]
        return raiz

    def añade(self, a: str, b: str, **meta) -> None:
        a, b = a.strip(), b.strip()
        if not a or not b:
            return
        ra, rb = self._find(a), self._find(b)
        if ra != rb:
            self._padre[rb] = ra
        self.registro.append({"idrh_a": a, "idrh_b": b, **meta})

    def canonico(self, idrh: str) -> str:
        """Identificador canónico del grupo de equivalencia."""
        idrh = (idrh or "").strip()
        if not idrh:
            return ""
        return self._find(idrh)

    def mismos(self, a: str, b: str) -> bool:
        a, b = (a or "").strip(), (b or "").strip()
        if not a or not b:
            return False
        return self.canonico(a) == self.canonico(b)

    @classmethod
    def desde_csv(cls, ruta=None, col_a="idrh_a", col_b="idrh_b") -> "Equivalencias":
        ruta = Path(ruta) if ruta else DIR_CONFIG / "equivalencias_nie_dni.csv"
        eq = cls()
        if not ruta.exists():
            return eq
        # el fichero lleva comentarios '#'; los saltamos
        lineas = [
            ln for ln in ruta.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")
        ]
        if not lineas:
            return eq
        import csv as _csv
        for r in _csv.DictReader(lineas, delimiter=";"):
            eq.añade(
                r.get(col_a, ""), r.get(col_b, ""),
                motivo=r.get("motivo", ""),
                fecha_alta=r.get("fecha_alta", ""),
                usuario=r.get("usuario", ""),
            )
        return eq
