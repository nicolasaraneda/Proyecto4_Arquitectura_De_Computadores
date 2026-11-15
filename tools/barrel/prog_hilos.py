#!/usr/bin/env python3
"""prog_hilos.py: programa aleatorio de cuatro hilos para verificar el Espino barrel.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 prog_hilos.py SEMILLA -o programa.s [--modo separado|compartido|spi1|trade|uno]
                          [-n 72] [--hilo-spi T] [--trade sw/trade.s] [--jalr-libre]
                          [--peso-spi 7] [--peso-periph 3] [--lineal]

Sale del generador del repositorio (tools/prog_aleatorio.py), con la misma
mezcla de instrucciones, repetido en cuatro hilos. El programa empieza con la
tabla de arranque del barrel (el hilo t parte en la dirección 4 t) y cada
hilo tiene su propio cuerpo de instrucciones al azar, que se repite para
siempre, y sus propios valores iniciales de registros.

Modos:
  separado    Cada hilo tiene su zona de datos (16 palabras) y no toca las de
              los demás. Los cuatro leen y escriben los registros del esclavo
              SPI y de los periféricos. Con el bus SPI quieto lo que lee un
              hilo no depende de los otros, así que cada hilo debe hacer
              exactamente lo mismo que el Espino base corriendo solo.
  compartido  Los cuatro hilos leen y escriben la misma zona de datos (16
              palabras). Lo que lee un hilo depende del orden en que los
              cuatro acceden a la memoria. En este modo se deja que un jalr
              salga con una base cualquiera, así que un hilo puede terminar
              ejecutando el código de otro. La referencia son cuatro Espino
              base que ejecutan una instrucción cada uno por turnos, con las
              escrituras de cada uno copiadas a la memoria de los demás
              (tb/tb_verif.sv con +compartida=1).
  spi1        Como separado, pero solo el hilo --hilo-spi accede al esclavo
              SPI (el doble de veces). Sirve para la prueba en que el
              testbench hace llegar precios nuevos entre dos instrucciones de
              ese hilo: los otros tres no pueden tocar el SPI porque bajarían
              la bandera de precio nuevo.
  trade       El hilo --hilo-spi corre el programa de --trade (sw/trade.s, que
              se copia al final sin cambios) y los otros tres corren cuerpos
              al azar que no tocan el SPI, cada uno con su zona de datos. Es
              el caso del fondo de estrategias: un hilo atiende a la maestra
              mientras los demás calculan. Las zonas quedan en 0x600 a 0x6FF y
              el programa de --trade después, así que su palabra de trabajo
              (0x7FC) no se toca.
  uno         Solo el hilo --hilo-spi tiene cuerpo (hasta 300 instrucciones) y
              los otros tres quedan en un lazo vacío.

Igual que en tools/prog_aleatorio.py: los saltos van siempre hacia adelante y
dentro del cuerpo del hilo, x13, x14 y x15 guardan las direcciones base y
nunca se escriben, y los stores solo tocan la zona de datos. Dos diferencias
con ese generador:

  - Fuera del modo compartido ningún salto cae en un jalr sin pasar por su
    auipc (ver cuerpo), para que ningún hilo se salga de su código. Con
    --jalr-libre se permite en cualquier modo, como en el generador original:
    lo usa tools/verif.sh para dejar medido por qué hizo falta el cambio.
  - Los programas no se quedan quietos. En el generador original, después de
    una o dos vueltas del cuerpo los registros llegan a un punto fijo y todas
    las vueltas siguientes repiten los mismos valores (se ve en la columna
    de instrucciones distintas de mediciones/verificacion.txt, grupo A contra
    grupo U). Aquí x11 y x12 no se usan como
    destino en el cuerpo y al comienzo de cada vuelta avanzan con una
    recurrencia de sumas (x12 += x11; x11 += impar + x12), así que cada
    vuelta empieza con valores nuevos. El cuerpo los usa como operandos igual
    que a los demás y además una de cada siete operaciones entre registros
    mezcla uno de los dos en un registro cualquiera.

Con --lineal el cuerpo de cada hilo se ejecuta una sola vez y termina en un
lazo vacío (un salto a sí mismo), donde tb/barrel/tb_verif.sv da por terminada
la corrida (+fin_lazo=1). Es el generador de la campaña del criterio 5 de la
puerta de simulación: como casi ninguna instrucción se repite, lo que se
compara son instrucciones distintas y no vueltas del mismo lazo. Para que los
saltos hacia atrás sigan ejercitados, el cuerpo lleva además lazos cortos con
contador (2 a 4 vueltas, con operandos que cambian en cada vuelta). En el modo
compartido no se ponen, porque ahí un jalr puede caer dentro de uno con el
contador en cualquier valor. Ningún salto de un cuerpo lineal cae dentro de
un lazo.
"""
import argparse
import random

