"""Registro persistente de contratos entre importaciones.

Como las cargas son semanales/mensuales, la primera vez que aparece un contrato
se **congela** su fecha de alta (mín. de las tres 'última actualización'); las
modificaciones posteriores ya no la alteran. Permite además detectar los
**contratos nuevos** de cada importación.

El registro se guarda en un CSV (contiene DNI/NIE → va en data/, no se versiona).
No afecta al cálculo del saldo; enriquece la auditoría (alta fiable + novedades).
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Optional

from .fechas import parse_fecha
from .modelo import Contrato

_CAMPOS = ["idrh", "num_periodo", "id_plaza", "clausula",
           "primera_aparicion", "alta_congelada", "alta_ultima", "veces_visto"]


class RegistroContratos:
    def __init__(self):
        self.registros: dict[tuple[str, str], dict] = {}
        self.nuevos: set[tuple[str, str]] = set()

    @classmethod
    def carga(cls, ruta) -> "RegistroContratos":
        reg = cls()
        p = Path(ruta)
        if not p.exists():
            return reg
        with open(p, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f, delimiter=";"):
                clave = (r["idrh"], r["num_periodo"])
                reg.registros[clave] = r
        return reg

    def actualiza(self, contratos: list[Contrato], fecha_import: date) -> None:
        """Registra la importación: congela el alta de los contratos nuevos."""
        self.nuevos = set()
        fimp = fecha_import.isoformat()
        for c in contratos:
            clave = (c.idrh, c.num_periodo)
            alta = c.alta.isoformat() if c.alta else ""
            existente = self.registros.get(clave)
            if existente is None:
                self.registros[clave] = dict(
                    idrh=c.idrh, num_periodo=c.num_periodo, id_plaza=c.id_plaza,
                    clausula=c.clausula, primera_aparicion=fimp,
                    alta_congelada=alta or fimp,   # si no hay fechas, la 1ª importación
                    alta_ultima=alta, veces_visto="1",
                )
                self.nuevos.add(clave)
            else:
                existente["alta_ultima"] = alta
                existente["veces_visto"] = str(int(existente.get("veces_visto", "0") or 0) + 1)

    def guarda(self, ruta) -> None:
        p = Path(ruta)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=_CAMPOS, delimiter=";")
            w.writeheader()
            for r in self.registros.values():
                w.writerow({k: r.get(k, "") for k in _CAMPOS})

    def info(self) -> dict[tuple[str, str], dict]:
        """Por contrato: {alta_congelada: date, primera_aparicion: date, nuevo: bool}."""
        out = {}
        for clave, r in self.registros.items():
            out[clave] = dict(
                alta_congelada=parse_fecha(r.get("alta_congelada")),
                primera_aparicion=parse_fecha(r.get("primera_aparicion")),
                nuevo=clave in self.nuevos,
            )
        return out
