#!/usr/bin/env python3
"""contabilidad.py: la contabilidad de la maestra contra la que emula R3 (sw/c1.s y ref/c1/c1.py).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

R3 lleva una copia de la caja y de las acciones de la maestra (sw/c1.s, rutina `ejecutar`) y decide con
ella. Si esa copia difiere de la contabilidad de la maestra, el candado y la media posición se deciden
con una cuenta que no es la real. Dos partes:

 1. La tarea `ejecutar` del testbench oficial (tb/tb_proyecto_4.sv, el texto entre "Contabilidad
    oficial" y "Mide los ciclos", copiado tal cual y compilado con Icarus) contra tres cosas, para
    comisión 0, 5 y 50 y vectores (byte, precio, caja, acciones): ref/market.py, la `ejecutar` de
    ref/c1/c1.py y la rutina `ejecutar` de sw/c1.s ya ensamblada, corrida en un simulador RV32I mínimo
    (la rutina del arnés se comprueba palabra por palabra contra el ensamblado de sw/c1.s).
    Se separan las diferencias que caen fuera de lo que la competencia puede producir (byte con las
    dos acciones en 1, que el testbench trata como mantener y la referencia como compra; venta cuyo
    producto no cubre la comisión, que el testbench no ejecuta) de las que caen dentro (precio de 100 a
    255 y byte sin acción 11): estas últimas tienen que ser cero.
 2. Tick a tick, la caja, las acciones y el patrimonio que emula ref/c1/c1.py contra los de la maestra
    (ref/market.py, porte exacto del testbench oficial, que la parte 1 comprueba) en series de 20 000
    ticks: la de práctica, las sintéticas y, si existe $P4_DATOS, las otras acciones y las cinco empresas.
    Cuenta cuántas veces la fase A apuesta (media posición) y cuántas órdenes parciales hay.

El RTL contra la referencia, tick a tick (caja y acciones incluidas), es de la puerta b (make c1-puerta-b).

Uso, desde la raíz: python3 tools/c1/contabilidad.py [--vectores N] [--ventanas N] [-o salida.txt]
(make c1-contabilidad; unos 2 minutos)
"""
import argparse
import hashlib
import importlib.util
import multiprocessing as mp
import os
import random
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
sys.path.insert(0, os.path.join(RAIZ, "ref", "cotas"))
sys.path.insert(0, os.path.join(RAIZ, "ref", "c1"))
import market  # noqa: E402
import comun  # noqa: E402
import series as familias  # noqa: E402
import tablas as TB  # noqa: E402

_spec = importlib.util.spec_from_file_location("c1ref", os.path.join(RAIZ, "ref", "c1", "c1.py"))
c1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c1)

M32 = 0xFFFFFFFF
COMISIONES = (0, 5, 50)
D_COM, CUENTA = 0x200, 0x300       # direcciones de datos del arnés del simulador


def s32(x):
    x &= M32
    return x - (1 << 32) if x >> 31 else x


# --- vectores ------------------------------------------------------------------------------------------

def vectores(com, n_aleatorios, semilla):
    rng = random.Random(semilla + com)
    p_clave = [1, 3, 4, 5, 6, 99, 100, 101, 128, 177, 254, 255]
    acc_clave = [0, 1, 2, 31, 32, 33, 63, 64, 200, 400]
    cantidades = [0, 1, 2, 3, 4, 5, 8, 15, 16, 17, 31, 32, 33, 47, 48, 62, 63]
    bytes_ = [(a << 6) | q for a in range(4) for q in cantidades]
    vec = []
    for p in p_clave:
        cajas = set(range(40))
        for k in range(66):                                   # cajas en el borde de cada cantidad
            for d in (-1, 0, 1):
                if com + k * p + d >= 0:
                    cajas.add(com + k * p + d)
        cajas |= {10000, 10005, 25500, 32768, 40000}
        for b in bytes_:
            for caja in sorted(cajas):
                for acc in acc_clave:
                    vec.append((b, p, caja, acc))
    for _ in range(n_aleatorios):
        p = rng.choice([rng.randint(1, 255), rng.randint(100, 255), rng.randint(100, 255)])
        caja = rng.choice([rng.randint(0, 60), rng.randint(0, 3000), rng.randint(0, 40000), rng.randint(0, 40000)])
        acc = rng.choice([rng.randint(0, 70), rng.randint(0, 200), rng.randint(0, 255)])
        vec.append((rng.randint(0, 255), p, caja, acc))
    return vec