ALU_R = ["add", "sub", "xor", "or", "and", "slt", "sltu"]
ALU_I = ["addi", "slti", "sltiu", "xori", "ori", "andi"]
SHIFT_R = ["sll", "srl", "sra"]
SHIFT_I = ["slli", "srli", "srai"]
LOADS = ["lw", "lh", "lhu", "lb", "lbu"]
STORES = ["sw", "sh", "sb"]
BRANCHES = ["beq", "bne", "blt", "bge", "bltu", "bgeu"]

NDATOS = 16                      # palabras de cada zona de datos
FIN = 0x800                      # la memoria tiene 512 palabras


def cuerpo(rng, t, n, spi, periph, jalr_libre, lineal=False):
    """Devuelve las líneas del hilo t: entrada, valores iniciales y cuerpo.

    En tools/prog_aleatorio.py un salto puede caer justo en un jalr, sin pasar
    por el auipc que le prepara la base, y el jalr sale con una base
    cualquiera. Con un solo hilo no importa. Con cuatro, el hilo puede caer en
    el código de otro y leer su zona de datos o el SPI, y entonces ya no se
    puede comparar con un Espino base que corre solo. Con jalr_libre = False
    ningún salto cae en un jalr: destinos lleva los índices a los que salta
    alguna instrucción anterior.
    """
    rd = lambda: f"x{rng.choice([0] + list(range(1, 11)) * 4)}"
    rs = lambda: f"x{rng.randint(0, 15)}"
    imm = lambda: rng.choice([rng.randint(-2048, 2047), rng.randint(-8, 8), 0, 1, -1, 2047, -2048])
    L = lambda k: f"h{t}_L{k}"

    pesos = {"alu_r": 22, "alu_i": 22, "shift": 5, "lui": 5, "load": 12, "store": 11,
             "spi": spi, "periph": periph, "branch": 10, "jal": 2, "jalr": 2, "rara": 4,
             "lazo": 3 if lineal and not jalr_libre else 0}
    tipos = [k for k, v in pesos.items() if v > 0]
    ini = [f"    li   x15, zona{t}",
           "    li   x14, 0x80010000",
           "    li   x13, 0x80000000"]
    for r in range(1, 11):
        # En un cuerpo lineal casi todos los valores iniciales son de 32 bits:
        # un valor chico en la misma dirección se repite de una corrida a otra
        if lineal and rng.random() < 0.8:
            ini.append(f"    li   x{r}, {rng.getrandbits(32)}")
            continue
        ini.append(f"    li   x{r}, {rng.choice([rng.getrandbits(32), rng.randint(-300, 300), rng.randint(0, 255)])}")
    ini.append(f"    li   x11, {rng.getrandbits(32)}")
    ini.append(f"    li   x12, {rng.getrandbits(32)}")
    if lineal:
        # En orden al azar, para que las tres bases no queden siempre en las
        # mismas direcciones y no se repitan de una corrida a otra
        rng.shuffle(ini)
    out = [f"hilo{t}:"] + ini
    # Cada vuelta empieza con valores nuevos en x11 y x12 (ver el encabezado)
    out.append(f"h{t}_cuerpo:")
    out.append("    add  x12, x12, x11")
    out.append(f"    addi x11, x11, {2 * rng.randint(0, 1023) + 1}")
    out.append("    add  x11, x11, x12")

    c = []
    destinos = set()
    while len(c) < n:
        tipo = rng.choices(tipos, [pesos[k] for k in tipos])[0]
        adelante = lambda desde: min(n, desde + 1 + rng.randint(0, 4))
        if tipo == "alu_r":
            if rng.random() < 0.15:           # mezcla un valor nuevo en un registro
                r = rng.randint(1, 10)
                c.append(f"{rng.choice(['add', 'xor', 'sub'])} x{r}, x{r}, x{rng.choice([11, 12])}")
            else:
                c.append(f"{rng.choice(ALU_R)} {rd()}, {rs()}, {rs()}")
        elif tipo == "alu_i":
            c.append(f"{rng.choice(ALU_I)} {rd()}, {rs()}, {imm()}")
        elif tipo == "shift":
            if rng.random() < 0.5:
                c.append(f"{rng.choice(SHIFT_R)} {rd()}, {rs()}, {rs()}")
            else:
                c.append(f"{rng.choice(SHIFT_I)} {rd()}, {rs()}, {rng.randint(0, 31)}")
        elif tipo == "lui":
            c.append(f"{rng.choice(['lui', 'auipc'])} {rd()}, {rng.getrandbits(20)}")
        elif tipo == "load":
            c.append(f"{rng.choice(LOADS)} {rd()}, {rng.randint(0, 4 * NDATOS - 1)}(x15)")
        elif tipo == "store":
            c.append(f"{rng.choice(STORES)} {rs()}, {rng.randint(0, 4 * NDATOS - 1)}(x15)")
        elif tipo == "spi":
            if rng.random() < 0.6:
                c.append(f"{rng.choice(['lw', 'lw', 'lbu', 'lh'])} {rd()}, {rng.choice([0, 4, 4, 8, 12, 5])}(x14)")
            else:
                c.append(f"{rng.choice(STORES)} {rs()}, {rng.choice([8, 8, 8, 0, 4, 12, 9])}(x14)")
        elif tipo == "periph":
            if rng.random() < 0.5:
                c.append(f"lw {rd()}, {rng.choice([0, 4, 8, 8])}(x13)")
            else:
                c.append(f"sw {rs()}, {rng.choice([0, 4, 8])}(x13)")
        elif tipo == "branch":
            d = adelante(len(c))
            destinos.add(d)
            c.append(f"{rng.choice(BRANCHES)} {rs()}, {rs()}, {L(d)}")
        elif tipo == "jal":
            d = adelante(len(c))
            destinos.add(d)
            c.append(f"jal {rd()}, {L(d)}")
        elif tipo == "lazo":
            # Lazo corto con contador en x12: 2 a 4 vueltas de 1 a 3 operaciones
            # cuyos operandos cambian en cada vuelta. Solo se entra por arriba.
            k = rng.randint(1, 3)
            if len(c) + k + 3 > n or any(len(c) < d <= len(c) + k + 2 for d in destinos):
                continue
            ini = len(c) + 1
            c.append(f"addi x12, x0, {rng.randint(2, 4)}")
            for _ in range(k):
                r = rng.randint(1, 10)
                c.append(rng.choice([f"add x{r}, x{r}, x11", f"xor x{r}, x{r}, x{rng.randint(1, 10)}",
                                     f"sub x11, x11, x{r}", f"add x{r}, x{r}, x12",
                                     f"sw x{r}, {4 * rng.randint(0, NDATOS - 1)}(x15)",
                                     f"lw x{r}, {4 * rng.randint(0, NDATOS - 1)}(x15)"]))
            c.append("addi x12, x12, -1")
            c.append(f"bne x12, x0, {L(ini)}")
        elif tipo == "jalr":
            if len(c) + 2 > n:
                continue
            if not jalr_libre and len(c) + 1 in destinos:
                continue                                              # algún salto caería en el jalr
            r = rng.randint(1, 10)
            salto = min(n - len(c), 2 + rng.randint(0, 3))            # en instrucciones, desde el auipc
            destinos.add(len(c) + salto)
            c.append(f"auipc x{r}, 0")
            c.append(f"jalr {rd()}, {4 * salto + rng.choice([0, 0, 1])}(x{r})")   # el bit 0 se descarta
        else:
            r_d, r_s = rng.choice(range(1, 11)), rng.randint(0, 15)
            alto = rng.getrandbits(25) << 7
            destinos.add(len(c) + 2)          # por si el branch con funct3 inválido salta (desplazamiento 8)
            c.append(rng.choice([
                f".word {alto | 0x0B}",                                   # custom-0: no hace nada
                f".word {(alto & ~0x7000) | 0x0F}",                       # misc-mem
                f".word {0x00000073 | (rng.getrandbits(1) << 20)}",       # ecall, ebreak
                f".word {(rng.randint(0, 4 * NDATOS - 1) << 20) | (15 << 15) | (rng.choice([3, 6, 7]) << 12) | (r_d << 7) | 0x03}",  # load con funct3 inválido
                f".word {(r_s << 20) | (rng.randint(1, 12) << 15) | (rng.choice([2, 3]) << 12) | (8 << 7) | 0x63}",              # branch con funct3 inválido
            ]))

    for k, texto in enumerate(c):
        out.append(f"{L(k)}:")
        out.append(f"    {texto}")
    out.append(f"{L(len(c))}:")
    out.append(f"    j    {L(len(c))}" if lineal else f"    j    h{t}_cuerpo")
    return out


