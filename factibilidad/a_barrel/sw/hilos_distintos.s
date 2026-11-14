# =============================================================================
# hilos_distintos.s: los cuatro hilos del Espino barrel haciendo cosas distintas.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Prueba de humo del prototipo (factibilidad/a_barrel/README.md). Cada hilo
# parte en su entrada de la tabla de arranque (dirección 4 t), hace un cálculo
# propio, deja sus resultados en su zona de memoria y termina en un lazo.
# Los hilos no comparten registros (cada uno tiene su contexto) ni datos: lo
# único común es el código de la subrutina "multiplicar", que usa el hilo 3.
#
#   hilo 0   suma 1 + 2 + ... + 100                          RES0+0 = 5050
#   hilo 1   Fibonacci, 30 pasos                             RES1+0 = 832040
#   hilo 2   stores y loads de byte, media palabra y         RES2+0 = 0x0000817E
#            palabra, con y sin signo                        RES2+4 = 0x80FF7F01
#   hilo 3   subrutina llamada con jal y con jalr,           RES3+0 = 5535
#            comparaciones, lui y auipc                      RES3+4 = 1001
#                                                            RES3+8 = 0x00000015
#                                                            RES3+12 = dirección de "marca"
# Cada hilo escribe además 1 en la última palabra de su zona (RESt+60) cuando
# termina.
#
# Como los hilos son independientes, cada uno debe hacer exactamente lo mismo
# que el Espino base ejecutando este programa desde la dirección 4 t. Eso es
# lo que compara tools/humo.sh con las trazas.
# =============================================================================

.equ RES0, 0x700
.equ RES1, 0x740
.equ RES2, 0x780
.equ RES3, 0x7C0
.equ LISTO, 60

# --- Tabla de arranque: el hilo t parte en la dirección 4 t ------------------
    j    hilo0
    j    hilo1
    j    hilo2
    j    hilo3

# --- Hilo 0: suma de 1 a 100 --------------------------------------------------
hilo0:
    li   x8, RES0
    addi x5, x0, 100
    addi x6, x0, 0
h0_lazo:
    add  x6, x6, x5
    addi x5, x5, -1
    bnez x5, h0_lazo
    sw   x6, 0(x8)               # 5050
    addi x7, x0, 1
    sw   x7, LISTO(x8)
h0_fin:
    j    h0_fin

# --- Hilo 1: Fibonacci ----------------------------------------------------------
hilo1:
    li   x8, RES1
    addi x5, x0, 0               # a = F(0)
    addi x6, x0, 1               # b = F(1)
    addi x7, x0, 30
h1_lazo:
    add  x9, x5, x6
    mv   x5, x6
    mv   x6, x9
    addi x7, x7, -1
    bnez x7, h1_lazo
    sw   x5, 0(x8)               # F(30) = 832040
    addi x7, x0, 1
    sw   x7, LISTO(x8)
h1_fin:
    j    h1_fin

# --- Hilo 2: accesos a memoria de todos los tamaños ---------------------------
hilo2:
    li   x8, RES2
    li   x5, 0x80FF7F01
    sw   x5, 16(x8)
    lb   x6, 16(x8)              # 0x00000001
    lb   x7, 17(x8)              # 0x0000007F
    lb   x9, 18(x8)              # 0xFFFFFFFF
    lb   x10, 19(x8)             # 0xFFFFFF80
    lbu  x11, 19(x8)             # 0x00000080
    lh   x12, 18(x8)             # 0xFFFF80FF
    lhu  x13, 18(x8)             # 0x000080FF
    lhu  x14, 16(x8)             # 0x00007F01
    add  x15, x6, x7
    add  x15, x15, x9
    add  x15, x15, x10
    add  x15, x15, x11
    add  x15, x15, x12
    add  x15, x15, x13
    add  x15, x15, x14
    sw   x15, 0(x8)              # 0x0000817E
    sw   x0, 20(x8)
    sb   x6, 20(x8)              # byte 0 = 0x01
    sb   x7, 21(x8)              # byte 1 = 0x7F
    sh   x13, 22(x8)             # bytes 2 y 3 = 0x80FF
    lw   x3, 20(x8)              # 0x80FF7F01, usado en la instrucción siguiente
    sw   x3, 4(x8)
    addi x7, x0, 1
    sw   x7, LISTO(x8)
h2_fin:
    j    h2_fin

# --- Hilo 3: subrutinas, comparaciones, lui y auipc ---------------------------
hilo3:
    li   x8, RES3
    addi x10, x0, 123
    addi x11, x0, 45
    jal  x1, multiplicar         # x12 = 123 * 45
    sw   x12, 0(x8)              # 5535
    la   x5, multiplicar
    addi x10, x0, 77
    addi x11, x0, 13
    jalr x1, 0(x5)               # x12 = 77 * 13
    sw   x12, 4(x8)              # 1001
    addi x5, x0, -1
    addi x6, x0, 1
    slt  x7, x5, x6              # 1: -1 < 1 con signo
    sltu x9, x5, x6              # 0: 0xFFFFFFFF no es menor que 1 sin signo
    slti x13, x5, 0              # 1
    sltiu x14, x6, 2             # 1
    add  x7, x7, x7              # 2
    add  x7, x7, x9              # 2
    add  x7, x7, x7              # 4
    add  x7, x7, x13             # 5
    add  x7, x7, x7              # 10
    add  x7, x7, x14             # 11
    xori x7, x7, 0x1E            # 0x15
    sw   x7, 8(x8)               # 0x00000015
marca:
    auipc x15, 0                 # dirección de "marca"
    sw   x15, 12(x8)
    addi x7, x0, 1
    sw   x7, LISTO(x8)
h3_fin:
    j    h3_fin

# x12 = x10 * x11 por sumas repetidas. Usa x11 como contador. Vuelve por x1.
multiplicar:
    addi x12, x0, 0
m_lazo:
    beqz x11, m_fin
    add  x12, x12, x10
    addi x11, x11, -1
    j    m_lazo
m_fin:
    jalr x0, 0(x1)

# Relleno con ceros hasta las 512 palabras de la RAM
.org 0x800
