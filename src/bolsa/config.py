"""Carga de configuración (parámetros y mapeo de columnas).

Incluye un parser YAML mínimo, sin dependencias externas, suficiente para los
ficheros de ``config/``: mapas anidados por indentación, listas con ``- `` y
escalares (str / int / float). Si PyYAML está instalado, se usa en su lugar.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:  # preferimos PyYAML si está disponible
    import yaml as _yaml  # type: ignore
except Exception:  # pragma: no cover - camino sin dependencia
    _yaml = None

RAIZ = Path(__file__).resolve().parents[2]
DIR_CONFIG = RAIZ / "config"


def _coacciona(valor: str) -> Any:
    """Convierte un escalar de texto a int/float/bool/str."""
    v = valor.strip()
    if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
        return v[1:-1]
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    if v.lower() in ("null", "~", ""):
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def _quita_comentario(linea: str) -> str:
    """Elimina comentarios ``#`` respetando los que van dentro de comillas."""
    fuera = True
    comilla = ""
    for i, ch in enumerate(linea):
        if fuera and ch in "\"'":
            fuera = False
            comilla = ch
        elif not fuera and ch == comilla:
            fuera = True
        elif fuera and ch == "#":
            # comentario solo si va al inicio o precedido de espacio
            if i == 0 or linea[i - 1] in " \t":
                return linea[:i]
    return linea


def _parse_yaml_min(texto: str) -> Any:
    lineas = []
    for cruda in texto.splitlines():
        sin = _quita_comentario(cruda).rstrip()
        if sin.strip() == "":
            continue
        indent = len(sin) - len(sin.lstrip(" "))
        lineas.append((indent, sin.strip()))

    pos = 0

    def parse_bloque(indent_min: int) -> Any:
        nonlocal pos
        # ¿lista o mapa?
        if pos < len(lineas) and lineas[pos][1].startswith("- "):
            items = []
            while pos < len(lineas):
                indent, cont = lineas[pos]
                if indent < indent_min or not cont.startswith("- "):
                    break
                items.append(_coacciona(cont[2:]))
                pos += 1
            return items
        mapa: dict[str, Any] = {}
        while pos < len(lineas):
            indent, cont = lineas[pos]
            if indent < indent_min:
                break
            if ":" not in cont:
                pos += 1
                continue
            clave, _, resto = cont.partition(":")
            clave = clave.strip()
            resto = resto.strip()
            pos += 1
            if resto == "":
                # bloque anidado (mapa o lista) con mayor indentación
                if pos < len(lineas) and lineas[pos][0] > indent:
                    mapa[clave] = parse_bloque(lineas[pos][0])
                else:
                    mapa[clave] = None
            else:
                mapa[clave] = _coacciona(resto)
        return mapa

    return parse_bloque(0)


def carga_yaml(ruta: os.PathLike | str) -> Any:
    texto = Path(ruta).read_text(encoding="utf-8")
    if _yaml is not None:
        return _yaml.safe_load(texto)
    return _parse_yaml_min(texto)


class Config:
    """Acceso tipado a parámetros y mapeo de columnas."""

    def __init__(self, dir_config: os.PathLike | str = DIR_CONFIG):
        self.dir_config = Path(dir_config)
        self.parametros = carga_yaml(self.dir_config / "parametros.yaml")
        self.mapeo = carga_yaml(self.dir_config / "mapeo_columnas.yaml")

    # --- parámetros de negocio ---
    @property
    def fecha_corte(self) -> str:
        return self.parametros["fecha_corte"]

    @property
    def fecha_limite(self) -> str:
        return self.parametros["fecha_limite"]

    @property
    def clausulas_prioritarias(self) -> list[str]:
        return list(self.parametros["clausulas_prioritarias"])

    @property
    def prefijo_laboral(self) -> str:
        return self.parametros["prefijo_laboral"]

    @property
    def estados_vivos(self) -> list[str]:
        return list(self.parametros["estados_vivos"])

    @property
    def estados_anulados(self) -> list[str]:
        return list(self.parametros["estados_anulados"])

    def es_laboral(self, id_plaza: str) -> bool:
        return bool(id_plaza) and id_plaza.upper().startswith(self.prefijo_laboral)


CONFIG = Config()
