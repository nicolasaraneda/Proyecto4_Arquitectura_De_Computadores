# tabla_prueba.s: prueba de la memoria para la tabla de política con los
# cuatro hilos del barrel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Cada hilo es dueño de un cuarto de la tabla (Q entradas seguidas) y hace con
# él lo que haría un programa que aprende: lo inicializa, lo recorre leyendo y
# ajustando cada entrada con una suma, y publica una suma de comprobación. El
# hilo 0, que hace de supervisor, espera a los otros tres, junta las cuatro
# sumas y las muestra. Los cuatro ejecutan el mismo código (es reentrante):
# cada uno entra con sus constantes en sus propios registros.
#
#   1. Escribe la entrada i de su cuarto con v, y v avanza PASO en cada una.
#   2. Recorre su cuarto: lee la entrada, la acumula en S, le suma c (1, 2,
#      3, ...) y la vuelve a escribir.
#   3. Prueba de accesos por byte en su primera entrada: sb en el byte 1, lhu
#      de la entrada y lb del byte 1. Los dos valores leídos se acumulan en S.
#   4. Publica S en RES + 4 t y un 1 en RES + 16 + 4 t. Cada palabra
#      compartida tiene un solo hilo que la escribe.
#   5. El hilo 0 espera las tres banderas, suma las cuatro S, deja la suma en
#      RES + 32, muestra su byte bajo en el display y enciende los 4 LEDs.
#
# El testbench (tb/tb_tabla.sv) calcula lo mismo por su cuenta y compara la
# tabla entera, las sumas, el display y que nada fuera de la tabla y de la
# zona RES haya cambiado.
#
# Constantes que se fijan al ensamblar, según la forma de la memoria:
#   forma 1, BRAM de 256 x 16 por MMIO:   -D TAB_BASE=0x80020000 -D Q=64  -D QBYTES=256
#   forma 2, otras 512 palabras de datos: -D TAB_BASE=0x800      -D Q=128 -D QBYTES=512
# En las dos una entrada ocupa 4 bytes de direcciones.

.equ TAB_BASE,  0x80020000
.equ Q,         64            # entradas por hilo
.equ QBYTES,    256           # 4 Q
.equ PASO,      0x01230457
.equ RES,       0x700         # zona de resultados, en la memoria de datos
.equ PER_BASE,  0x80000000

# Tabla de arranque del barrel: el hilo t parte en la dirección 4 t
    j    hilo0
    j    hilo1
    j    hilo2
    j    hilo3

# Registros de entrada al código común:
#   x1   primera entrada del cuarto del hilo
#   x3   valor inicial v
#   x13  byte de la prueba por byte
#   x14  RES + 4 t
#   x15  número del hilo
hilo0:
    li   x1, TAB_BASE
    li   x3, 0x1037
    li   x13, 0xA0
    li   x14, RES
    li   x15, 0
    j    comun
hilo1:
    li   x1, TAB_BASE
    li   x9, QBYTES
    add  x1, x1, x9
    li   x3, 0x2037
    li   x13, 0xA1
    li   x14, RES
    addi x14, x14, 4
    li   x15, 1
    j    comun
hilo2:
    li   x1, TAB_BASE
    li   x9, QBYTES
    add  x1, x1, x9
    add  x1, x1, x9
    li   x3, 0x3037
    li   x13, 0xA2
    li   x14, RES
    addi x14, x14, 8
    li   x15, 2
    j    comun
hilo3:
    li   x1, TAB_BASE
    li   x9, QBYTES
    add  x1, x1, x9
    add  x1, x1, x9
    add  x1, x1, x9
    li   x3, 0x4037
    li   x13, 0xA3
    li   x14, RES
    addi x14, x14, 12
    li   x15, 3

comun:
    # 1. Inicializa su cuarto
    li   x4, PASO
    li   x2, Q
    mv   x5, x1
escribe:
    sw   x3, 0(x5)
    add  x3, x3, x4
    addi x5, x5, 4
    addi x2, x2, -1
    bnez x2, escribe

    # 2. Lee, acumula, ajusta y vuelve a escribir
    li   x2, Q
    mv   x5, x1
    li   x6, 0                 # S
    li   x7, 0                 # c
ajusta:
    lw   x8, 0(x5)
    add  x6, x6, x8
    addi x7, x7, 1
    add  x8, x8, x7
    sw   x8, 0(x5)
    addi x5, x5, 4
    addi x2, x2, -1
    bnez x2, ajusta

    # 3. Accesos por byte en la primera entrada
    sb   x13, 1(x1)
    lhu  x9, 0(x1)
    add  x6, x6, x9
    lb   x9, 1(x1)
    add  x6, x6, x9

    # 4. Publica la suma y la bandera
    sw   x6, 0(x14)
    li   x9, 1
    sw   x9, 16(x14)
    beqz x15, supervisor
fin:
    j    fin

    # 5. Solo el hilo 0: espera a los otros tres y junta las sumas
supervisor:
    lw   x9, 20(x14)
    beqz x9, supervisor
espera2:
    lw   x9, 24(x14)
    beqz x9, espera2
espera3:
    lw   x9, 28(x14)
    beqz x9, espera3
    lw   x9, 4(x14)
    add  x6, x6, x9
    lw   x9, 8(x14)
    add  x6, x6, x9
    lw   x9, 12(x14)
    add  x6, x6, x9
    sw   x6, 32(x14)
    li   x11, PER_BASE
    sw   x6, 0(x11)            # display: byte bajo de la suma
    li   x9, 15
    sw   x9, 4(x11)            # los cuatro LEDs
listo:
    j    listo

# Relleno con ceros hasta las 512 palabras de la memoria
.org 0x800
