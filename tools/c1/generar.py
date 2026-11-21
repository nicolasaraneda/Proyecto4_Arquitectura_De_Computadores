#!/usr/bin/env python3
"""generar.py: genera el programa de R3 (sw/c1.s) y su tabla (sw/c1_tabla.hex) desde el modelo.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Las celdas de la tabla salen de ref/c1/tablas.py (el modelo del paseo normalizado, sin precios
guardados). El assembly de los cuatro hilos sale de la plantilla de este archivo, con las
constantes del modelo y de la contabilidad puestas como .equ y como palabras de datos. La
referencia exacta es ref/c1/c1.py y el diseño está en docs/c1_plan.md.

Uso, desde la raíz:
  python3 tools/c1/generar.py                  escribe sw/c1.s y sw/c1_tabla.hex
  python3 tools/c1/generar.py --check          comprueba que los dos archivos del repositorio son los generados
  python3 tools/c1/generar.py --apagada -o DIR la misma pareja con la política apagada (banda 40 exacta)
Opciones: --plazo N, --caja N, --comision N, --m N, --n-ronda N (parámetros del programa y de la tabla).
"""
import argparse
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "ref", "c1"))
import tablas as TB  # noqa: E402

PLANTILLA = r"""# =============================================================================
# c1.s: programa de R3. C1 en los cuatro hilos del Espino barrel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# GENERADO por tools/c1/generar.py. No editar a mano: cambiar la plantilla o
# los parámetros y generar de nuevo (make c1-generar).
#
# C1 (docs/c1_plan.md): la banda 40 de R2 más un desempate.
#   fase A   antes de ver 100 o 255: media posición solo si la tabla da
#            probabilidad >= 0,95 de que el 255 llegue antes que el 100
#   motor    desde el primer extremo: política óptima V2 comprimida, hasta
#            ganarle M al clon de la banda 40
#   candado  con D >= M (patrimonio propio menos el del clon) copia al clon
#            hasta el final de la ronda
#
# Hardware: el de R2 (barrel con emad y devk, vigilante) con la tabla de 512
# palabras (-DESPINO_TABLA_512). No usa la extensión, ni desplazamientos, ni
# multiplicación: sumas, restas, comparaciones, and/or/xor y lecturas.
# Referencia byte a byte: ref/c1/c1.py.
#
#   hilo 0  corredor    lee el precio, calcula la banda 40 por su cuenta (la
#                       misma de sw/fondo.s), publica precio y fase, espera
#                       la política del tick con plazo y escribe DECISION
#   hilo 1  régimen     S2, clase de v^2 con histéresis, tramos del reloj
#   hilo 2  política    lee la celda de la tabla: fase A y motor
#   hilo 3  emulador    cuenta propia, cuenta del clon, D, máquina de modos
#                       y byte de la política
#
# Memoria compartida: cada palabra tiene un solo hilo que la escribe. Lo que
# se publica lleva el número de tick en los bits 31:8.
#   D_PUB   hilo 0   tick y precio            D_REG   hilo 1   tick y tabla activa
#   D_FOFF  hilo 0   desplazamiento de fase   D_REGA  hilo 1   celda de la fase A
#   D_FASE  hilo 0   tick y byte banda 40     D_REGM  hilo 1   celda del motor
#   D_ORD   hilo 0   tick y byte escrito      D_TAB   hilo 2   tick y posiciones
#                                             D_POL   hilo 3   tick y byte de la política
#
# Degradación (como en R2): el hilo 0 decide siempre. Usa la política solo si
# trae el tick actual; vencido el plazo, si es del tick anterior sostiene una
# orden completa (o mantiene), y si es más vieja pasa a modo seguro: banda 40
# sin política, para siempre. También pasa a modo seguro con un precio menor
# que P_MIN o pasado el tick N_RONDA. Con la palabra POLITICA de la tabla en 0
# parte en modo seguro: la banda 40 exacta de R2.
# =============================================================================

.equ SPI_BASE,      0x80010000
.equ OFF_STATUS,    0
.equ OFF_PRICE,     4
.equ OFF_DECISION,  8
.equ PER_BASE,      0x80000000
.equ PER_DIGITOS,   0
.equ PER_LEDS,      4
.equ PER_BOTONES,   8
.equ TAB_BASE,      0x80020000
# Tabla de 512 palabras de 16 bits: la palabra i está en 4 i
.equ T_LO_MAS_1,    @T_LO_MAS_1@
.equ T_HI,          @T_HI@
.equ T_BANDA_COMPRA, @T_BANDA_COMPRA@
.equ T_BANDA_VENTA, @T_BANDA_VENTA@
.equ T_POLITICA,    @T_POLITICA@
.equ T_CUAD64,      @T_CUAD64@
.equ T_N64,         @T_N64@
.equ T_FASE_A,      @T_FASE_A@
.equ T_MOTOR,       @T_MOTOR@
.equ COMPRAR_63,    0x7F
.equ VENDER_63,     0xBF
.equ VENDER_MENOS_COMPRAR, 0x40
.equ HISTERESIS,    @HISTERESIS@
.equ D_MAX,         @D_MAX@
.equ LARGO_A,       @LARGO_A@
.equ LARGO_M,       @LARGO_M@
.equ OBJ_MAX,       511

# --- Tabla de arranque: el hilo t parte en la dirección 4 t -------------------
    j    hilo0
    j    hilo1
    j    hilo2
    j    hilo3

# =============================================================================
# Hilo 0: corredor
#   x1 tabla   x2 SPI   x3 tick << 8   x4 q (byte de la banda 40)   x5 p
#   x6 byte que se escribe   x9 modo seguro   x10 se vio el mínimo
#   x11 se vio el máximo   x12 ticks que quedan de la ronda   x7 x8 x13 x14 x15 temporales
# =============================================================================
hilo0:
    li   x1, TAB_BASE
    li   x2, SPI_BASE
    li   x3, 0
    li   x4, 0
    li   x10, 0
    li   x11, 0
    lw   x12, D_N_RONDA(x0)
    lw   x9, T_POLITICA(x1)
    sltiu x9, x9, 1            # política apagada: parte en modo seguro
h0_espera:
    lw   x15, OFF_STATUS(x2)
    andi x15, x15, 1
    beqz x15, h0_espera
    lw   x5, OFF_PRICE(x2)
#@HILO0
    addi x3, x3, 256
    or   x15, x3, x5
    sw   x15, D_PUB(x0)        # publica tick y precio
# banda 40, igual que sw/fondo.s
    lw   x13, T_LO_MAS_1(x1)
    sltu x6, x5, x13           # bajo = p <= 100
    lw   x13, T_HI(x1)
    sltu x7, x5, x13
    xori x7, x7, 1             # alto = p >= 255
    lw   x13, T_BANDA_COMPRA(x1)
    sltu x14, x5, x13          # p <= 140
    lw   x13, T_BANDA_VENTA(x1)
    sltu x15, x5, x13
    xori x15, x15, 1           # p >= 215
    or   x10, x10, x6          # se vio el mínimo
    or   x11, x11, x7          # se vio el máximo
    and  x8, x10, x11          # los dos
    and  x14, x14, x8
    or   x14, x14, x6          # comprar
    and  x15, x15, x8
    or   x15, x15, x7          # vender
    or   x13, x14, x15         # cambia
    sub  x13, x0, x13
    sub  x14, x0, x15
    andi x14, x14, VENDER_MENOS_COMPRAR
    addi x14, x14, COMPRAR_63
    xor  x15, x14, x4
    and  x15, x15, x13
    xor  x4, x4, x15           # q
# publica la fase: desplazamiento de la celda del motor (B 0, C 256, D 512) y q
    sub  x13, x0, x11
    andi x13, x13, 256
    sub  x14, x0, x8
    andi x14, x14, 256
    add  x13, x13, x14
    sw   x13, D_FOFF(x0)
    or   x13, x3, x4
    sw   x13, D_FASE(x0)
# modo seguro: precio bajo el mínimo válido o ronda más larga que la supuesta
    lw   x13, D_P_MIN(x0)
    sltu x13, x5, x13
    or   x9, x9, x13
    addi x12, x12, -1
    slti x13, x12, 0
    or   x9, x9, x13
    mv   x6, x4                # respaldo: la banda 40
    bnez x9, h0_escribe
# espera la política de este tick, con plazo
    lw   x7, D_PLAZO(x0)
h0_sondeo:
    lw   x13, D_POL(x0)
#@POL
    sub  x13, x13, x3          # el byte, si es de este tick
    sltiu x14, x13, 256
    bnez x14, h0_llego
    addi x7, x7, -1
    bnez x7, h0_sondeo
# plazo vencido
    addi x13, x13, 256         # el byte, si es del tick anterior
    sltiu x14, x13, 256
    beqz x14, h0_viejo
    andi x14, x13, 63          # del tick anterior: sostiene una orden completa
    addi x14, x14, -63
    li   x6, 0                 # una parcial no se repite: mantener
    bnez x14, h0_escribe
h0_llego:
    mv   x6, x13
    j    h0_escribe
h0_viejo:
    li   x9, 1                 # más vieja o nunca llegó: modo seguro
h0_escribe:
    sw   x6, OFF_DECISION(x2)
    or   x13, x3, x6
    sw   x13, D_ORD(x0)        # el byte escrito, para la cuenta propia
    li   x13, PER_BASE
    sw   x9, PER_LEDS(x13)     # telemetría: LED 0 es el modo seguro
    j    h0_espera

# Un hilo que se saltó un tick deja de publicar (el hilo 0 lo nota por el plazo)
muerto:
    j    muerto

# =============================================================================
# Hilo 1: régimen y reloj
#   x1 tabla   x2 último D_PUB   x3 precio anterior   x4 64 S2   x5 p
#   x6 tick << 8   x7 tabla activa   x8 clase cruda   x9 calcular antes de publicar
#   x12 clase   x13 cuenta de la histéresis   x10 x14 x15 temporales
# =============================================================================
hilo1:
    li   x1, TAB_BASE
    li   x2, 0
    li   x3, -1
    li   x4, 0
    li   x12, -1
    li   x13, 0
h1_espera:
    lw   x14, D_PUB(x0)
    beq  x14, x2, h1_espera
#@HILO1
    mv   x2, x14
    andi x5, x14, 255          # p
    sub  x6, x14, x5           # tick << 8
# la tabla se usa desde el tick T_MIN
    li   x7, 0
    li   x9, 0                 # x9: hay que calcular la clase antes de publicar
    lw   x14, D_CMIN(x0)
    beqz x14, h1_activa
    addi x14, x14, -1
    sw   x14, D_CMIN(x0)
    j    h1_publica
h1_activa:
    li   x7, 1
    slti x9, x12, 0            # primera vez: todavía no hay clase
    addi x14, x13, @MENOS_HIST_MENOS_1@
    bnez x14, h1_seguir
    li   x9, 1                 # la histéresis puede cambiar la clase en este tick
h1_seguir:
    bnez x9, h1_calcula
# publica la celda del tick. Casi siempre va antes del cálculo: la clase solo
# puede cambiar cuando la cuenta de la histéresis está por cumplirse
h1_publica:
    lw   x14, D_CVA(x0)
    lw   x15, D_TRA(x0)
    add  x14, x14, x15
    sw   x14, D_REGA(x0)
    lw   x14, D_CVM(x0)
    lw   x15, D_TRM(x0)
    add  x14, x14, x15
    sw   x14, D_REGM(x0)
    or   x14, x6, x7
    sw   x14, D_REG(x0)        # tick y tabla activa
    bnez x9, h1_reloj
h1_calcula:
    li   x8, 0
    mv   x14, x3
    mv   x3, x5                # el precio de este tick es el anterior del siguiente
    bltz x14, h1_primero       # primer tick: no hay diferencia
# S2: 64 d^2 con |d| topado en D_MAX
    sub  x14, x5, x14
    bge  x14, x0, h1_abs
    sub  x14, x0, x14
h1_abs:
    sltiu x15, x14, @D_MAX_MAS_1@
    bnez x15, h1_tope
    li   x14, D_MAX
h1_tope:
    add  x14, x14, x14
    add  x14, x14, x14
    add  x14, x14, x1
    lw   x14, T_CUAD64(x14)
    add  x4, x4, x14
# sumas N_j (t - 1) y clase cruda: cuántas cumplen 64 S2 >= N_j (t - 1)
    la   x10, D_B
    mv   x15, x1
h1_suma:
    lw   x14, 0(x10)
    lw   x5, T_N64(x15)
    add  x14, x14, x5
    sw   x14, 0(x10)
    bltu x4, x14, h1_menor
    addi x8, x8, 1
h1_menor:
    addi x15, x15, 4
    addi x10, x10, 4
    la   x14, D_CMIN            # fin de las siete sumas
    bne  x10, x14, h1_suma
h1_primero:
    beqz x7, h1_fin            # antes de T_MIN no hay clase
    bltz x12, h1_fija          # primera vez: la clase es la cruda
    beq  x8, x12, h1_igual
    addi x13, x13, 1
    addi x14, x13, @MENOS_HISTERESIS@
    bltz x14, h1_fin
h1_fija:
    mv   x12, x8
    add  x14, x8, x8
    add  x14, x14, x14
    add  x14, x14, x14
    add  x14, x14, x14
    add  x14, x14, x14
    sw   x14, D_CVM(x0)        # 32 clase: fila del motor
    add  x14, x14, x14
    sw   x14, D_CVA(x0)        # 64 clase: fila de la fase A
h1_igual:
    li   x13, 0
h1_fin:
    bnez x9, h1_publica        # camino lento: publica después de calcular
# reloj: tramos del tick siguiente
h1_reloj:
    lw   x14, D_CA(x0)
    addi x14, x14, -1
    bnez x14, h1_ca
    lw   x15, D_TRA(x0)
    beqz x15, h1_ta
    addi x15, x15, -4
    sw   x15, D_TRA(x0)
h1_ta:
    li   x14, LARGO_A
h1_ca:
    sw   x14, D_CA(x0)
    lw   x14, D_CM(x0)
    addi x14, x14, -1
    bnez x14, h1_cm
    lw   x15, D_TRM(x0)
    beqz x15, h1_tm
    addi x15, x15, -4
    sw   x15, D_TRM(x0)
h1_tm:
    li   x14, LARGO_M
h1_cm:
    sw   x14, D_CM(x0)
    j    h1_espera

# =============================================================================
# Hilo 2: política (tablas)
#   x1 tabla   x2 último D_PUB   x3 posición de la fase A   x4 posición del motor
#   x13 tick << 8   x15 p   x14 tabla activa   x12 q == comprar
#   x10 q   x11 desplazamiento de fase   x8 x9 temporales
# =============================================================================
hilo2:
    li   x1, TAB_BASE
    li   x2, 0
    li   x3, 0
    li   x4, 0
h2_espera:
    lw   x14, D_PUB(x0)
    beq  x14, x2, h2_espera
#@HILO2
    mv   x2, x14
    andi x15, x14, 255         # p
    sub  x13, x14, x15         # tick << 8
h2_reg:
    lw   x14, D_REG(x0)
    sub  x14, x14, x13         # 0 o 1 (tabla activa) si es de este tick
    sltiu x12, x14, 2
    beqz x12, h2_reg
h2_fase:
    lw   x10, D_FASE(x0)
    sub  x10, x10, x13         # q, si es de este tick
    sltiu x12, x10, 256
    beqz x12, h2_fase
    lw   x11, D_FOFF(x0)
    xori x12, x10, COMPRAR_63
    sltiu x12, x12, 1          # q == comprar 63
    li   x9, 0
    beqz x14, h2_fijo          # antes de T_MIN no hay tabla
    beqz x10, h2_a             # q == mantener: todavía es la fase A
# motor: celda F * 64 + clase * 8 + tramo; byte bajo con posición 0, alto con posición 1
    lw   x8, D_REGM(x0)
    add  x8, x8, x11
    add  x8, x8, x1
    add  x8, x8, x4
    lbu  x8, T_MOTOR(x8)
    sltu x4, x8, x15
    xori x4, x4, 1             # invertido si p <= nivel
    li   x9, 8
    j    h2_publica
h2_a:
# fase A: celda clase * 16 + tramo; byte bajo entrada, alto salida
    lw   x8, D_REGA(x0)
    add  x8, x8, x1
    add  x8, x8, x3
    lbu  x8, T_FASE_A(x8)
    sltu x8, x15, x8
    xori x8, x8, 1             # media posición si p >= nivel
    xori x9, x3, 1
    and  x9, x9, x8            # entra: estaba en 0 y pasa a 1
    add  x9, x9, x9
    add  x9, x9, x8
    addi x9, x9, 8             # bit 3: tabla activa
    mv   x3, x8
h2_fijo:
    mv   x4, x12               # sin tabla del motor: su posición es la de la banda 40
h2_publica:
    add  x8, x4, x4
    add  x8, x8, x8
    or   x9, x9, x8            # bit 2: posición del motor
    or   x9, x9, x13
    sw   x9, D_TAB(x0)         # publica: tick, activa, motor, entra, fase A
    j    h2_espera

# =============================================================================
# Hilo 3: emulador del clon, cuenta propia y máquina de modos
#   x1 p   x2 2p   x3 4p   x4 8p   x5 16p   x6 32p
#   x14 último D_PUB   x15 tick << 8
#   x7 x8 x9 x10 x11 x12 x13 de trabajo (ver cada rutina)
# =============================================================================
hilo3:
    li   x14, 0
    li   x15, 0
h3_espera:
    lw   x13, D_PUB(x0)
    beq  x13, x14, h3_espera
#@HILO3
    mv   x14, x13
    andi x1, x13, 255          # p
    sub  x13, x13, x1
    addi x15, x15, 256
    bne  x13, x15, muerto
    add  x2, x1, x1
    add  x3, x2, x2
    add  x4, x3, x3
    add  x5, x4, x4
    add  x6, x5, x5
# cuenta propia: ejecuta al precio nuevo el byte que el hilo 0 escribió
    lbu  x10, D_ORD(x0)
    beqz x10, h3_clon
    la   x11, D_CAJA
    jal  x12, ejecutar
h3_clon:
# cuenta del clon: ejecuta su byte pendiente (la banda 40 del tick anterior)
    lw   x10, D_QC(x0)
    la   x11, D_CAJAC
    jal  x12, ejecutar
# D = caja - caja del clon + (acc - acc del clon) p
    lw   x7, D_ACC(x0)
    lw   x9, D_ACCC(x0)
    sub  x7, x7, x9
    li   x8, 0
    beqz x7, h3_sin_p          # mismas acciones: no hay producto que hacer
    jal  x12, producto
h3_sin_p:
    lw   x7, D_CAJA(x0)
    add  x7, x7, x8            # en la fase A el clon no tiene acciones: es el patrimonio propio
    lw   x9, D_CAJAC(x0)
    sub  x13, x7, x9           # D
    sw   x13, D_DIF(x0)
h3_fase:
    lw   x10, D_FASE(x0)
    sub  x10, x10, x15         # q, si es de este tick
    sltiu x9, x10, 256
    beqz x9, h3_fase
# máquina de modos: 0 fase A, 1 recuperación, 2 candado
    lw   x11, D_MODO(x0)
    bnez x11, h3_no_a
    beqz x10, h3_fase_a        # q == mantener: sigue la fase A
    li   x11, 1                # primer extremo: recuperación
h3_no_a:
    addi x9, x11, -2
    beqz x9, h3_copia
    lw   x9, D_M(x0)
    blt  x13, x9, h3_tab       # D < M: sigue en recuperación
    li   x11, 2                # candado
h3_copia:
    mv   x8, x10               # copia al clon
    j    h3_publica
h3_fase_a:
# Fase A sin media posición: adelanta el objetivo de una entrada, por si la
# tabla la pide en este tick. Objetivo = min(511, W / (2 p)), con W en x7.
# Se calcula antes de esperar al hilo 2 para que no alargue la respuesta.
    lw   x9, D_SA(x0)
    bnez x9, h3_tab            # con media posición no puede haber entrada
    add  x12, x6, x6
    add  x12, x12, x12
    add  x12, x12, x12
    add  x12, x12, x12         # 512 p
    li   x13, OBJ_MAX
    add  x9, x12, x12
    bgeu x7, x9, h3_tab        # W >= 1024 p: el tope
    li   x13, 1                # centinela: después de 9 pasos llega a 512
    li   x9, 512
h3_div:
    add  x13, x13, x13
    bltu x7, x12, h3_div1
    sub  x7, x7, x12
    addi x13, x13, 1
h3_div1:
    add  x7, x7, x7
    bltu x13, x9, h3_div
    addi x13, x13, -512
h3_tab:
    lw   x9, D_TAB(x0)
    sub  x9, x9, x15           # bits de la política, si es de este tick
    sltiu x12, x9, 16
    beqz x12, h3_tab
    beqz x11, h3_modo_a
# recuperación: el motor
    andi x9, x9, 4
    li   x8, VENDER_63
    beqz x9, h3_publica
    li   x8, COMPRAR_63
    j    h3_publica
h3_modo_a:
    andi x12, x9, 1
    sw   x12, D_SA(x0)         # posición de la fase A según la tabla
    li   x8, 0
    andi x7, x9, 8
    beqz x7, h3_publica        # antes de T_MIN: mantener
    li   x8, VENDER_63
    beqz x12, h3_publica       # la tabla dice caja: vender 63
    andi x12, x9, 2
    beqz x12, h3_hacia
    sw   x13, D_OBJ(x0)        # entra: fija el objetivo adelantado
h3_hacia:
    lw   x8, D_OBJ(x0)
    lw   x9, D_ACC(x0)
    sub  x9, x8, x9            # lo que falta para el objetivo
    li   x8, 0
    beqz x9, h3_publica
    li   x8, 0x40
    bge  x9, x0, h3_cant
    li   x8, 0x80
    sub  x9, x0, x9
h3_cant:
    addi x12, x9, -63
    bltz x12, h3_orden
    li   x9, 63
h3_orden:
    or   x8, x8, x9
h3_publica:
    or   x9, x15, x8
    sw   x9, D_POL(x0)         # publica: tick y byte de la política
    sw   x11, D_MODO(x0)
    sw   x10, D_QC(x0)         # el byte del clon para el tick siguiente
# fuera del camino de la respuesta: patrimonio propio emulado y telemetría
    lw   x7, D_ACC(x0)
    jal  x12, producto
    lw   x7, D_CAJA(x0)
    add  x8, x8, x7
    sw   x8, D_W(x0)
    sb   x11, @D_W_MODO@(x0)        # el byte alto de la palabra D_W lleva el modo
    li   x7, PER_BASE
    lw   x9, PER_BOTONES(x7)
    andi x9, x9, 15
    lbu  x9, D_W(x9)           # los botones eligen el byte: patrimonio y modo, caja, acciones, caja del clon
    sw   x9, PER_DIGITOS(x7)
    j    h3_espera

# -----------------------------------------------------------------------------
# ejecutar: la contabilidad oficial para un byte, con los múltiplos de p.
#   x10 byte   x11 puntero a la cuenta (caja en 0, acciones en 4)   vuelve por x12
#   compra  q = min(cantidad, (caja - comisión) / p)   caja -= q p + comisión
#   venta   q = min(cantidad, acciones)                caja += q p - comisión
# La parte voraz resta de x7 los múltiplos 32p ... p mientras quede cantidad y
# alcance. En la venta x7 es ~caja, que sin signo siempre alcanza: restar de
# ~caja es sumar a caja.
#   x7 saldo   x8 cantidad que falta   x9 temporal   x13 cantidad pedida
# -----------------------------------------------------------------------------
ejecutar:
    andi x8, x10, 63
    andi x9, x10, 0x40
    bnez x9, ej_compra
    andi x9, x10, 0x80
    beqz x9, ej_fin            # mantener
    lw   x9, 4(x11)
    bgeu x9, x8, ej_venta
    mv   x8, x9                # no se venden más acciones que las que hay
ej_venta:
    lw   x7, 0(x11)
    xori x7, x7, -1
    j    ej_voraz
ej_compra:
    lw   x7, 0(x11)
    lw   x9, D_COM(x0)
    sub  x7, x7, x9
    bltz x7, ej_fin            # no alcanza ni para la comisión
ej_voraz:
    mv   x13, x8
@VORAZ@
    sub  x13, x13, x8          # cantidad ejecutada
    beqz x13, ej_fin           # una orden que queda en cero no se ejecuta ni paga
    lw   x9, 4(x11)
    andi x10, x10, 0x40
    beqz x10, ej_vende
    add  x9, x9, x13
    sw   x9, 4(x11)
    sw   x7, 0(x11)
    jr   x12
ej_vende:
    sub  x9, x9, x13
    sw   x9, 4(x11)
    xori x7, x7, -1
    lw   x9, D_COM(x0)
    sub  x7, x7, x9
    sw   x7, 0(x11)
ej_fin:
    jr   x12

# -----------------------------------------------------------------------------
# producto: x8 = x7 * p con los 8 bits de p (x1), por duplicaciones y sumas.
# Exacto para cualquier x7, también negativo. Usa x9. Vuelve por x12.
# -----------------------------------------------------------------------------
producto:
@PRODUCTO@
    jr   x12

# =============================================================================
# Datos. Cada palabra tiene un solo hilo que la escribe.
# =============================================================================
.org @DATOS@
# hilo 0
D_PUB:      .word 0
D_FOFF:     .word 0
D_FASE:     .word 0
D_ORD:      .word 0
D_N_RONDA:  .word @N_RONDA@          # ticks de la ronda que supone el modelo
D_P_MIN:    .word @P_MIN@            # precio mínimo válido
D_PLAZO:    .word @PLAZO@            # vueltas del lazo de espera
# hilo 1
D_REG:      .word 0
D_REGA:     .word 0
D_REGM:     .word 0
D_B:        .word 0, 0, 0, 0, 0, 0, 0   # N_j (t - 1)
D_CMIN:     .word @T_MIN_MENOS_1@
D_CVA:      .word 0
D_CVM:      .word 0
D_TRA:      .word @TRA_INI@          # 4 * tramo de la fase A
D_CA:       .word @LARGO_A@
D_TRM:      .word @TRM_INI@          # 4 * tramo del motor
D_CM:       .word @LARGO_M@
# hilo 2
D_TAB:      .word 0
# hilo 3
D_POL:      .word 0xFFFFFE00         # ningún tick: ni el actual ni el anterior
# Las cuatro palabras que siguen son lo que la telemetría puede mostrar, un byte por vez:
# el botón elegido (0 a 15) es el desplazamiento desde D_W
D_W:        .word @CAJA0@            # patrimonio propio emulado (byte alto: modo)
D_CAJA:     .word @CAJA0@            # cuenta propia: caja y acciones
D_ACC:      .word 0
D_CAJAC:    .word @CAJA0@            # cuenta del clon
D_ACCC:     .word 0
D_COM:      .word @COMISION@
D_M:        .word @M@                # candado: D >= M
D_QC:       .word 0
D_MODO:     .word 0
D_OBJ:      .word 0
D_SA:       .word 0
D_DIF:      .word 0
.org 0x800
"""


