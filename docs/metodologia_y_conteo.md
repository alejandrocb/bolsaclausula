# Metodología y conteo de la bolsa de días

Este documento explica **qué hace el sistema**, **cómo se cuentan los días en
cada sitio** (PeopleNet vs Propuestas), los **dos modos de cálculo** que
produce la herramienta, y **cómo hemos llegado a estas conclusiones** con
datos. Todas las cifras de ejemplo son agregadas por cláusula (sin datos
personales) de las cargas de agosto de 2026.

---

## 1. Qué hace el sistema

Recalcula y concilia la **bolsa de días de contratación temporal** de la
Gerencia entre dos aplicativos que **cuentan de forma distinta**:

- **PeopleNet** — sistema de **contratos**. Lleva la bolsa anual autorizada
  (`Días contratación`) y un contador de días consumidos (`Días Usados`).
- **Aplicativo de Propuestas** — libro de **reservas/movimientos**. Al aprobar
  una propuesta, resta días; al anular/devolver, los suma.

Cláusulas prioritarias: **N91c** (refuerzos) y **S9b1a** (sustituciones).
Todo se recalcula **desde el corte inmutable del 02/07/2026** para ser
**reproducible**: los mismos ficheros dan siempre el mismo resultado, sin
acumular error.

---

## 2. Cómo cuenta cada sistema (la clave de todo)

Los dos sistemas miden "días usados" de forma diferente, y de ahí nacen todas
las diferencias:

| | PeopleNet | Aplicativo de Propuestas |
|---|---|---|
| Cuenta | **Contratos a su fin REAL** (tope 31/12) | Días **comprometidos/reservados** al aprobar (a menudo hasta 31/12) |
| Momento | Al **mecanizar** el contrato | Al **aprobar** la propuesta |
| Cierres | Los refleja solo (contrato más corto → menos días) | Necesita una **devolución** manual (que a veces no se hace) |

**Consecuencia:** cuando una sustitución termina antes de tiempo, PeopleNet lo
refleja automáticamente (el contrato es más corto), pero el aplicativo de
Propuestas se queda con los días "gastados" hasta que alguien registra la
devolución. Ese desfase es la razón principal de que ambos no cuadren y de que
hagamos este cuadre.

### Prueba de que "Días Usados" de PeopleNet = contratos a fin real

Sumando cada contrato hasta su **fin real** (tope 31/12, dentro de 2026) por
cláusula, obtenemos **el mismo número** que el `Días Usados` oficial de
PeopleNet. El cuadre es **exacto** en casi todas las cláusulas:

| Cláusula | Comprometido a fin real (calculado) | Días Usados (PeopleNet) |
|---|--:|--:|
| N91b | 6.272 | 6.272 ✅ exacto |
| N91c | 116.046 | 116.046 ✅ exacto |
| S9b1a | 196.420 | 195.729 (99,6 %) |
| S9b1b | 274 | 274 ✅ exacto |
| S9b1c | 9.229 | 9.229 ✅ exacto |

El cuadre exacto de N91c demuestra que **el `Días Usados` de PeopleNet cuenta
cada contrato hasta su fin real** — y por tanto ya incorpora los cierres
anticipados. Este control se ejecuta en cada carga (pestaña
`A13_Usados_vs_Contratos`).

> El pequeño residuo de S9b1a (~0,3 %, estable) es una diferencia de convención
> interna de PeopleNet que no replicamos al día. No se puede atribuir a ningún
> contrato concreto (no hay solapes, ni plazas laborales, ni fechas raras). Es
> un **diagnóstico**: si algún día se disparara, indicaría contratos que faltan
> en el export o un descuadre real.

---

## 3. Los dos modos de cálculo

La herramienta produce **dos cifras de "disponible"**, que responden a preguntas
distintas y **no son comparables entre sí**.

### Modo A — "desde el corte" (histórico/reproducible)

Reconstruye el saldo por plaza partiendo del reparto del corte del 02/07 y
aplicando los movimientos posteriores:

```
saldo = postcontrol(02/07) − consumo + devoluciones + devolución_por_cierre ± ajuste
```

- **Base:** el reparto por plaza del corte del 02/07.
- **Mira:** propuestas/movimientos del aplicativo.
- **Devolución por cierre:** como el aplicativo reserva hasta 31/12, si el
  contrato cierra antes hay que devolver los días no usados.
