# cuelgue.s: programa de prueba que deja de responder.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Sirve para probar el vigilante. Responde con el byte DEC a los primeros K
# precios y después se queda en un lazo sin leer precios ni escribir DECISION,
# como haría un programa o un core que se colgó.
#
# Para que se vea en la placa cuál imagen está corriendo, enciende el LED 1 y
# muestra en los displays, en hexadecimal, el byte bajo de la cantidad de
# precios que le faltan por responder. La imagen de respaldo (el bitstream de
# competencia) deja los LED apagados y los displays en 00.
#
# K y DEC se cambian al ensamblar:
#   python3 tools/pochoasm.py factibilidad/e_warmboot/sw/cuelgue.s -D K=20 -D DEC=0x7F -o SALIDA.hex

.equ PER_BASE,      0x80000000
.equ OFF_DIGITOS,   0          # displays de 7 segmentos (dos dígitos hexadecimales)
.equ OFF_LEDS,      4
.equ SPI_BASE,      0x80010000
.equ OFF_STATUS,    0
.equ OFF_PRICE,     4
.equ OFF_DECISION,  8
.equ K,             20
.equ DEC,           0x7F       # comprar 63

_start:
    li   x2, SPI_BASE
    li   x3, PER_BASE
    li   x10, K
    li   x8, DEC
    li   x7, 1
    sw   x7, OFF_LEDS(x3)      # LED 1 encendido: corre la imagen principal
    sw   x10, OFF_DIGITOS(x3)
esperar:
    lw   x7, OFF_STATUS(x2)
    andi x7, x7, 1
    beqz x7, esperar
    lw   x5, OFF_PRICE(x2)
    sw   x8, OFF_DECISION(x2)
    addi x10, x10, -1
    sw   x10, OFF_DIGITOS(x3)
    bnez x10, esperar
colgado:
    j    colgado

# Relleno con ceros hasta las 512 palabras de la RAM
.org 0x800