def voraz():
    L = []
    for k, (w, reg) in enumerate(((32, "x6"), (16, "x5"), (8, "x4"), (4, "x3"), (2, "x2"), (1, "x1"))):
        L += [f"    addi x9, x8, -{w}",
              f"    bltz x9, ej_v{k}",
              f"    bltu x7, {reg}, ej_v{k}",
              f"    sub  x7, x7, {reg}",
              "    mv   x8, x9",
              f"ej_v{k}:"]
    return "\n".join(L)


def producto(desenrollado=True):
    if desenrollado:
        L = ["    li   x8, 0"]
        for k, bit in enumerate((128, 64, 32, 16, 8, 4, 2, 1)):
            if k:
                L.append("    add  x8, x8, x8")
            L += [f"    andi x9, x1, {bit}", f"    beqz x9, pr_{k}", "    add  x8, x8, x7", f"pr_{k}:"]
        return "\n".join(L)
    raise NotImplementedError


PAR_DEFECTO = dict(TB.PROGRAMA, politica=TB.POLITICA_C1)


def parametros_tabla(par):
    return {TB.T_POLITICA: par["politica"]}


def _datos():
    """(cantidad de palabras de datos, {etiqueta: índice}) de la sección de datos de la plantilla."""
    n, etiquetas = 0, {}
    for linea in PLANTILLA.split(".org @DATOS@")[1].splitlines():
        linea = linea.split("#")[0].strip()
        if ".word" in linea:
            if ":" in linea:
                etiquetas[linea.split(":")[0].strip()] = n
            n += len(linea.split(".word")[1].split(","))
    return n, etiquetas


