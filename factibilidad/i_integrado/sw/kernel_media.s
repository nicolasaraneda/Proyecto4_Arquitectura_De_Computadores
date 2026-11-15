# kernel_media.s: tres hilos de estrategia que usan mulstep, emad y devk sin
# parar, para correr junto a la regla base en el hilo 0.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# No es una estrategia: es carga de trabajo para la prueba mixta
# (tools/mixto.sh). El hilo 0 corre sw/trade.s, que se copia a continuación de
# este archivo sin cambios, y atiende a la maestra con instrucciones de RV32E
# (loads, stores, saltos y accesos al SPI). Los hilos 1, 2 y 3 ejecutan en un
# lazo las tres instrucciones nuevas del subconjunto recomendado, cada uno con
# sus valores, y publican en la memoria una suma S y el número de vuelta n:
#
#     x3 = mulstep(x1, x2)        (x1 << 1) + (x1[31] ? x2 : 0)
#     x4 = emad(x3, x1, 5)        x1 + (x3 >>> 5)
#     x1 = devk(x4, x3, 5)        (x4 << 5) - x3
#     S  = S + x1
#
# tools/modelo_kernel.py calcula la misma secuencia con el modelo ref/xd.py de
# factibilidad/d_isa, y tb/mon_mixto.sv compara cada pareja (S, n) que sale por
# el bus. Así se prueban las dos direcciones a la vez: que las instrucciones
# nuevas de tres hilos no alteran lo que hace el hilo de RV32E, y que el
# tráfico de ese hilo no altera el resultado de las instrucciones nuevas.
#
# Las instrucciones nuevas se pasan a .word con tools/xd_word.py --pre de
# d_isa. Los tres hilos comparten el código del lazo (es reentrante).

.equ KRES, 0x6C0               # S y n del hilo t en KRES + 8 (t - 1) y KRES + 8 (t - 1) + 4

# Tabla de arranque del barrel
    j    _start
    j    kernel1
    j    kernel2
    j    kernel3

kernel1:
    li   x1, 0x13579BDF
    li   x2, 0x2468ACE1
    li   x5, KRES
    j    kernel
kernel2:
    li   x1, 0x89ABCDEF
    li   x2, 0x0F1E2D3D
    li   x5, KRES
    addi x5, x5, 8
    j    kernel
kernel3:
    li   x1, 0x7FFFFFF1
    li   x2, 0xDEADBEEF
    li   x5, KRES
    addi x5, x5, 16
kernel:
    li   x6, 0                 # S
    li   x8, 0                 # n
vuelta:
    mulstep x3, x1, x2
    emad    x4, x3, x1, 5
    devk    x1, x4, x3, 5
    add     x6, x6, x1
    addi    x8, x8, 1
    sw      x6, 0(x5)
    sw      x8, 4(x5)
    j       vuelta

