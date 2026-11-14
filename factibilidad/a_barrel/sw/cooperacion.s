# =============================================================================
# cooperacion.s: tres hilos calculan y un hilo supervisor junta los resultados.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Prueba de humo del prototipo (factibilidad/a_barrel/README.md). Es la forma
# mínima del esquema "un gestor por hilo": los hilos 1, 2 y 3 publican un
# valor en una palabra de memoria propia y después suben una bandera. El hilo
# 0 espera las tres banderas, suma los tres valores y escribe el resultado en
# el display y en los LEDs.
#
# Regla de uso de la memoria compartida: cada palabra tiene un solo hilo que
# la escribe. Un load y un store son atómicos (un acceso al bus por
# instrucción y un solo hilo en la etapa de ejecución por ciclo), pero leer,
# modificar y escribir son tres instrucciones y entre ellas corren los otros
# hilos. Con un solo escritor por palabra no hace falta nada más. La bandera
# se escribe después del valor, así que quien ve la bandera ve el valor.
#
#   hilo 1   suma 1 + ... + 10 = 55
#   hilo 2   6 * 7 = 42 por sumas repetidas
#   hilo 3   255
#   hilo 0   55 + 42 + 255 = 352 = 0x160. Display "60", LEDs 1111 si la suma
#            es 352 y 0001 si no.
# =============================================================================

.equ PERIPH_HI, 0x80000
.equ OFF_DISP,  0
.equ OFF_LEDS,  4

.equ VALOR1,    0x7C0
.equ VALOR2,    0x7C4
.equ VALOR3,    0x7C8
.equ LISTO1,    0x7D0
.equ LISTO2,    0x7D4
.equ LISTO3,    0x7D8

# --- Tabla de arranque ----------------------------------------------------------
    j    supervisor
    j    hilo1
    j    hilo2
    j    hilo3

# --- Hilo 0: supervisor ---------------------------------------------------------
supervisor:
    lui  x2, PERIPH_HI
espera1:
    lw   x5, LISTO1(x0)
    beqz x5, espera1
espera2:
    lw   x5, LISTO2(x0)
    beqz x5, espera2
espera3:
    lw   x5, LISTO3(x0)
    beqz x5, espera3
    lw   x6, VALOR1(x0)
    lw   x7, VALOR2(x0)
    lw   x9, VALOR3(x0)
    add  x6, x6, x7
    add  x6, x6, x9              # 352
    sw   x6, OFF_DISP(x2)        # el display muestra los 8 bits bajos: "60"
    addi x7, x0, 352
    addi x10, x0, 1              # LEDs si falla
    bne  x6, x7, sup_leds
    addi x10, x0, 15             # LEDs si pasa
sup_leds:
    sw   x10, OFF_LEDS(x2)
sup_fin:
    j    sup_fin

# --- Hilo 1: suma de 1 a 10 -----------------------------------------------------
hilo1:
    addi x5, x0, 10
    addi x6, x0, 0
h1_lazo:
    add  x6, x6, x5
    addi x5, x5, -1
    bnez x5, h1_lazo
    sw   x6, VALOR1(x0)
    addi x7, x0, 1
    sw   x7, LISTO1(x0)
h1_fin:
    j    h1_fin

# --- Hilo 2: 6 * 7 --------------------------------------------------------------
hilo2:
    addi x5, x0, 7
    addi x6, x0, 0
h2_lazo:
    addi x6, x6, 6
    addi x5, x5, -1
    bnez x5, h2_lazo
    sw   x6, VALOR2(x0)
    addi x7, x0, 1
    sw   x7, LISTO2(x0)
h2_fin:
    j    h2_fin

# --- Hilo 3: una constante, publicada mucho después que las otras -------------
hilo3:
    addi x5, x0, 200             # demora, para que el supervisor tenga que esperar
h3_lazo:
    addi x5, x5, -1
    bnez x5, h3_lazo
    addi x6, x0, 255
    sw   x6, VALOR3(x0)
    addi x7, x0, 1
    sw   x7, LISTO3(x0)
h3_fin:
    j    h3_fin

# Relleno con ceros hasta las 512 palabras de la RAM
.org 0x800
