# =============================================================================
# fondo.s: programa de R1 y R2 desde el 17/11 (decisión T133, opción F-a). El
# hilo 0 del Espino barrel corre la regla de cotas (desde el 19/11 con banda 40,
# decisión T140: solo cambió la tabla); los hilos 1, 2 y 3 quedan
# en un lazo de espera. El nombre del archivo se mantiene porque todas las
# herramientas de R1 y R2 lo usan; hasta el 17/11 era el fondo de cuatro hilos
# que votaba (docs/fondo.md, historial de git).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Corre en el Espino barrel compilado con -DESPINO_XD_EMAD, -DESPINO_XD_DEVK y
# -DESPINO_TABLA (el hardware de R1 y R2 no cambia). No usa la extensión.
# Referencia byte a byte: ref/fondo.py, que decide igual que ref/trader.py
# (Oficial, la regla de sw/trade.s en R0).
#
# Regla (docs/cotas.md): las series se normalizan de modo que su mínimo es 100
# y su máximo 255.
#   p <= 100   -> comprar 63 y recordar que se vio el mínimo
#   p >= 255   -> vender 63 y recordar que se vio el máximo
#   con los dos extremos ya vistos: p <= 140 -> comprar 63; p >= 215 -> vender 63
#   si no      -> repetir el último byte (parte en 0x00, mantener)
# Los cuatro umbrales salen de la tabla de parámetros en cada tick (BRAM de
# solo lectura en 0x8002_0000; se cambian con icebram sin sintetizar):
#   T_LO_MAS_1 = 101, T_HI = 255, T_BANDA_COMPRA = 141, T_BANDA_VENTA = 215
#   (banda 40; con banda 60 eran 161 y 195).
#
#   hilo 0   sondea el SPI, lee el precio, decide sin saltos que dependan del
#            precio, escribe DECISION una vez por tick y después un registro
#            de telemetría. Es el único hilo que toca el SPI y el periférico.
#   hilos 1 a 3   un lazo de un salto. No leen ni escriben memoria.
#
# Telemetría, un store por tick después de decidir:
#   ticks pares   los 7 segmentos muestran 63 si el byte es comprar 63, si no 00
#   ticks impares LED 0 latido (bit 10 del número de tick), LED 1 se vio el
#                 mínimo, LED 2 se vio el máximo, LED 3 adentro (comprar 63)
#
# Registros del hilo 0:
#   x1 base de la tabla   x2 base del SPI    x3 número de tick (desde 1)
#   x4 q, el último byte  x5 p               x6 bajo   x7 alto   x8 los dos
#   x9 comprar   x10 se vio el mínimo   x11 se vio el máximo   x12 vender
#   x13 umbral y máscara  x14 byte nuevo y base del periférico  x15 temporal
#
# Las líneas que empiezan con "#@" son marcas para tools/fondo/variante.py,
# que arma desde este mismo archivo los programas con fallas puestas a
# propósito (pruebas de degradación y del vigilante).
# =============================================================================

.equ SPI_BASE,      0x80010000
.equ OFF_STATUS,    0          # bit 0: precio nuevo
.equ OFF_PRICE,     4
.equ OFF_DECISION,  8
.equ PER_BASE,      0x80000000 # periférico de la placa
.equ PER_DIGITOS,   0          # dos dígitos de 7 segmentos
.equ PER_LEDS,      4          # cuatro LED
.equ COMPRAR_63,    0x7F
.equ VENDER_MENOS_COMPRAR, 0x40  # 0xBF - 0x7F
.equ DIGITOS_ADENTRO, 0x63     # los 7 segmentos muestran 63 o 00
.equ BIT_LATIDO,    0x400      # bit 10 del número de tick
.equ TAB_BASE,      0x80020000
.equ T_LO_MAS_1,    0          # bajo si p < este valor (101)
.equ T_HI,          4          # alto si p >= este valor (255)
.equ T_BANDA_COMPRA, 8         # con los dos extremos vistos, compra si p < este valor (141)
.equ T_BANDA_VENTA, 12         # y vende si p >= este valor (215)