def tarea_oficial():
    """El texto de la contabilidad oficial del testbench, sin tocar."""
    with open(os.path.join(RAIZ, "tb", "tb_proyecto_4.sv"), encoding="utf-8") as f:
        t = f.read()
    a = t.index("  int caja = CAJA0")
    b = t.index("  // Mide los ciclos")
    return t[a:b]


def correr_testbench(vec, com, d):
    """Pasa los vectores por la tarea oficial con Icarus. Devuelve [(caja, acciones, ordenes)]."""
    cuerpo = ("`timescale 1ns/1ps\nmodule t;\n  parameter int COMISION = 5; parameter int CAJA0 = 10000;\n" + tarea_oficial() + """
  int fd, fo, o_byte, o_p, o_caja, o_acc;
  logic [7:0] b;
  initial begin
    fd = $fopen("vec.txt", "r"); fo = $fopen("sv.txt", "w");
    while ($fscanf(fd, "%d %d %d %d\\n", o_byte, o_p, o_caja, o_acc) == 4) begin
      caja = o_caja; acciones = o_acc; ordenes = 0; w = 0; peak = 0; max_dd = 0;
      b = o_byte[7:0];
      ejecutar(b, o_p);
      $fdisplay(fo, "%0d %0d %0d", caja, acciones, ordenes);
    end
    $fclose(fo); $finish;
  end
endmodule
""")
    with open(os.path.join(d, "t.sv"), "w") as f:
        f.write(cuerpo)
    with open(os.path.join(d, "vec.txt"), "w") as f:
        f.write("".join("%d %d %d %d\n" % v for v in vec))
    subprocess.run(["iverilog", "-g2012", "-s", "t", "-o", f"t{com}", f"-Pt.COMISION={com}", "t.sv"], cwd=d, check=True)
    subprocess.run(["vvp", "-n", f"t{com}"], cwd=d, check=True, stdout=subprocess.DEVNULL)
    with open(os.path.join(d, "sv.txt")) as f:
        return [tuple(map(int, l.split())) for l in f]


# --- la rutina ensamblada de sw/c1.s en un simulador RV32I mínimo --------------------------------------

def rutina_ejecutar():
    with open(os.path.join(RAIZ, "sw", "c1.s"), encoding="utf-8") as f:
        lineas = f.read().split("\n")
    a = next(i for i, l in enumerate(lineas) if l.startswith("ejecutar:"))
    b = next(i for i, l in enumerate(lineas) if l.startswith("ej_fin:")) + 2      # incluye el jr x12
    return "\n".join(lineas[a:b])


def ensamblar(fuente, salida):
    subprocess.run([sys.executable, os.path.join(RAIZ, "tools", "pochoasm.py"), fuente, "-o", salida],
                   check=True, stdout=subprocess.DEVNULL)
    with open(salida) as f:
        return [int(x, 16) for x in f.read().split()]


