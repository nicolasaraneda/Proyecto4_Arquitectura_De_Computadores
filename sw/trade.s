# trade.s: programa de inversion para el Pochoco SoC (Espino Core, RV32E).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Version trivial (tramo 1): sirve para validar el flujo completo con el
# testbench oficial. La estrategia es "comprar y mantener": en cada tick deja
# en DECISION la orden "comprar 63". La maestra recorta la compra a lo que
# alcanza con la caja, asi que repetir la orden no tiene costo: cuando la caja
# ya no alcanza para una accion mas, la orden queda en cero y no paga comision.
#
# Ciclo principal:
#   1. Esperar a que STATUS[0] (precio nuevo) valga 1.
#   2. Leer PRICE. La lectura baja la bandera de precio nuevo.
#   3. Escribir DECISION una sola vez, con la decision definitiva.
#
# Registros:
#   x2  base del esclavo SPI (0x8001_0000)
#   x3  byte de decision
#   x4  temporal (STATUS)
#   x5  ultimo precio leido (todavia no se usa)

.equ SPI_BASE,     0x80010000
.equ OFF_STATUS,   0          # bit 0: precio nuevo, bit 1: CS activo
.equ OFF_PRICE,    4          # precio recibido (1 a 255)
.equ OFF_DECISION, 8          # byte que la maestra lee en la proxima transaccion

.equ COMPRAR_63,   0x7F       # accion 01 (comprar), cantidad 63

_start:
    li   x2, SPI_BASE
    li   x3, COMPRAR_63

esperar:
    lw   x4, OFF_STATUS(x2)
    andi x4, x4, 1
    beqz x4, esperar

    lw   x5, OFF_PRICE(x2)
    sw   x3, OFF_DECISION(x2)
    j    esperar