def texto_asm(par):
    n_datos, etiquetas = _datos()
    datos = 0x800 - 4 * n_datos
    s = PLANTILLA
    rep = {
        "T_LO_MAS_1": 4 * TB.T_LO_MAS_1, "T_HI": 4 * TB.T_HI, "T_BANDA_COMPRA": 4 * TB.T_BANDA_COMPRA,
        "T_BANDA_VENTA": 4 * TB.T_BANDA_VENTA, "T_POLITICA": 4 * TB.T_POLITICA, "T_CUAD64": 4 * TB.T_CUAD64,
        "T_N64": 4 * TB.T_N64, "T_FASE_A": 4 * TB.T_FASE_A, "T_MOTOR": 4 * TB.T_MOTOR,
        "HISTERESIS": TB.HISTERESIS, "D_MAX": TB.D_MAX, "LARGO_A": TB.LARGO_A, "LARGO_M": TB.LARGO_M,
        "D_MAX_MAS_1": TB.D_MAX + 1, "MENOS_HISTERESIS": -TB.HISTERESIS, "MENOS_HIST_MENOS_1": -(TB.HISTERESIS - 1), "D_W_MODO": datos + 4 * etiquetas["D_W"] + 3,
        "VORAZ": voraz(), "PRODUCTO": producto(), "DATOS": hex(datos),
        "N_RONDA": par["n_ronda"], "P_MIN": par["p_min"], "PLAZO": par["plazo"], "T_MIN_MENOS_1": TB.T_MIN - 1,
        "TRA_INI": 4 * (TB.TRAMOS_A - 1), "TRM_INI": 4 * (TB.TRAMOS_M - 1), "CAJA0": par["caja"],
        "COMISION": par["comision"], "M": par["m"],
    }
    for k, v in rep.items():
        s = s.replace(f"@{k}@", str(v))
    if "@" in s.replace("#@", ""):
        raise SystemExit("quedó una marca sin reemplazar en la plantilla")
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-o", "--salida", default=os.path.join(RAIZ, "sw"))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apagada", action="store_true")
    ap.add_argument("--solo-asm", action="store_true",
                    help="con --check: revisa solo sw/c1.s, sin calcular el modelo (para la integración continua)")
    for nombre in ("plazo", "caja", "comision", "m", "n_ronda", "p_min"):
        ap.add_argument("--" + nombre.replace("_", "-"), type=int)
    a = ap.parse_args()
    par = dict(PAR_DEFECTO)
    for nombre in ("plazo", "caja", "comision", "m", "n_ronda", "p_min"):
        if getattr(a, nombre) is not None:
            par[nombre] = getattr(a, nombre)
    if a.apagada:
        par["politica"] = TB.POLITICA_APAGADA
    asm = texto_asm(par)
    if a.check and a.solo_asm:
        r_asm = os.path.join(a.salida, "c1.s")
        if not os.path.exists(r_asm) or open(r_asm).read() != asm:
            raise SystemExit(f"FAIL: {r_asm} no coincide con lo generado")
        print(f"PASS: {r_asm} es el que genera tools/c1/generar.py (la tabla no se revisa: make c1-generar)")
        return
    en_sw = os.path.abspath(a.salida) == os.path.join(RAIZ, "sw")
    try:
        T = TB.palabras(parametros_tabla(par))
    except SystemExit:
        # Sin el modelo calculado (una copia limpia del repositorio): las variantes de prueba (-o a otra
        # carpeta) toman las celdas de sw/c1_tabla.hex, que make c1-generar comprueba contra el modelo,
        # y solo cambian las palabras de parámetros. sw/c1_tabla.hex mismo sale siempre del modelo.
        if en_sw or a.check:
            raise
        T = TB.leer_hex(os.path.join(RAIZ, "sw", "c1_tabla.hex"))
        for i, v in parametros_tabla(par).items():
            T[i] = v & 0xFFFF
    hexa = "".join(f"{v:04x}\n" for v in T)
    r_asm, r_hex = os.path.join(a.salida, "c1.s"), os.path.join(a.salida, "c1_tabla.hex")
    if a.check:
        mal = [r for r, t in ((r_asm, asm), (r_hex, hexa)) if not os.path.exists(r) or open(r).read() != t]
        if mal:
            raise SystemExit("FAIL: no coinciden con lo generado: " + ", ".join(mal))
        print(f"PASS: {r_asm} y {r_hex} son los que genera tools/c1/generar.py")
        return
    os.makedirs(a.salida, exist_ok=True)
    with open(r_asm, "w") as f:
        f.write(asm)
    with open(r_hex, "w") as f:
        f.write(hexa)
    print(f"{r_asm} y {r_hex} generados")


if __name__ == "__main__":
    main()
