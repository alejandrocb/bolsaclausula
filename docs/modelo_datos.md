# Modelo de datos y conciliación

## 1. Niveles de granularidad (clave del sistema)

Existen **tres niveles** que hay que casar correctamente:

| Nivel | Ejemplo | Dónde aparece |
|-------|---------|---------------|
| `categoria_id` (numérico) | `65`, `169`, `175` | SaldoActual, Movimientos, Propuestas |
| `categoria_codigo` = `id_plaza` | `E071A2` | Todos |
| `bolsa_dias_id` | `1544` | SaldoActual, Movimientos (una bolsa = categoria_id × dirección × cláusula) |

Un mismo `id_plaza` (p.ej. `E071A2`, Enfermera/o) agrupa **varios**
`categoria_id` (Enfermera/o, Enfermera/o-Unidad Hemodinámica, Enfermero/a-Ámbito
Escolar). El **corte inicial** trabaja a nivel `id_plaza` y lleva la columna
`categoria_ids_maestro` con el conjunto agregado (`65,169,175`).

**Regla de agregación:** para comparar el saldo recalculado (nivel `id_plaza`)
con `SaldoActualPropuestas` (nivel `categoria_id`), se **agrega SaldoActual a
`id_plaza`** sumando `bolsa_dias_restante` por `(id_plaza, dirección, cláusula)`.

## 2. Clave de negocio

```
ClavePlaza = (id_plaza, direccion_codigo, clausula)
```

La **validación crítica** (regla 12) se hace agregando a
`(direccion_codigo, clausula)`: una plaza puede quedar en negativo, pero una
Dirección no debe quedar sin disponibilidad.

## 3. Entidades (`src/bolsa/modelo.py`)

- **SaldoInicial** — fila del corte (base inmutable). Verifica la identidad
  `saldo_postcontrol = saldo_base_02_07 − nuevos_control + recuperados_control`.
- **Propuesta** — compromiso de contratación (propuesta_id, idrh, fechas,
  estado/sub_estado, cláusula declarada).
- **Contrato** — periodo real de PeopleNet (idrh, núm_periodo, fechas,
  **cláusula real**, motivo). Fin vacío = abierto.
- **Movimiento** — evidencia de lo que Propuestas restó/devolvió
  (movimiento_id único; importe + consume, − devuelve).
- **SaldoActual** — fotografía por bolsa (categoria_id) de Propuestas.
- **BolsaPeopleNet** — bolsa global oficial por cláusula (`disponible =
  contratación − usados`).
- **Enlace** — propuesta + sus contratos; expone `clausula_efectiva`
  (la del contrato manda) y `clausula_distinta`.

## 4. Diagrama de conciliación

```
        CORTE INICIAL 02/07/2026  (auditoria + post_control + diario)
        saldo_postcontrol = base − nuevos + recuperados        [INMUTABLE]
                       │  clave (id_plaza, dirección, cláusula)
                       ▼
 PROPUESTAS ─────►  MOTOR (motor.conciliar)  ◄───── CONTRATOS PEOPLENET
 estado/fechas       │  enlace idrh+fechas+plaza     inicio/fin/cláusula real
 cláusula decl.      │  (equivalencias NIE/DNI)
 MOVIMIENTOS ───►    ▼
 (verificación)   saldo_calculado
                  = postcontrol − consumo + devolución ± ajuste_cláusula
                       │
      ┌────────────────┼─────────────────────┐
      ▼                ▼                       ▼
 SALDO CALCULADO   SALDO ACTUAL           BOLSA PEOPLENET (global)
 "para recargar"   (SaldoActual)          disponible − reservas = riesgo
      └──── DIFERENCIA / DESCUADRE ────┘
```

## 5. Fórmula contable

Por `ClavePlaza`, con cada propuesta que **computa** (APROBADA, autorizada tras
el corte, cláusula prioritaria, plaza no laboral, con fecha de inicio):

```
consumo_bruto        = días_inclusivos(inicio, reserva_fin)
reserva_fin          = min(fin_propuesta | 31/12/2026)
consumo_neto         = días_inclusivos(inicio, fin_computable)
fin_computable       = min(fin_propuesta, fin_contrato_si_cerrado, 31/12/2026)
devolucion_prevista  = consumo_bruto − consumo_neto
```

Acumulación (el consumo/devolución se anotan en la **cláusula declarada**; si el
contrato tiene otra cláusula, `ajuste_clausula` mueve el **neto** de la
declarada a la efectiva, con **suma cero** entre ambas):

```
consumo_posterior[decl]   += consumo_bruto
devolucion_posterior[decl]+= devolucion_prevista
si cláusula distinta:
    ajuste_clausula[decl]  += consumo_neto      # se "devuelve" a la declarada
    ajuste_clausula[efec]  -= consumo_neto      # se consume en la efectiva
si sin contrato:
    reserva_pendiente[efec]+= consumo_neto

saldo_calculado = saldo_postcontrol − consumo_posterior
                + devolucion_posterior + ajuste_clausula
```

## 6. Devoluciones: tres estados diferenciados (regla 8)

- **prevista/calculada** — `devolucion_prevista` (contrato cierra antes del fin
  reservado).
- **registrada** — suma de movimientos `DEVOLUCION_SOLICITUD` de esa propuesta.
- **pendiente** — `max(0, prevista − registrada)`.

Los movimientos **no** alteran el `saldo_calculado` (que usa el consumo neto);
solo **verifican** que lo real coincide con lo esperado. Así una devolución ya
registrada **no se aplica dos veces**.
