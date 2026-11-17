# Diagramas para la defensa

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Cinco dibujos para explicar el diseño en la pizarra, cada uno con los números que lo acompañan y el archivo de donde salen. Están en texto a propósito: se copian a mano en la pizarra en un minuto, y no hay que buscar una figura.

## 1. El SoC: qué hay alrededor del core

```
                         +--------------------------- pochoco_soc (rtl/pochoco_soc.v) ---------------------------+
   maestra SPI           |                                                                                        |
   CS_n, SCLK, MOSI ---->|  u_spi: esclavo SPI (rtl/pochoco_spi_slave.v)  0x8001_0000                              |
   MISO <----------------|    STATUS (precio nuevo), PRICE, DECISION      byte_done, new_price_q, wr, off         |
                         |         ^  |                                     (nombres que el testbench usa)       |
                         |   bus   |  v                                                                           |
                         |  +--------------+      +---------------------+      +-----------------------------+   |
                         |  | core Espino  |<---->| memoria (2 KB, BRAM)|      | tabla de parámetros (R1, R2)|   |
                         |  | base, segm.  |      | programa y datos    |      | 256 x 16 bits, solo lectura |   |
                         |  | o barrel     |<-----|  0x0000_0000        |      | 0x8002_0000 (BRAM aparte)   |   |
                         |  +--------------+      +---------------------+      +-----------------------------+   |
                         |         |                                                                              |
                         |         v                                                                              |
                         |  periférico de la placa 0x8000_0000: dos dígitos y cuatro LED (telemetría)            |
                         |                                                                                        |
                         |  vigilante (solo R2, rtl/vigilante.v): 5 precios sin escritura en DECISION -> BOOT   |
                         +----------------------------------------------------------------------------------------+
```

- Todo es BRAM con lectura registrada: la memoria, el banco de registros y la tabla. Eso define el CPI de cada core (secciones 2 a 4).
- El testbench oficial entra por jerarquía a `u_spi`; por eso ningún peldaño cambia el esclavo ni esos nombres (`docs/defensa/espino_base.md`, sección 3).
- R0: base sin tabla ni vigilante, 1091 celdas, 12 BRAM. R1: barrel, `emad` y `devk`, tabla: 1029 celdas, 13 BRAM. R2: R1 más el vigilante: 1045 celdas (`docs/mediciones/p7/variantes.txt`).

## 2. Espino base: dos fases por instrucción (CPI 2)

```
flanco      N               N+1              N+2
            |                |                |
memoria  ---+ sale la instr. |                |
            | rs1, rs2 -> banco (BRAM)        |
            |   espera un flanco (ops_valid_q)|
banco       |                + operandos      |
            |                | ALU, salto,    + se escribe rd, avanza el PC
            |                | bus            |
            <---- fase 1 ---><---- fase 2 ---->
```

| Instrucción | Ciclos | Por qué |
|-------------|--------|---------|
| ALU, store, salto no tomado | 2 | La espera del banco (`rtl/espino_core/espino_id_stage.v:209`) |
| Load | 3 | Un ciclo más esperando el dato (`espino_load_store_unit.v:45`) |
| Salto tomado | 3 | La instrucción siguiente entra inválida (`espino_if_stage.v:50`) |

Con `sw/trade.s`: 19,5 instrucciones en promedio y 21 en el peor caso de `byte_done` a `DECISION`, CPI 2,10, 41 ciclos de respuesta en promedio y 44 de peor caso (`docs/defensa/cifras.md`).

## 3. Espino segmentado: tres etapas en dos ciclos

```
           subida            bajada             subida             bajada            subida
             |                 |                  |                  |                 |
instr i      |--- IF: la BRAM lee en bajada --->|                                      |
             |                 |--- ID: rs1, rs2, decodifica --->|                      |
             |                 |                  |--- EX: ALU, bus, escribe rd ------>|
instr i+1    |                 |                  |--- IF ---------->|--- ID -------->|--- EX ...
```

- IF y ID de la instrucción siguiente ocurren en el mismo ciclo que el EX de la actual: sale una instrucción por ciclo.
- El banco tiene escritura adelantada: un `rd` escrito en el flanco se lee en la instrucción siguiente sin esperar.
- Load 2 ciclos, salto tomado 2. Con `sw/trade.s` el CPI medido es 1,350 y la respuesta 22 ciclos promedio, 26 peor (`docs/espino_segmentado.md`, `docs/defensa/cifras.md`).

## 4. Espino barrel: cuatro hilos, una etapa cada uno

```
ciclo      1   2   3   4   5   6   7   8
hilo 0     F   R   X   M   F   R   X   M
hilo 1     M   F   R   X   M   F   R   X
hilo 2     X   M   F   R   X   M   F   R
hilo 3     R   X   M   F   R   X   M   F

F: el PC del hilo direcciona la memoria        X: ALU, salto, petición al bus
R: sale la instrucción, banco con {hilo, reg}  M: llega el dato del load, se escribe {hilo, rd}
```

