#!/usr/bin/env python3
"""tablas.py: las tablas de C1 (R3), generadas desde el modelo del paseo normalizado.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Qué calcula (docs/c1_plan.md, sección 4):

  fase A   por celda (clase de v^2 j = 0..7, tramo de 1250 ticks restantes tr = 0..15) dos niveles:
             ENT  con posición 0 entra a media posición si p >= ENT. Es el mayor entre el umbral de
                  "media o más" de la política óptima V3 (objetivo log) y el menor precio con
                  probabilidad >= 0,95 de que el 255 llegue antes que el 100
             SAL  con media posición la mantiene si p >= SAL (umbral de V3 con posición 1/2)
  motor    por celda (fase B, C o D, clase j, tramo de 2500 ticks tr = 0..7) dos niveles de la
           política óptima V2 (objetivo log):
             BAJO   con posición 0 pasa a invertido si p <= BAJO
             BAJO1  invertido, se mantiene si p <= BAJO1
           (los otros dos umbrales de la celda de la exploración, alto y salida, valen 256 en las
           192 celdas: no se guardan, y este módulo lo comprueba)

Todo sale de ref/c1/paseo.py (el modelo) con los r del medio de cada tramo, igual que
optimo_estrategia.Comprimida y v5.comprimida_tramos de la exploración. No se lee ningún precio.

El cálculo completo demora unos 15 minutos con 24 núcleos; el resultado por clase queda en
build/c1/modelo/ y sw/c1_tabla.hex queda en el repositorio.

Uso, desde la raíz:
  python3 ref/c1/tablas.py --calcular [--jobs N]   calcula lo que falte en build/c1/modelo/
  python3 ref/c1/tablas.py --hex sw/c1_tabla.hex   escribe la tabla de la placa (512 palabras)
  python3 ref/c1/tablas.py --check sw/c1_tabla.hex compara el archivo con el modelo calculado
  python3 ref/c1/tablas.py --mostrar               imprime las celdas
"""
import argparse
import json
import os
import struct
import sys
from multiprocessing import Pool

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, AQUI)
import paseo as P  # noqa: E402

CACHE = os.environ.get("C1_MODELO", os.path.join(RAIZ, "build", "c1", "modelo"))
LO, HI, L, N = P.LO, P.HI, P.L, P.N
CLASES = len(P.V2S)
TRAMOS_A, LARGO_A = 16, N // 16          # fase A: 16 tramos de 1250 ticks
TRAMOS_M, LARGO_M = 8, N // 8            # motor: 8 tramos de 2500 ticks
FASES_M = "BCD"
P_MIN = 0.95                             # umbral de probabilidad de la apuesta en la fase A
# Cortes de la clase de v^2 en sesenta y cuatroavos (optimo_estrategia.N64 de la exploración): las
# medias geométricas de la grilla V2S redondeadas a 1/64. La clase es cuántos cumple 64 S2 >= N_j (t - 1).
N64 = (11, 20, 28, 39, 55, 78, 111)
T_MIN = 390                              # antes de este tick no se usa ninguna tabla
HISTERESIS = 64
D_MAX = 15                               # tope de la diferencia en S2

# --- formato de la tabla de la placa: 512 palabras de 16 bits (rtl/pochoco_tabla.v) ------------------
PALABRAS = 512
T_LO_MAS_1, T_HI, T_BANDA_COMPRA, T_BANDA_VENTA = 0, 1, 2, 3   # las cuatro de R2, en el mismo lugar
T_POLITICA = 4       # 0: política apagada (banda 40 exacta, como R2); 1: C1
T_CUAD64 = 16        # 16 palabras: 64 d^2
T_N64 = 32           # 7 palabras: los cortes de la clase
T_FASE_A = 64        # 128 palabras: celda j * 16 + tr; byte bajo ENT, byte alto SAL
T_MOTOR = 192        # 192 palabras: celda F * 64 + j * 8 + tr (F: B 0, C 1, D 2); byte bajo BAJO, alto BAJO1
POLITICA_APAGADA, POLITICA_C1 = 0, 1
USADAS = 5 + 16 + 7 + 128 + 192

# Parámetros que viven en el programa (palabras de datos de sw/c1.s, tools/c1/generar.py)
PROGRAMA = dict(plazo=28, caja=10000, comision=5, m=100, n_ronda=N, p_min=LO)

PARAMETROS = {       # los cuatro primeros son los de la banda 40 de R2 (sw/fondo_tabla.hex)
    T_LO_MAS_1: 101, T_HI: 255, T_BANDA_COMPRA: 141, T_BANDA_VENTA: 215, T_POLITICA: POLITICA_C1,
}


# --- compresión: copiada de optimo_estrategia.Comprimida (rama minutos-reales) ----------------------