# --- Tabla de arranque: el hilo t parte en la dirección 4 t -------------------
    j    supervisor
    j    hilo1
    j    hilo2
    j    hilo3

# --- Hilos 1 a 3: sin trabajo -------------------------------------------------
hilo1:
#@HILO1
    j    hilo1
hilo2:
#@HILO2
    j    hilo2
hilo3:
#@HILO3
    j    hilo3

# --- Hilo 0 -------------------------------------------------------------------
supervisor:
    li   x1, TAB_BASE
    li   x2, SPI_BASE
    li   x3, 0                 # todavía no hay ningún tick
    li   x4, 0                 # q = mantener: parte en caja
    li   x10, 0                # todavía no se ve el mínimo
    li   x11, 0                # ni el máximo

# 1. Esperar un precio nuevo y leerlo (la lectura baja la bandera)
s_espera:
    lw   x15, OFF_STATUS(x2)
    andi x15, x15, 1
    beqz x15, s_espera
    lw   x5, OFF_PRICE(x2)
#@SUPERVISOR

# 2. Comparar contra los umbrales de la tabla
s_decidir:
    lw   x13, T_LO_MAS_1(x1)
    sltu x6, x5, x13           # bajo = p <= 100
    lw   x13, T_HI(x1)
    sltu x7, x5, x13
    xori x7, x7, 1             # alto = p >= 255
    lw   x13, T_BANDA_COMPRA(x1)
    sltu x9, x5, x13           # p <= 140
    lw   x13, T_BANDA_VENTA(x1)
    sltu x12, x5, x13
    xori x12, x12, 1           # p >= 215

# 3. Decidir sin saltos, igual que sw/trade.s
    or   x10, x10, x6          # se vio el mínimo
    or   x11, x11, x7          # se vio el máximo
    and  x8, x10, x11          # los dos
    and  x9, x9, x8            # comprar = bajo | (los dos & p <= 140)
    or   x9, x9, x6
    and  x12, x12, x8          # vender = alto | (los dos & p >= 215)
    or   x12, x12, x7
    or   x13, x9, x12          # cambia (comprar y vender nunca son 1 a la vez)
    sub  x13, x0, x13          # 0 o 0xFFFFFFFF
    sub  x14, x0, x12          # 0xFFFFFFFF si vende
    andi x14, x14, VENDER_MENOS_COMPRAR
    addi x14, x14, COMPRAR_63  # 0x7F (comprar 63) o 0xBF (vender 63)
    xor  x15, x14, x4          # q = cambia ? byte nuevo : q
    and  x15, x15, x13
    xor  x4, x4, x15
    sw   x4, OFF_DECISION(x2)

# 4. Telemetría: un store por tick, después de decidir
s_telemetria:
    addi x3, x3, 1             # número de este tick
    xori x15, x4, COMPRAR_63
    sltiu x15, x15, 1          # 1 si está adentro (comprar 63)
    li   x14, PER_BASE
    andi x13, x3, 1
    bnez x13, t_leds
    sub  x15, x0, x15          # ticks pares: 7 segmentos
    andi x15, x15, DIGITOS_ADENTRO
    sw   x15, PER_DIGITOS(x14)
    j    s_espera
t_leds:
    add  x15, x15, x15         # LED 3: adentro
    add  x15, x15, x15
    add  x15, x15, x15
    add  x13, x11, x11         # LED 2: se vio el máximo
    add  x13, x13, x13
    or   x15, x15, x13
    add  x13, x10, x10         # LED 1: se vio el mínimo
    or   x15, x15, x13
    li   x13, BIT_LATIDO       # LED 0: latido
    and  x13, x13, x3
    sltu x13, x0, x13
    or   x15, x15, x13
    sw   x15, PER_LEDS(x14)
    j    s_espera
