# trade_ema.s: la regla base de sw/trade.s con la extensión de la ISA (pieza D).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Variante: ema. El bloque 6 pasa de 8 instrucciones a 1. 32 p queda en x10.
# Es el mismo algoritmo y entrega las mismas decisiones que sw/trade.s
# (referencia bit a bit: ref/trader.py, ReglaBase). Solo cambian los bloques
# marcados con "XD". El detalle del algoritmo y de los registros está en
# sw/trade.s y en docs/trade_s.md.
#
# Las instrucciones nuevas no las conoce tools/pochoasm.py: antes de ensamblar
# se pasan a .word con factibilidad/d_isa/tools/xd_word.py --pre (make sw).
# Necesita el core con -DXD_EMA=0 (con o sin -DXD_EMAALU).

.equ SPI_BASE,      0x80010000
.equ OFF_STATUS,    0
.equ OFF_PRICE,     4
.equ OFF_DECISION,  8

.equ K,             5          # alfa = 1/32
.equ UMBRAL_COMPRA, -128
.equ UMBRAL_VENTA,  1
.equ VENDER_63,     0xBF
.equ COMPRAR_MENOS_VENDER, -64

_start:
    li   x2, SPI_BASE
    li   x4, 0                 # pos = 0: afuera

# --- Primer precio: la media parte en ese precio (S = 32 p) ------------------
primero:
    lw   x7, OFF_STATUS(x2)
    andi x7, x7, 1
    beqz x7, primero
    lw   x5, OFF_PRICE(x2)
    add  x10, x5, x5            # 2 p
    add  x10, x10, x10            # 4 p
    add  x10, x10, x10            # 8 p
    add  x10, x10, x10            # 16 p
    add  x10, x10, x10            # 32 p
    mv   x3, x10               # S = 32 p, asi dev = 0 y no se opera
    j    decidir

# --- 1. Esperar el precio -----------------------------------------------------
esperar:
    lw   x7, OFF_STATUS(x2)
    andi x7, x7, 1
    beqz x7, esperar

# --- 2. Leer ------------------------------------------------------------------
    lw   x5, OFF_PRICE(x2)

# --- 3. Predecir: dev = 32 p - S ---------------------------------------------
    add  x10, x5, x5            # 2 p
    add  x10, x10, x10            # 4 p
    add  x10, x10, x10            # 8 p
    add  x10, x10, x10            # 16 p
    add  x10, x10, x10            # 32 p
decidir:
    sub  x6, x10, x3           # dev = 32 p - S

# --- 4. Decidir, sin saltos ---------------------------------------------------
    slti x7, x6, UMBRAL_COMPRA # 1 si hay que entrar
    slti x9, x6, UMBRAL_VENTA  # 0 si hay que salir
    or   x4, x4, x7            # pos = (pos | entrar) & no_salir
    and  x4, x4, x9
    sub  x7, x0, x4
    andi x7, x7, COMPRAR_MENOS_VENDER
    addi x8, x7, VENDER_63     # 0xBF (vender 63) o 0x7F (comprar 63)

# --- 5. Escribir la decision (una sola vez por tick) -------------------------
    sw   x8, OFF_DECISION(x2)

# --- 6. Actualizar la media ---------------------------------------------------
    ema  x3, x10, x3, K        # XD: S = S + ((32 p - S) >>> 5)
    j    esperar

# Relleno con ceros hasta las 512 palabras de la RAM
.org 0x800
