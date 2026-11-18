# trade_p20b70.s: variante de sw/trade.s, "comprar 20 al inicio, banda 70".
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Variante de contingencia (docs/cotas.md, R-b): solo se usa si el ayudante confirma
# que cada ronda se normaliza por separado y Nicolas la elige. Referencia bit a bit:
# ref/regla_cotas.Cotas("parte", k=20, banda=70). Se verifica con
# tools/variante_cotas.sh, que corre la puerta de R0 con este programa.
#
# Algoritmo: cotas, "comprar 20 al inicio" con banda 70. Las
# series de la competencia se normalizan de modo que su minimo es 100 y su
# maximo 255:
#   si p <= 100      -> comprar 63 (y recordar que se vio el minimo)
#   si p >= 255      -> vender 63 (y recordar que se vio el maximo)
#   si ya se vieron los dos extremos:
#       p <= 170     -> comprar 63
#       p >= 185     -> vender 63
#   si no            -> repetir la decision anterior
# Con el primer precio que ve, si no es un extremo, escribe una sola vez "comprar
# 20" (0x54) y despues mantener hasta el primer extremo. Si la serie no toca ningun
# extremo, queda con esas 20 acciones.
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
#   x3  1 hasta el primer precio, despues 0
#   x1  byte que se escribe (el de q, o "comprar 20" en el primer precio)
#
# El .org del final rellena el .hex hasta las 512 palabras, para que la
# simulacion y la placa partan con la misma memoria.

.equ SPI_BASE,      0x80010000
.equ OFF_STATUS,    0          # bit 0: precio nuevo, bit 1: CS activo
.equ OFF_PRICE,     4          # precio recibido (1 a 255)
.equ OFF_DECISION,  8          # byte que la maestra lee en la proxima transaccion

.equ LO_MAS_1,      101        # bajo si p < 101: el minimo de la serie es 100
.equ HI,            255        # alto si p >= 255: el maximo es 255
.equ BANDA_COMPRA,  171        # con los dos extremos vistos, compra si p < 171 (100 + 70)
.equ BANDA_VENTA,   185        # y vende si p >= 185 (255 - 70)
.equ COMPRAR_K,     0x54       # accion 01, cantidad 20: la compra del primer precio
.equ COMPRAR_63,    0x7F       # accion 01, cantidad 63
.equ VENDER_MENOS_COMPRAR, 0x40  # 0xBF - 0x7F

_start:
    li   x2, SPI_BASE
    li   x4, 0                 # q = mantener: parte en caja
    li   x10, 0                # todavia no se ve el minimo
    li   x11, 0                # ni el maximo
    li   x3, 1                 # el proximo precio es el primero

esperar:
    lw   x7, OFF_STATUS(x2)
    andi x7, x7, 1
    beqz x7, esperar
    lw   x5, OFF_PRICE(x2)
    sltiu x6, x5, LO_MAS_1     # bajo = p <= 100
    sltiu x7, x5, HI           # p < 255
    xori x7, x7, 1             # alto = p >= 255
    sltiu x9, x5, BANDA_COMPRA # p <= 160
    sltiu x12, x5, BANDA_VENTA # p < 195
    xori x12, x12, 1           # p >= 195
    or   x10, x10, x6          # se vio el minimo
    or   x11, x11, x7          # se vio el maximo
    and  x8, x10, x11          # los dos
    and  x9, x9, x8            # comprar = bajo | (los dos & p <= 160)
    or   x9, x9, x6
    and  x12, x12, x8          # vender = alto | (los dos & p >= 195)
    or   x12, x12, x7
    or   x13, x9, x12          # cambia (comprar y vender nunca son 1 a la vez)
    sub  x13, x0, x13          # 0 o 0xFFFFFFFF
    sub  x14, x0, x12          # 0xFFFFFFFF si vende
    andi x14, x14, VENDER_MENOS_COMPRAR
    addi x14, x14, COMPRAR_63  # 0x7F (comprar 63) o 0xBF (vender 63)
    xor  x15, x14, x4          # q = cambia ? byte nuevo : q
    and  x15, x15, x13
    xor  x4, x4, x15
    or   x15, x6, x7           # el primer precio, si no es un extremo: comprar 20 una vez
    xori x15, x15, 1
    and  x15, x15, x3
    sub  x15, x0, x15          # 0 o 0xFFFFFFFF
    addi x1, x0, COMPRAR_K
    xor  x1, x1, x4            # byte = primero ? comprar 20 : q
    and  x1, x1, x15
    xor  x1, x1, x4
    li   x3, 0
    sw   x1, OFF_DECISION(x2)
    j    esperar

# Relleno con ceros hasta las 512 palabras de la RAM
.org 0x800