```
   +-------+  {hilo, PC}   +---------+  instr  +------------------------+  operandos  +-----+      +-----------+
   | 4 PCs |-------------->| memoria |-------->| banco {hilo, reg} 64x32|------------>| ALU |----->| bus, carga|
   +-------+               | (BRAM)  |         | 2 copias en BRAM       |             +-----+      | y escritura|
       ^                   +---------+         +------------------------+                         +-----------+
       |                       F | R                       R | X                         X | M             |
       +----------------------------- PC siguiente del hilo (X) -------------------------------------------+
```

- **No hay riesgos**: cuando un hilo vuelve a F, su instrucción anterior ya escribió en M. No hay adelantamiento ni burbujas (`docs/defensa/barrel.md`, sección 3).
- **Cada BRAM cae en una frontera entre etapas**: su registro de salida es el registro de pipeline. Por eso es el core más pequeño (932 celdas solo, contra 1091 del base en la misma medición, `docs/mediciones/p7/variantes.txt`).
- CPI 4 por hilo y 1 agregado, sin excepciones.

## 5. Un tick por los cuatro hilos del fondo (R1)

```
tiempo (ciclos desde byte_done)  0         36             ~80            ~130-220                 ~223 (prom.)   444 (peor)
                                 |          |              |                 |                        |              |
maestra   CS_n baja, 8 bits ---> byte_done                                                                     (siguiente
                                 |                                                                              transacción:
supervisor (hilo 0)  sondea STATUS -> lee PRICE -> PUB = tick*256+precio -> max_media propia -> lee EST_1..3 -> voto ponderado -> DECISION
                                                    |                                         ^  (lazo de 48 ciclos,                  lee el byte)
gestor 1 (hilo 1)    sondea PUB  ------------------>+-> puntaje, regla (-96, sale > 0) ------>| EST_1 = tick*256 + pos
gestor 2 (hilo 2)    sondea PUB  ------------------>+-> puntaje, regla (-128, sale > 0) ----->| EST_2
gestor 3 (hilo 3)    sondea PUB  ------------------>+-> puntaje, regla (-64, sale > +16) ---->| EST_3
                                                                                              hasta 8 vueltas (PLAZO)
```

Cómo se lee:

1. La maestra termina de mandar el precio: `byte_done`. El supervisor está sondeando `STATUS` (lazo de 12 ciclos) y lo ve.
2. Lee `PRICE` y publica `PUB = tick * 256 + precio` en **un solo store**: un gestor nunca ve un precio con el número de otro tick. Hasta aquí, a lo más 36 ciclos.
3. Los tres gestores, que sondeaban `PUB` (lazo de 8 ciclos), corren cada uno su regla con su umbral y publican primero su puntaje (`DES_k`) y al final su voto (`EST_k = tick * 256 + posición`).
4. Mientras tanto el supervisor calcula su propia `max_media` (44 ciclos), que reemplaza cualquier voto que no llegue.
5. Lee los tres `EST_k` en un lazo de 48 ciclos y les resta `tick * 256`: 0 o 1 es un voto de este tick; 2 o más es viejo. Con los tres sanos sale en la segunda o tercera vuelta; a la octava se rinde y decide sin los que faltan.
6. Suma los pesos de los votos de compra (6, 5 y 5 dieciseisavos al comenzar, ajustados cada 512 ticks) y compara con 8: comprar 63 o vender 63. Escribe `DECISION` una vez y un registro de telemetría.
7. La maestra lee ese byte en la transacción siguiente y lo ejecuta al precio de ese tick.

Números: 223,01 ciclos en promedio, 444 de peor caso barriendo la fase (19,6 % de los 2262 de la ronda 3), 568 con el plazo agotado, 679 con un gestor atrasado a propósito; límite de la puerta 1131 (`docs/fondo.md`, sección 1). La decisión no depende de cuántos ciclos demora cada hilo, solo de los valores: por eso `ref/fondo.py` no modela ciclos y coincide byte por byte.

## 6. La escalera y el relevo de R2

```
R2 (r2_multi.bin, imagen múltiple en la flash)
  imagen 0: R1 + vigilante  --- 5 precios sin escribir DECISION ---> BOOT (SB_WARMBOOT) con CS_n en alto
                                                                         |
                                       35,50 ms medidos en la placa      v   (MISO con pull-up: la maestra lee 0xFF = mantener)
  imagen 1: R0 (Espino base con max_media, sin vigilante) <--- arranca, reset de 0,164 ms, decide desde cero
```

361 ticks sin decisión nueva a 0,1 ms, 40 a 1 ms y 8 a 10 ms (`docs/mediciones/placa_16nov.md`). La imagen de respaldo no tiene vigilante, para que no exista un ciclo de reinicios.
