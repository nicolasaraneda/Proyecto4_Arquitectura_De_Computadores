# trade.s: programa de inversion para el Pochoco SoC (Espino Core, RV32E).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Variante: solo software. Referencia bit a bit: ref/trader.py (Oficial, que es
# la regla de cotas de ref/regla_cotas.py con inicio "espera" y banda 40).
#
# Algoritmo: cotas, "espera" con banda 40 (decision T140, docs/cotas.md; del
# 17/11 al 19/11 fue banda 60, decision T133). Las
# series de la competencia se normalizan de modo que su minimo es 100 y su
# maximo 255:
#   si p <= 100      -> comprar 63 (y recordar que se vio el minimo)
#   si p >= 255      -> vender 63 (y recordar que se vio el maximo)
#   si ya se vieron los dos extremos:
#       p <= 140     -> comprar 63
#       p >= 215     -> vender 63
#   si no            -> repetir la decision anterior
# Parte en caja: hasta el primer extremo escribe 0x00 (mantener). Si la serie
# no toca ningun extremo, no opera.
#
# La maestra recorta cada orden a lo que alcanza con la caja o con las
# acciones, asi que repetir "comprar 63" o "vender 63" no paga comisiones de
# mas. Por eso el programa no lleva contabilidad.
#
# Ciclo principal:
#   1. esperar   sondea STATUS[0] hasta que haya un precio nuevo
#   2. leer      lee PRICE (la lectura baja la bandera)
#   3. comparar  cuatro comparaciones con sltiu, independientes entre si
#   4. decidir   actualiza las banderas y arma el byte con mascaras, sin saltos
#   5. escribir  un solo store a DECISION, con la decision definitiva
# No hay saltos que dependan del precio: el tiempo de respuesta es el mismo en
# cada tick. El unico salto que depende de algo externo es el del sondeo.
#
# Registros:
#   x2  base del esclavo SPI (0x8001_0000)
#   x4  q, el ultimo byte escrito (0x00, 0x7F o 0xBF)
#   x5  p, el ultimo precio (1 a 255)
#   x6  bajo: p <= 100
#   x7  alto: p >= 255
#   x8  los dos extremos ya vistos
#   x9  comprar
#   x10 se vio el minimo (queda en 1)
#   x11 se vio el maximo (queda en 1)
#   x12 vender
#   x13 mascara "cambia"
#   x14 byte nuevo
#   x15 temporal
#
# El .org del final rellena el .hex hasta las 512 palabras, para que la
# simulacion y la placa partan con la misma memoria.

.equ SPI_BASE,      0x80010000
.equ OFF_STATUS,    0          # bit 0: precio nuevo, bit 1: CS activo
.equ OFF_PRICE,     4          # precio recibido (1 a 255)
.equ OFF_DECISION,  8          # byte que la maestra lee en la proxima transaccion

.equ LO_MAS_1,      101        # bajo si p < 101: el minimo de la serie es 100
.equ HI,            255        # alto si p >= 255: el maximo es 255
.equ BANDA_COMPRA,  141        # con los dos extremos vistos, compra si p < 141 (100 + 40)
.equ BANDA_VENTA,   215        # y vende si p >= 215 (255 - 40)
.equ COMPRAR_63,    0x7F       # accion 01, cantidad 63
.equ VENDER_MENOS_COMPRAR, 0x40  # 0xBF - 0x7F

_start:
    li   x2, SPI_BASE
    li   x4, 0                 # q = mantener: parte en caja
    li   x10, 0                # todavia no se ve el minimo
    li   x11, 0                # ni el maximo

esperar:
    lw   x7, OFF_STATUS(x2)
    andi x7, x7, 1
    beqz x7, esperar
    lw   x5, OFF_PRICE(x2)
    sltiu x6, x5, LO_MAS_1     # bajo = p <= 100
    sltiu x7, x5, HI           # p < 255
    xori x7, x7, 1             # alto = p >= 255
    sltiu x9, x5, BANDA_COMPRA # p <= 140
    sltiu x12, x5, BANDA_VENTA # p < 215
    xori x12, x12, 1           # p >= 215
    or   x10, x10, x6          # se vio el minimo
    or   x11, x11, x7          # se vio el maximo
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
    j    esperar

# Relleno con ceros hasta las 512 palabras de la RAM
.org 0x800
