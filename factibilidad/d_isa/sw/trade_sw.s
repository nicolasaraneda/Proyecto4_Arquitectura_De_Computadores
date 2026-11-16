# trade_sw.s: la regla base de sw/trade.s con la extensión de la ISA (pieza D).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Variante: solo software (copia de sw/trade.s, para medir con el mismo flujo).
# Es el mismo algoritmo y entrega las mismas decisiones que sw/trade.s
# (referencia bit a bit: ref/trader.py, ReglaBase). Solo cambian los bloques
# marcados con "XD". El detalle del algoritmo y de los registros está en
# sw/trade.s y en docs/trade_s.md.
#
# Las instrucciones nuevas no las conoce tools/pochoasm.py: antes de ensamblar
# se pasan a .word con factibilidad/d_isa/tools/xd_word.py --pre (make sw).
# Necesita el core con cualquier variante (no usa instrucciones nuevas).

.equ SPI_BASE,      0x80010000
.equ OFF_STATUS,    0
.equ OFF_PRICE,     4
.equ OFF_DECISION,  8

.equ K,             5          # alfa = 1/32
.equ UMBRAL_COMPRA, -128
.equ UMBRAL_VENTA,  1
.equ VENDER_63,     0xBF
.equ COMPRAR_MENOS_VENDER, -64
.equ TMP,           0x7FC
.equ TMP_BYTE1,     0x7FD

_start:
    li   x2, SPI_BASE
    li   x4, 0                 # pos = 0: afuera

# --- Primer precio: la media parte en ese precio (S = 32 p) ------------------
primero:
    lw   x7, OFF_STATUS(x2)
    andi x7, x7, 1
    beqz x7, primero
    lw   x5, OFF_PRICE(x2)
    add  x6, x5, x5            # 2 p
    add  x6, x6, x6            # 4 p
    add  x6, x6, x6            # 8 p
    add  x6, x6, x6            # 16 p
    add  x6, x6, x6            # 32 p
    mv   x3, x6                # S = 32 p, asi dev = 0 y no se opera
    j    decidir

# --- 1. Esperar el precio -----------------------------------------------------
esperar:
    lw   x7, OFF_STATUS(x2)
    andi x7, x7, 1
    beqz x7, esperar

# --- 2. Leer ------------------------------------------------------------------
    lw   x5, OFF_PRICE(x2)

# --- 3. Predecir: dev = 32 p - S ---------------------------------------------
    add  x6, x5, x5            # 2 p
    add  x6, x6, x6            # 4 p
    add  x6, x6, x6            # 8 p
    add  x6, x6, x6            # 16 p
    add  x6, x6, x6            # 32 p
decidir:
    sub  x6, x6, x3            # dev = 32 p - S

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
    addi x7, x3, 31            # S + 31
    add  x7, x7, x7            # por 2
    add  x7, x7, x7            # por 4
    add  x7, x7, x7            # por 8
    sw   x7, TMP(x0)
    lbu  x7, TMP_BYTE1(x0)     # ((S + 31) * 8) >> 8 = (S + 31) >> 5
    add  x3, x3, x5
    sub  x3, x3, x7
    j    esperar

# Relleno con ceros hasta las 512 palabras de la RAM
.org 0x800
