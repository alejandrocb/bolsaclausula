"""Modelo de dominio: entidades y claves de la conciliación."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


# Clave canónica de una bolsa a nivel de negocio.
# La validación crítica se hace agregando por (direccion_codigo, clausula).
@dataclass(frozen=True)
class ClavePlaza:
    id_plaza: str
    direccion_codigo: str
    clausula: str


@dataclass
class SaldoInicial:
    """Fila del corte inicial validado (base aritmética inmutable)."""
    clave: ClavePlaza
    direccion_id: str
    direccion_nombre: str
    descripcion_categoria: str
    saldo_postcontrol: int          # columna 'saldo' (= base - nuevos + recuperados)
    saldo_base_02_07: int
    nuevos_control: int
    recuperados_control: int
    origen_ajustes: str
    categoria_ids_maestro: tuple[str, ...] = ()

    def cuadra(self) -> bool:
        """Verifica la identidad aritmética del corte."""
        return self.saldo_postcontrol == (
            self.saldo_base_02_07 - self.nuevos_control + self.recuperados_control
        )


@dataclass
class Propuesta:
    propuesta_id: str
    id_plaza: str
    direccion_codigo: str
    clausula: str                   # cláusula declarada en la propuesta
    estado: str
    sub_estado: str
    fecha_autorizacion: Optional[date]
    fecha_inicio: Optional[date]
    fecha_fin: Optional[date]
    idrh: str
    propuesta_original_id: str = ""
    propuesta_sustituta_id: str = ""

    @property
    def abierta(self) -> bool:
        return self.fecha_fin is None


@dataclass
class TramoGFH:
    """Tramo de un contrato en un GFH concreto (regla dirección real)."""
    fecha_inicio: Optional[date]
    fecha_fin: Optional[date]
    gfh_id: str
    gfh_nombre: str
    division: str                   # dirección real (resuelta con el maestro)


@dataclass
class Contrato:
    idrh: str
    num_periodo: str
    id_plaza: str
    clausula: str                   # cláusula REAL de PeopleNet (manda, regla 5)
    fecha_inicio: Optional[date]
    fecha_fin: Optional[date]
    motivo_inicio: str
    tramos: list["TramoGFH"] = field(default_factory=list)
    propuesta_ref: str = ""        # propuesta enlazada explícitamente (comentario)

    @property
    def cerrado(self) -> bool:
        return self.fecha_fin is not None

    @property
    def divisiones(self) -> list[str]:
        return sorted({t.division for t in self.tramos if t.division})


@dataclass
class Movimiento:
    movimiento_id: str
    bolsa_dias_id: str
    propuesta_id: str
    fecha_movimiento: Optional[date]
    tipo_movimiento: str
    importe: int                    # + consume, - devuelve
    id_plaza: str
    direccion_codigo: str
    clausula: str


@dataclass
class SaldoActual:
    """Fotografía por bolsa (categoria_id) del aplicativo de Propuestas."""
    bolsa_dias_id: str
    direccion_codigo: str
    categoria_id: str
    id_plaza: str                   # categoria_codigo
    clausula: str
    bolsa_dias_inicial: int
    bolsa_dias_restante: int


@dataclass
class BolsaPeopleNet:
    """Bolsa global oficial por cláusula (control de riesgo)."""
    anio: int
    clausula: str
    dias_contratacion: int
    dias_usados: int
    comentario: str = ""

    @property
    def disponible(self) -> int:
        return self.dias_contratacion - self.dias_usados


@dataclass
class Enlace:
    """Resultado de enlazar una propuesta con (0..n) contratos PeopleNet."""
    propuesta: Propuesta
    contratos: list[Contrato] = field(default_factory=list)
    plaza_distinta: bool = False    # el contrato elegido está en otra plaza
    enlace_directo: bool = False    # enlazado por comentario del contrato

    @property
    def enlazada(self) -> bool:
        return len(self.contratos) > 0

    @property
    def clausula_efectiva(self) -> str:
        """La cláusula real de PeopleNet manda sobre la de la propuesta (regla 5)."""
        if self.contratos:
            return self.contratos[0].clausula
        return self.propuesta.clausula

    @property
    def clausula_distinta(self) -> bool:
        return self.enlazada and self.clausula_efectiva != self.propuesta.clausula