- Es el modo que responde *«¿por qué tenía tantos días y ahora me quedan tan
  pocos?»* (pestaña web «Por Dirección»; fichero `recarga_propuestas`).

### Modo B — "anclado a PeopleNet" (el ideal)

Ancla el disponible en la **realidad de PeopleNet**, sin depender del
aplicativo:

```
disponible = Contratación − Usados_real(PeopleNet, a fin real) − Pendiente(reservas sin contrato)
```

- **Base:** la bolsa anual (Contratación), repartida a plaza/dirección con el
  reparto del corte.
- **Usados_real:** contratos a fin real → **ya lleva los cierres dentro**, así
  que este modo **no necesita la devolución por cierre** ni arrastra los
  errores del aplicativo.
- **Pendiente:** propuestas aprobadas sin contrato (reservas a la espera de
  mecanizar).
- **Ajuste al oficial:** nuestro recuento por contrato se escala (~0,3 %) para
  que su suma por cláusula sea **exactamente** el `Días Usados` oficial de
  PeopleNet. Así el disponible cuadra con el Margen sin arrastrar el residuo.
- **Control por DIRECCIÓN:** que cada dirección sume ≥ 0 (una plaza suelta puede
  ir en negativo mientras la dirección global sume positivo).
- Ficheros: pestañas `B1_Anclado_PeopleNet_Direccion`, `B2_..._Plaza`,
  `B3_Sin_GFH`; fichero `recarga_anclada_PeopleNet`; pestaña web «Anclado
  PeopleNet».

Los dos modos se generan **en paralelo** para poder compararlos.

---

## 4. Por qué las dos cifras de "disponible" no son comparables

- **Disponible PeopleNet** = `Contratación − Días Usados`. Base: la **bolsa
  anual global** por cláusula.
- **Saldo del aplicativo** (modo A) = parte del **reparto por plaza del corte**.

Parten de bases distintas, así que **restar una de otra no mide nada** (es como
restar kilómetros menos litros). La prueba de que no es un control válido: el
signo de la diferencia **cambia según la cláusula** (en una el aplicativo queda
por debajo, en otra por encima); una fuga real sería siempre del mismo signo.

### El único control válido: el Margen

```
Margen = Contratación − ( Días Usados + Reservas sin contrato )
```

Todo sobre la **misma base** (la de PeopleNet). Si es **positivo**, no se ha
comprometido más de lo autorizado. Ejemplo: N91c +10.034, S9b1a +43.297 → ambos
verdes. Ese es el número que responde a *«¿nos hemos pasado?»*.

---

## 5. Cómo llegamos a estas conclusiones (con datos)

1. **El origen de la bolsa (14/05/2026).** La bolsa inicial salió del **gasto
   del año anterior menos ~10 %**: N91c 99.303 = 90,03 % de 110.301 (gasto
   2025); S9b1a 208.575 = 90,27 % de 231.063. En junio se **amplió** (+28.383
   N91c → 127.686; S9b1a → 240.069) porque ese −10 % dejaba muy poco margen.

2. **El corte del 02/07 es "anticipador".** Nuestro corte llevaba ya cargados
   los compromisos que PeopleNet fue mecanizando durante julio: el nivel de
   usados que implica el corte coincide con el que PeopleNet alcanza hacia el
   31/07. Es decir, el corte **anticipó** y PeopleNet **convergió** a él. No
   estaba inflado ni corto.

3. **PeopleNet cuenta los cierres.** El `Días Usados` puede **bajar** (lo vimos:
   S9b1a 183.200 el 14/05 → 177.642 el 23/06). Y el cuadre exacto de N91c
   (A13) demuestra que cuenta contratos a fin real. Por eso el modo anclado no
   necesita reconstruir cierres: los toma de PeopleNet.

4. **Las dos cifras de disponible no se pueden comparar** (§4). El control es el
   Margen, no la resta.

5. **El residuo ~0,3 % de S9b1a** no es un error (no hay solapes ni laborales
   ni fechas raras); es convención de PeopleNet. En el modo anclado se **ancla
   al oficial** para que no reste disponible; en A13 se muestra como
   diagnóstico.

---

## 5bis. Saldo inicial 01/01/2026 reconstruido (solo PeopleNet)

Además de los dos modos, la herramienta reconstruye **hacia atrás** un saldo a
**01/01/2026** por plaza y dirección, con dos exigencias:

1. que en el **corte (02/07/2026)** coincida **exactamente** con el saldo real
   (el `postcontrol`), y