def _intervalos(dec, i0):
    """Dos posiciones: (alto, bajo) de una fila de decisiones; 256 y 99 marcan intervalo vacío."""
    n = len(dec)
    bajo = 99
    k = 0
    while k < n and dec[k] == 1:
        bajo = LO + i0 + k
        k += 1
    alto = 256
    k = n - 1
    while k >= 0 and dec[k] == 0:          # corte superior (se ignora)
        k -= 1
    if k >= 0 and LO + i0 + k > bajo:
        while k >= 0 and dec[k] == 1 and LO + i0 + k > bajo:
            alto = LO + i0 + k
            k -= 1
    return alto, bajo


def _niveles(dec, i0):
    """Tres posiciones (V3): umbrales (a1, a2, b1, b2): s' >= 1/2 si x >= a1 o x <= b1; s' = 1 si
    x >= a2 o x <= b2. Arriba se ignoran los ceros y la media posición del corte superior."""
    n = len(dec)
    b1 = b2 = 99
    k = 0
    while k < n and dec[k] == 2:
        b2 = b1 = LO + i0 + k
        k += 1
    while k < n and dec[k] >= 1:
        b1 = LO + i0 + k
        k += 1
    a1 = a2 = 256
    k = n - 1
    while k >= 0 and dec[k] == 0:
        k -= 1
    while k >= 0 and dec[k] == 1 and LO + i0 + k > b1:
        k -= 1
    if k >= 0 and dec[k] == 2:
        while k >= 0 and dec[k] == 2 and LO + i0 + k > b1:
            a2 = a1 = LO + i0 + k
            k -= 1
        while k >= 0 and dec[k] >= 1 and LO + i0 + k > b1:
            a1 = LO + i0 + k
            k -= 1
    else:       # sin bloque de posición completa arriba: el bloque de media posición
        k = n - 1
        while k >= 0 and dec[k] == 0:
            k -= 1
        while k >= 0 and dec[k] >= 1 and LO + i0 + k > b1:
            a1 = LO + i0 + k
            k -= 1
    return a1, a2, b1, b2


# --- cálculo por clase ---------------------------------------------------------------------------

