# =============================================================================
# trade_xd.s: max_media escrita con la extensión de la ISA (devk y emad).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Programa de prueba de la extensión (docs/extension_isa.md). No es el programa
# de competencia: es sw/trade.s (docs/trade_s.md) con dos bloques reemplazados,
# para comprobar de punta a punta que el ensamblador y el hardware hacen lo que
# dice la especificación. Tiene que decidir igual que ref/trader.py en todos
# los ticks (make xd-equiv).
#
#   bloque de sw/trade.s                          aquí
#   32 p con cinco sumas y dev = 32 p - S (6)     devk x6, x5, x3, 5      (1)
#   S = S + p - ((S + 31) >> 5), con la memoria   emad x3, x6, x3, 5      (1)
#   como desplazador (8)
#
# Las dos formas de actualizar la media dan el mismo número:
#   S + ((32 p - S) >>> 5) = S + p + piso(-S / 32) = S + p - techo(S / 32)
#                          = S + p - ((S + 31) >> 5)
#
# Solo corre en el Espino barrel compilado con -DESPINO_XD_EMAD y
# -DESPINO_XD_DEVK (o -DESPINO_XD). Necesita la tabla de arranque delante
# (tools/barrel/tabla.py).
#
# Registros: x2 base del SPI, x3 S (la media por 32), x4 pos, x5 precio,
# x6 dev, x7 y x9 temporales, x8 byte de decisión.
# =============================================================================

.extension xd

.equ SPI_BASE,      0x80010000
.equ OFF_STATUS,    0          # bit 0: precio nuevo
.equ OFF_PRICE,     4
.equ OFF_DECISION,  8
.equ K,             5          # alfa = 1/32. El hardware solo tiene k = 5
.equ UMBRAL_COMPRA, -96        # entra si dev < -(3 * 32)
.equ UMBRAL_VENTA,  1          # sale si dev > 0
.equ VENDER_63,     0xBF
.equ COMPRAR_MENOS_VENDER, -64 # 0x7F - 0xBF

_start:
    li   x2, SPI_BASE
    li   x4, 0                 # pos = 0: afuera

# Primer precio: la media parte en ese precio
primero:
    lw   x7, OFF_STATUS(x2)
    andi x7, x7, 1
    beqz x7, primero
    lw   x5, OFF_PRICE(x2)
    devk x3, x5, x0, K         # S = 32 p (con rs2 = x0 es p << 5)
    j    decidir

esperar:
    lw   x7, OFF_STATUS(x2)
    andi x7, x7, 1
    beqz x7, esperar
    lw   x5, OFF_PRICE(x2)

decidir:
    devk x6, x5, x3, K         # dev = 32 p - S
    slti x7, x6, UMBRAL_COMPRA # 1 si hay que entrar
    slti x9, x6, UMBRAL_VENTA  # 0 si hay que salir
    or   x4, x4, x7            # pos = (pos | entrar) & no_salir
    and  x4, x4, x9
    sub  x7, x0, x4            # 0 si pos = 0, 0xFFFFFFFF si pos = 1
    andi x7, x7, COMPRAR_MENOS_VENDER
    addi x8, x7, VENDER_63     # 0xBF (vender 63) o 0x7F (comprar 63)
    sw   x8, OFF_DECISION(x2)

    emad x3, x6, x3, K         # S = S + (dev >>> 5)
    j    esperar

.org 0x800