2. que muestre lo que **quedaría hoy** solo con los **movimientos de PeopleNet**
   (contratos), *olvidando las propuestas comprometidas* (se añaden después).

Por cada (plaza, dirección, cláusula):

```
Saldo inicial 01/01  = Saldo en el corte + Consumo PeopleNet AL corte
Saldo en el corte    = postcontrol(02/07)          (coincide por construcción)
Saldo actual solo-PN = Saldo en el corte − Consumo PeopleNet DESDE el corte
                     = Saldo inicial 01/01 − Consumo PeopleNet total
```

- **Consumo PeopleNet** = cada contrato a su **fin real** (tope 31/12),
  repartido a la división real por tramo GFH — igual que el `Días Usados`.
- El reparto de un contrato entre *al corte* / *desde el corte* se hace por su
  **fecha de inicio** (≤ 02/07 = al corte; posterior = desde el corte). Es
  **robusto**: no depende de la fecha de *alta* reconstruida, que desplazaría
  contratos antiguos (con este dato, ~9.000 días N91c y ~17.500 S9b1a se
  clasificaban mal como "posteriores").
- El consumo previo al corte **ya está dentro del postcontrol**, así que no se
  vuelve a restar: para un contrato íntegramente previo, el *saldo actual* es el
  del corte.
- **No** incluye las reservas sin contrato (propuestas comprometidas): es la
  **foto solo-PeopleNet**. El disponible con reservas es el modo anclado (B1–B3).

Comprobación automática: la columna *Saldo en el corte* suma **exactamente** el
`postcontrol` por cláusula (prueba `test_saldo_inicial`). El saldo inicial
reconstruido queda muy cerca de la bolsa anual (N91c ~124.000 sobre 127.686;
S9b1a ~233.000 sobre 240.069): la diferencia es el margen aún **no repartido**
a plaza. Salidas: pestañas `C1_Saldo_01_01_Direccion` y `C2_..._Plaza` de la
conciliación, y el fichero `saldo_inicial_01_01_2026_<fecha>.xlsx`.

## 6. Controles que se ejecutan en cada carga

| Pestaña / salida | Qué controla |
|---|---|
| `4_Semaforo` | Margen por cláusula (verde/ámbar/rojo). El control de sobre-compromiso. |
| `A13_Usados_vs_Contratos` | Que el `Días Usados` de PeopleNet cuadra con los contratos (diagnóstico). |
| `B1_Anclado_PeopleNet_Direccion` | Disponible anclado por **dirección** (verde si su global ≥ 0). |
| `B2_..._Plaza` | Desglose por plaza del modo anclado. |
| `B3_Sin_GFH` | Contratos cuyo GFH falta en el maestro de Divisiones (DNI + GFH a añadir). |
| `C1`/`C2` | Saldo inicial 01/01/2026 reconstruido (cuadra con el corte); saldo actual solo-PeopleNet. |
| `A1`–`A12` | Reservas, cierres, cláusula/dirección distinta, coherencia del enlace, etc. |

---

## 7. Ficheros necesarios en cada carga

**Imprescindibles** (el cálculo anclado se apoya aquí):
- **Contratos_PeopleNet** — el `Usados_real` (el ancla).
- **Bolsa_PeopleNet** (`Días contratación` + `Días Usados`) — la bolsa oficial.
- **PropuestasContratacion** — el `Pendiente` (reservas sin contrato) y las
  búsquedas por DNI/propuesta.
- **Maestro de Divisiones** (`data/maestros`) — dirección real por GFH.
- **Corte inicial** (`data/inicial`, no se toca) — el reparto por plaza.

**Opcionales** (ya no entran en el cálculo anclado):
- **MovimientosBolsa** — solo para el informe «¿ya hicieron el movimiento?» y
  auditoría.
- **SaldoActualPropuestas** — solo para comparar con el aplicativo.

---

## 8. En una frase (para dirección)

> Las dos cifras de *disponible* (PeopleNet y aplicativo) **no son comparables**
> porque se calculan sobre bases distintas. El control de **no habernos pasado**
> es el **Margen** (lo autorizado menos lo comprometido), positivo en las dos
> cláusulas. Y el modo **anclado a PeopleNet** carga el disponible tomando el
> gasto **real** de PeopleNet (que ya cuenta los cierres), sin depender de los
> errores del aplicativo de Propuestas.