R_A = [tr * LARGO_A + LARGO_A // 2 for tr in range(TRAMOS_A)]
R_M = [tr * LARGO_M + LARGO_M // 2 for tr in range(TRAMOS_M)]


def _ruta(nombre, j):
    return os.path.join(CACHE, f"{nombre}_{j}.json")


def _guardar(ruta, dato):
    os.makedirs(CACHE, exist_ok=True)
    with open(ruta + ".tmp", "w") as f:
        json.dump(dato, f)
    os.replace(ruta + ".tmp", ruta)


def _f32(x):
    """El valor como float32, que es como la exploración guardó y comparó la tabla de pA."""
    return struct.unpack("f", struct.pack("f", x))[0]


def calcular_pa(j):
    """Por tramo de la fase A, la fila P(255 antes que 100 | x, r del medio del tramo, clase j)."""
    ruta = _ruta("pA", j)
    if os.path.exists(ruta):
        return ruta
    filas = {}

    def cada(r, gD, gB, gC, gA, hA):
        if r in R_A:
            filas[r] = [None] + [_f32(hA[i] / gA[i]) if gA[i] > 0 else None for i in range(1, L - 1)] + [None]
    P.recurrencia(P.V2S[j], guardar=(), rmax=max(R_A), cada_r=cada)
    _guardar(ruta, {str(r): filas[r] for r in R_A})
    return ruta


def calcular_v3(j):
    """Por tramo de la fase A y posición s (0, 1/2, 1), los umbrales (a1, a2, b1, b2) de V3 log."""
    ruta = _ruta("V3", j)
    if os.path.exists(ruta):
        return ruta
    t = P.dp(("V3", "log", j, R_A))["A"]
    i0, i1 = P.RANGO["A"]
    out = {}
    for r in R_A:
        out[str(r)] = [_niveles([t[r][i * 3 + s] for i in range(i0, i1)], i0) for s in range(3)]
    _guardar(ruta, out)
    return ruta


def calcular_v2(j):
    """Por fase (B, C, D) y tramo del motor, (alto, bajo, salida, bajo1) de V2 log."""
    ruta = _ruta("V2", j)
    if os.path.exists(ruta):
        return ruta
    t = P.dp(("V2", "log", j, R_M))
    out = {}
    for F in FASES_M:
        i0, i1 = P.RANGO[F]
        for r in R_M:
            u = [_intervalos([t[F][r][i * 2 + s] for i in range(i0, i1)], i0) for s in range(2)]
            out[f"{F},{r}"] = (u[0][0], u[0][1], u[1][0], u[1][1])
    _guardar(ruta, out)
    return ruta


def _trabajo(a):
    return {"pA": calcular_pa, "V3": calcular_v3, "V2": calcular_v2}[a[0]](a[1])


def calcular(jobs=None):
    falta = [(n, j) for n in ("V2", "V3", "pA") for j in range(CLASES) if not os.path.exists(_ruta(n, j))]
    if falta:
        with Pool(min(jobs or os.cpu_count(), len(falta))) as pool:
            for k, r in enumerate(pool.imap_unordered(_trabajo, falta), 1):
                print(f"  modelo: {k}/{len(falta)} ({os.path.basename(r)})", file=sys.stderr, flush=True)


def _leer(nombre, j):
    ruta = _ruta(nombre, j)
    if not os.path.exists(ruta):
        raise SystemExit(f"falta {ruta}: correr python3 ref/c1/tablas.py --calcular")
    with open(ruta) as f:
        return json.load(f)


def celdas():
    """(A, M): A[(j, tr)] = (ENT, SAL) y M[(F, j, tr)] = (BAJO, BAJO1), con los valores del modelo
    (256 y 99 marcan nivel vacío). Comprueba lo que el formato de la placa supone."""
    A, M = {}, {}
    for j in range(CLASES):
        pa, v3, v2 = _leer("pA", j), _leer("V3", j), _leer("V2", j)
        for tr, r in enumerate(R_A):
            a1_0, a1_1 = v3[str(r)][0][0], v3[str(r)][1][0]
            fila = pa[str(r)]
            ok = [p for p in range(LO + 1, HI) if p >= a1_0 and fila[p - LO] is not None and fila[p - LO] >= P_MIN]
            ent = min(ok) if ok else 256
            if ok and ok != list(range(ent, HI)):
                raise SystemExit(f"fase A, clase {j}, tramo {tr}: la entrada no es un solo umbral")
            A[(j, tr)] = (ent, a1_1)
        for F in FASES_M:
            for tr, r in enumerate(R_M):
                alto, bajo, salida, bajo1 = v2[f"{F},{r}"]
                if alto != 256 or salida != 256:
                    raise SystemExit(f"motor, fase {F}, clase {j}, tramo {tr}: alto o salida no están vacíos")
                M[(F, j, tr)] = (bajo, bajo1)
    return A, M


def _byte(v):
    """Nivel a un byte. 256 (nunca, en comparaciones p >= nivel) se guarda como 255: en la fase A el
    precio está entre 101 y 254. 99 (nunca, en p <= nivel) cabe tal cual."""
    if v == 256:
        return 255
    if not 99 <= v <= 255:
        raise SystemExit(f"nivel fuera de rango: {v}")
    return v


def palabras(parametros=None):
    """Las 512 palabras de 16 bits de la tabla de la placa."""
    A, M = celdas()
    T = [0] * PALABRAS
    par = dict(PARAMETROS)
    if parametros:
        par.update(parametros)
    for i, v in par.items():
        T[i] = v & 0xFFFF
    for d in range(16):
        T[T_CUAD64 + d] = 64 * d * d
    for j in range(7):
        T[T_N64 + j] = N64[j]
    for (j, tr), (ent, sal) in A.items():
        T[T_FASE_A + j * TRAMOS_A + tr] = _byte(ent) | (_byte(sal) << 8)
    for (F, j, tr), (bajo, bajo1) in M.items():
        T[T_MOTOR + FASES_M.index(F) * 64 + j * TRAMOS_M + tr] = _byte(bajo) | (_byte(bajo1) << 8)
    return T


def leer_hex(ruta):
    with open(ruta) as f:
        T = [int(x, 16) for x in f.read().split()]
    if len(T) != PALABRAS:
        raise SystemExit(f"{ruta}: {len(T)} palabras, se esperaban {PALABRAS}")
    return T


def escribir_hex(ruta, T):
    with open(ruta, "w") as f:
        f.write("".join(f"{v:04x}\n" for v in T))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--calcular", action="store_true")
    ap.add_argument("--jobs", type=int)
    ap.add_argument("--hex")
    ap.add_argument("--apagada", action="store_true", help="con --hex: la política apagada (palabra 4 en 0)")
    ap.add_argument("--check")
    ap.add_argument("--mostrar", action="store_true")
    a = ap.parse_args()
    if a.calcular:
        calcular(a.jobs)
    if a.hex:
        par = {}
        if a.apagada:
            par[T_POLITICA] = POLITICA_APAGADA
        escribir_hex(a.hex, palabras(par))
        print(f"{a.hex}: {PALABRAS} palabras")
    if a.check:
        T, R = leer_hex(a.check), palabras()
        mal = [i for i in range(PALABRAS) if T[i] != R[i] and i != T_POLITICA]
        if mal:
            raise SystemExit(f"FAIL: {a.check} difiere del modelo en {len(mal)} palabras (la primera, {mal[0]})")
        print(f"PASS: {a.check} coincide con el modelo en las celdas y en los parámetros (POLITICA = {T[T_POLITICA]})")
    if a.mostrar:
        A, M = celdas()
        for j in range(CLASES):
            print("A", j, [A[(j, tr)] for tr in range(TRAMOS_A)])
        for F in FASES_M:
            for j in range(CLASES):
                print(F, j, [M[(F, j, tr)] for tr in range(TRAMOS_M)])


if __name__ == "__main__":
    main()