def generar(semilla, n, modo, hilo_spi, trade=None, peso_spi=7, peso_periph=3, jalr_libre=False, lineal=False):
    rng = random.Random(semilla)
    zonas = 1 if modo == "compartido" else 4
    base = 0x600 if modo == "trade" else FIN - 4 * NDATOS * zonas
    out = [f"# Programa aleatorio de cuatro hilos, semilla {semilla}, modo {modo}.",
           "# Generado por tools/barrel/prog_hilos.py." + (" Cuerpos lineales." if lineal else "")]
    for t in range(4):
        if modo == "uno" and t != hilo_spi:
            out += [f"ocioso{t}:", f"    j    ocioso{t}"]
        else:
            out.append("    j    _start" if modo == "trade" and t == hilo_spi else f"    j    hilo{t}")
    for t in range(4):
        out.append(f".equ zona{t}, {base + (0 if zonas == 1 else 4 * NDATOS * t)}")
    for t in range(4):
        if modo == "uno" and t != hilo_spi:
            continue
        if modo == "trade":
            if t == hilo_spi:
                continue
            spi = 0
        elif modo == "spi1":
            spi = 2 * peso_spi if t == hilo_spi else 0
        else:
            spi = peso_spi
        out += cuerpo(rng, t, n, spi, peso_periph, jalr_libre or modo == "compartido", lineal)
    out.append(f".org {base}")
    for _ in range(zonas * NDATOS // 4):
        out.append("    .word " + ", ".join(str(rng.getrandbits(32)) for _ in range(4)))
    if modo == "trade":
        out.append(f"# --- {trade}, sin cambios ---")
        out.append(open(trade, encoding="utf-8").read().rstrip("\n"))
    else:
        out.append(f".org {FIN}")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("semilla", type=int)
    ap.add_argument("-o", "--salida", required=True)
    ap.add_argument("-n", type=int, default=72, help="instrucciones del cuerpo de cada hilo")
    ap.add_argument("--modo", choices=["separado", "compartido", "spi1", "trade", "uno"], default="separado")
    ap.add_argument("--hilo-spi", type=int, default=0, choices=[0, 1, 2, 3])
    ap.add_argument("--trade", default="sw/trade.s", help="programa del hilo --hilo-spi en el modo trade")
    ap.add_argument("--jalr-libre", action="store_true", help="deja que un salto caiga en un jalr sin pasar por su auipc")
    ap.add_argument("--peso-spi", type=int, default=7, help="peso de los accesos al SPI en la mezcla (por defecto 7 de 100)")
    ap.add_argument("--peso-periph", type=int, default=3, help="peso de los accesos a los periféricos (por defecto 3 de 100)")
    ap.add_argument("--lineal", action="store_true", help="cada cuerpo se ejecuta una vez y termina en un lazo vacio")
    a = ap.parse_args()
    if a.lineal and a.modo == "trade":
        ap.error("--lineal no aplica al modo trade")
    if not 1 <= a.n <= (300 if a.modo == "uno" else 90):
        ap.error("-n debe estar entre 1 y 90 (300 en el modo uno)")
    with open(a.salida, "w", encoding="utf-8", newline="\n") as f:
        f.write(generar(a.semilla, a.n, a.modo, a.hilo_spi, a.trade, a.peso_spi, a.peso_periph, a.jalr_libre, a.lineal))


if __name__ == "__main__":
    main()