def preparar_asm(d):
    """Ensambla un arnés con la rutina y comprueba que es la de sw/c1.s ensamblado. Devuelve el programa del arnés."""
    with open(os.path.join(d, "arnes.s"), "w") as f:
        f.write("halt: j halt\n" + rutina_ejecutar() + f"\n.org {D_COM:#x}\nD_COM: .word 5\n")
    arnes = ensamblar(os.path.join(d, "arnes.s"), os.path.join(d, "arnes.hex"))
    real = ensamblar(os.path.join(RAIZ, "sw", "c1.s"), os.path.join(d, "c1.hex"))
    cod = arnes[1:D_COM // 4]
    while cod and cod[-1] == 0:
        cod.pop()

    def enm(w):    # los lw con rs1 = x0 llevan la dirección absoluta de D_COM, que cambia entre el arnés y el programa
        return (w & 0xFFFFF) if (w & 0x7F) == 0x03 and ((w >> 15) & 31) == 0 else w
    pos = [i for i in range(len(real) - len(cod) + 1) if [enm(w) for w in real[i:i + len(cod)]] == [enm(w) for w in cod]]
    dist = [j for j in range(len(cod)) if real[pos[0] + j] != cod[j]] if pos else []
    ok = bool(pos) and len(dist) == 2 and all((cod[j] & 0x7F) == 0x03 for j in dist)
    return arnes, ok, (pos[0] if pos else None), len(cod)


def imm_i(w): return s32(w) >> 20
def imm_s(w): return (s32(w) >> 25 << 5) | ((w >> 7) & 31)
def imm_b(w): return (s32(w & 0x80000000) >> 19) | ((w & 0x80) << 4) | ((w >> 20) & 0x7E0) | ((w >> 7) & 0x1E)
def imm_j(w): return (s32(w & 0x80000000) >> 11) | (w & 0xFF000) | ((w >> 9) & 0x800) | ((w >> 20) & 0x7FE)


def iss(prog, byte, p, caja, acc, com):
    """Corre `ejecutar` desde la dirección 4 hasta que vuelve a 0 (halt). Devuelve (caja, acciones)."""
    x = [0] * 32
    mem = {D_COM: com, CUENTA: caja & M32, CUENTA + 4: acc & M32}
    x[1], x[2], x[3], x[4], x[5], x[6] = p, 2 * p, 4 * p, 8 * p, 16 * p, 32 * p
    x[10], x[11], x[12] = byte, CUENTA, 0
    pc, n = 4, 0
    while pc != 0:
        w = prog[pc >> 2]
        op, rd, f3 = w & 0x7F, (w >> 7) & 31, (w >> 12) & 7
        a, b = x[(w >> 15) & 31] & M32, x[(w >> 20) & 31] & M32
        nxt = pc + 4
        if op == 0x13:
            i = imm_i(w) & M32
            x[rd] = s32({0: a + i, 4: a ^ i, 7: a & i, 6: a | i, 3: int(a < i), 2: int(s32(a) < s32(i))}[f3])
        elif op == 0x33:
            r = (a - b if (w >> 30) & 1 else a + b) if f3 == 0 else {7: a & b, 6: a | b, 4: a ^ b, 3: int(a < b), 2: int(s32(a) < s32(b))}[f3]
            x[rd] = s32(r)
        elif op == 0x03:
            d = (a + imm_i(w)) & M32
            x[rd] = s32(mem.get(d, 0)) if f3 == 2 else (mem.get(d & ~3, 0) >> (8 * (d & 3))) & 255
        elif op == 0x23:
            mem[(a + imm_s(w)) & M32] = b
        elif op == 0x63:
            sa, sb = s32(a), s32(b)
            if {0: a == b, 1: a != b, 4: sa < sb, 5: sa >= sb, 6: a < b, 7: a >= b}[f3]:
                nxt = pc + imm_b(w)
        elif op == 0x6F:
            if rd:
                x[rd] = pc + 4
            nxt = pc + imm_j(w)
        elif op == 0x67:
            nxt = (a + imm_i(w)) & ~1
            if rd:
                x[rd] = pc + 4
        else:
            raise SystemExit("opcode %x en %x" % (op, pc))
        x[0], pc, n = 0, nxt, n + 1
        if n > 400:
            raise SystemExit("la rutina no termina")
    return s32(mem[CUENTA]), mem[CUENTA + 4] & M32


# --- parte 1: vectores -------------------------------------------------------------------------------

G = {}


def clase(byte, p, caja, acc, com):
    """Por qué difiere un resultado: fuera de lo que la competencia puede producir, o 'OTRA'."""
    k = []
    if byte >> 6 == 3:
        k.append("byte con las dos acciones en 1")
    q = min(byte & 63, acc)
    if byte >> 6 == 2 and q > 0 and caja + q * p < com:
        k.append("venta que no cubre la comision")
    return " y ".join(k) or "OTRA"


def comparar_lote(rango):
    ini, fin = rango
    prog, com, vec, sv = G["prog"], G["com"], G["vec"], G["sv"]
    dif = {"ref": {}, "asm": {}, "market": {}}
    ej = {}
    dom = {"n": 0, "ref": 0, "asm": 0, "market": 0}
    for i in range(ini, fin):
        byte, p, caja, acc = vec[i]
        sc, sa, so = sv[i]
        m = market.Mercado(com, com)
        m.caja, m.acciones = caja, acc
        m.ejecutar(byte, p)
        rc, ra, rej = c1.ejecutar(byte, p, caja, acc, com)
        ac, aa = iss(prog, byte, p, caja, acc, com)
        en_dominio = byte >> 6 != 3 and p >= 100
        dom["n"] += en_dominio
        for nombre, obtenido in (("market", (m.caja, m.acciones)), ("ref", (rc, ra)), ("asm", (ac, aa))):
            if obtenido != (sc, sa):
                k = clase(byte, p, caja, acc, com)
                dif[nombre][k] = dif[nombre].get(k, 0) + 1
                ej.setdefault((nombre, k), (byte, p, caja, acc, (sc, sa), obtenido))
                if en_dominio:
                    dom[nombre] += 1
    return dif, ej, dom


def parte1(args, d, salida):
    arnes, ok, pos, largo = preparar_asm(d)
    salida(f"Rutina `ejecutar` de sw/c1.s ({largo} palabras) idéntica, salvo la dirección absoluta de D_COM, a la del ensamblado "
           f"de sw/c1.s desde la palabra {pos}: {'sí' if ok else 'NO'}")
    fallos = 0 if ok else 1
    for com in COMISIONES:
        vec = vectores(com, args.vectores, 7)
        sv = correr_testbench(vec, com, d)
        G.update(prog=arnes, com=com, vec=vec, sv=sv)
        paso = 20000
        with mp.get_context("fork").Pool(min(22, os.cpu_count() or 1)) as pool:
            res = pool.map(comparar_lote, [(i, min(i + paso, len(vec))) for i in range(0, len(vec), paso)])
        dif = {"ref": {}, "asm": {}, "market": {}}
        ej = {}
        dom = {"n": 0, "ref": 0, "asm": 0, "market": 0}
        for r in res:
            for nom in dif:
                for k, c in r[0][nom].items():
                    dif[nom][k] = dif[nom].get(k, 0) + c
            for k, v in r[1].items():
                ej.setdefault(k, v)
            for k in dom:
                dom[k] += r[2][k]
        salida(f"\nComisión {com}: {len(vec)} vectores (byte, precio, caja, acciones) por la tarea del testbench oficial, ref/market.py, "
               f"ref/c1/c1.py y la rutina ensamblada")
        for nom, etiqueta in (("market", "ref/market.py"), ("ref", "ref/c1/c1.py `ejecutar`"), ("asm", "sw/c1.s `ejecutar` ensamblado")):
            total = sum(dif[nom].values())
            salida(f"  {etiqueta} contra el testbench: {total} diferencias" + (":" if total else ""))
            for k, c in sorted(dif[nom].items()):
                salida(f"    {k}: {c}; ejemplo (byte, precio, caja, acciones; testbench; este) = {ej[(nom, k)]}")
                if k == "OTRA":
                    fallos += 1
        salida(f"  dentro de lo que la competencia puede producir (precio de 100 a 255, byte sin acción 11): {dom['n']} vectores; "
               f"diferencias: market.py {dom['market']}, ref/c1/c1.py {dom['ref']}, sw/c1.s {dom['asm']}")
        if dom["market"] or dom["ref"] or dom["asm"]:
            fallos += 1
        if dif["market"]:
            fallos += 1
    return fallos


# --- parte 2: series -----------------------------------------------------------------------------------

def analizar(precios, T):
    """Tick a tick: la cuenta emulada de ref/c1/c1.py contra la de la maestra (market.py)."""
    c = c1.C1(T)
    m = market.Mercado()
    actual = 0
    mism, primero, entradas, parciales, previo = 0, None, 0, 0, 0
    for n, p in enumerate(precios):
        m.ejecutar(actual, p)                                   # la maestra ejecuta el byte que leyó en este tick
        actual = c.paso(p)                                      # el programa ve el precio y decide
        if (c.caja, c.acc, c.W) != (m.caja, m.acciones, m.w):
            mism += 1
            primero = primero or (n, p, (c.caja, c.acc, c.W), (m.caja, m.acciones, m.w))
        if c.modo == 0 and c.sa == 1 and previo == 0:
            entradas += 1
        previo = c.sa if c.modo == 0 else 0
        parciales += 1 if 0 < (actual & 63) < 63 else 0
    return dict(mism=mism, primero=primero, entradas=entradas, parciales=parciales, ordenes=m.ordenes, W=m.w)


def _serie_ref(args):
    T, precios = args
    return analizar(precios, T)


def _ventanas_datos(args):
    T, ruta, semilla, n, largo = args
    with open(ruta) as f:
        x = [float(l.split(",")[2]) for l in f.read().splitlines()[1:]]
    rng = random.Random(semilla)
    out = []
    for _ in range(n):
        i = rng.randrange(len(x) - largo)
        out.append(analizar(comun.normalizar(x[i:i + largo]), T))
    return out


def _sintetica(args):
    T, fam, sem = args
    return analizar(comun.normalizar(familias.lote(fam, 1, 20000, sem)[0]), T)


def parte2(args, salida):
    T = TB.leer_hex(os.path.join(RAIZ, "sw", "c1_tabla.hex"))
    grupos = []
    pool = mp.get_context("fork").Pool(min(22, os.cpu_count() or 1))
    for ruta in ("data/practica_meta.csv", "tb/practica.csv"):
        grupos.append((ruta, [analizar(market.leer_serie(os.path.join(RAIZ, ruta)), T)]))
    grupos.append(("sintéticas (%d familias de ref/series.py, normalizadas, 20 000 ticks)" % len(familias.FAMILIAS),
                   pool.map(_sintetica, [(T, f, s) for f in familias.FAMILIAS for s in range(1, args.ventanas // 80 + 1)])))
    datos = os.path.expanduser(os.environ.get("P4_DATOS", "~/proyectos/datos_p4"))
    otras = os.path.join(datos, "otras")
    minuto = os.path.join(datos, "minuto")
    if os.path.isdir(otras):
        emp = sorted(f for f in os.listdir(otras) if f.endswith(".csv"))
        r = [x for l in pool.map(_ventanas_datos, [(T, os.path.join(otras, e), 5000 + k, args.ventanas // 100, 20000)
                                                  for k, e in enumerate(emp)]) for x in l]
        grupos.append((f"otras acciones ({len(emp)}, ventanas de 20 000 minutos normalizadas, $P4_DATOS/otras)", r))
    else:
        salida(f"(sin {otras}: no se corren las otras acciones)")
    if os.path.isdir(minuto):
        r = [x for l in pool.map(_ventanas_datos, [(T, os.path.join(minuto, e + ".csv"), 77 + k, args.ventanas // 20, 20000)
                                                  for k, e in enumerate(("META", "AAPL", "NFLX", "AMD", "TSLA"))]) for x in l]
        grupos.append(("cinco empresas (ventanas de 20 000 minutos normalizadas, $P4_DATOS/minuto)", r))
    pool.close()
    fallos = 0
    salida("")
    for nombre, res in grupos:
        dif = sum(r["mism"] for r in res)
        salida(f"{nombre}: {len(res)} series; {sum(1 for r in res if r['entradas'] > 0)} con apuesta de la fase A, "
               f"{sum(r['parciales'] for r in res)} órdenes parciales, {sum(r['ordenes'] for r in res)} órdenes de la maestra; "
               f"ticks con diferencia entre la cuenta emulada y la maestra: {dif}")
        if dif:
            fallos += 1
            salida(f"   primera diferencia (tick, precio, emulada (caja, acciones, patrimonio), maestra): "
                   f"{next(r['primero'] for r in res if r['mism'])}")
    return fallos


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vectores", type=int, default=500000, help="vectores aleatorios por comisión, además de los dirigidos")
    ap.add_argument("--ventanas", type=int, default=2000, help="ventanas de la parte 2 (se reparten entre los grupos)")
    ap.add_argument("-o", "--salida")
    args = ap.parse_args()
    lineas = []

    def salida(t=""):
        print(t, flush=True)
        lineas.append(t)

    t0 = time.time()
    sha = hashlib.sha256
    cab = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
    iv = subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.split("\n")[0]
    salida("Contabilidad de la maestra contra la que emula R3 (sw/c1.s y ref/c1/c1.py)")
    salida("Generado por tools/c1/contabilidad.py (make c1-contabilidad). No editar a mano.")
    salida(f"\nCommit de partida: {cab}. {iv}")
    for ruta in ("tb/tb_proyecto_4.sv", "sw/c1.s", "ref/c1/c1.py", "ref/market.py"):
        salida(f"{ruta} sha256 {sha(open(os.path.join(RAIZ, ruta), 'rb').read()).hexdigest()[:16]}...")
    salida("\n1. La tarea `ejecutar` del testbench oficial contra las tres copias")
    with tempfile.TemporaryDirectory() as d:
        f1 = parte1(args, d, salida)
    salida("\n2. Tick a tick: la cuenta que emula ref/c1/c1.py contra la de la maestra (ref/market.py)")
    f2 = parte2(args, salida)
    f = f1 + f2
    salida(f"\n{'PASS' if f == 0 else 'FAIL'}: {f} comprobaciones falladas ({time.time() - t0:.0f} s)")
    if args.salida:
        os.makedirs(os.path.dirname(os.path.abspath(args.salida)), exist_ok=True)
        with open(args.salida, "w", newline="\n") as fo:
            fo.write("\n".join(lineas) + "\n")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
