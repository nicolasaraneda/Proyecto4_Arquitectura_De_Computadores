# =============================================================================
# hilo_mmio.s: arranque sin tabla, con el registro HILO.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Prueba de la alternativa de arranque que se midió y no se eligió
# (factibilidad/a_barrel/README.md). Solo corre en el SoC compilado con
# -DBARREL_MMIO_HILO -DBARREL_BOOT_PASO=0: los cuatro hilos parten en la
# dirección 0 y cada uno lee en el registro HILO (0x8000_000C) qué hilo es.
#
# Los cuatro ejecutan las mismas cinco instrucciones y recién entonces se
# separan, con un salto indirecto a una tabla. Con la tabla de arranque del
# prototipo esa separación la hace el reset y cuesta una instrucción.
#
# Cada hilo deja en RES + 4 t el valor 0x100 (t + 1) + t:
#   hilo 0: 0x100    hilo 1: 0x201    hilo 2: 0x302    hilo 3: 0x403
# El sumando 0x100 (t + 1) lo pone el código propio de cada hilo y el sumando
# t es lo que entregó el registro, así que el resultado comprueba las dos cosas.
# =============================================================================

.equ PERIPH_HI, 0x80000
.equ OFF_HILO,  12
.equ RES,       0x7C0
.equ TABLA,     20               # dirección de la tabla: después de 5 instrucciones

_start:
    lui  x2, PERIPH_HI
    lw   x5, OFF_HILO(x2)        # x5 = número de hilo
    add  x6, x5, x5
    add  x6, x6, x6              # x6 = 4 t
    jalr x0, TABLA(x6)           # salta a tabla + 4 t
tabla:
    j    hilo0
    j    hilo1
    j    hilo2
    j    hilo3

hilo0:
    addi x7, x5, 0x100
    j    guardar
hilo1:
    addi x7, x5, 0x200
    j    guardar
hilo2:
    addi x7, x5, 0x300
    j    guardar
hilo3:
    addi x7, x5, 0x400
guardar:
    sw   x7, RES(x6)             # código reentrante: cada hilo en su palabra
fin:
    j    fin

# Relleno con ceros hasta las 512 palabras de la RAM
.org 0x800
