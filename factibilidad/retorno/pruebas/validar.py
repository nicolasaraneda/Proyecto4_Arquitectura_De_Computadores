#!/usr/bin/env python3
"""validar.py: validación del arnés de retorno contra las referencias del repositorio.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 factibilidad/retorno/pruebas/validar.py      (o make validar)

Qué comprueba, siempre exigiendo cero diferencias:

  1. Mercado. La contabilidad del arnés contra ref/market.py con flujos de
     órdenes al azar: todas las acciones (incluida la 11), cantidades de 0 a
     63, precios de 1 a 255 y distintas cajas y comisiones. Fila por fila.
  2. Números conocidos. Regla base 27 062 con 388 órdenes, comprar y mantener
     6 497, media 11 069 en los 10 bloques, 26 795 con los dos precios que se
     pierden en el testbench y 24 143 con la suma móvil de 64.
  3. decisiones.csv. El archivo que escribe el arnés para la regla base es
     idéntico byte a byte al de ref/trader.py.
  4. Motor. La familia paramétrica del arnés contra ref/motor/motor.c, serie
     por serie, para todos los candidatos y 60 combinaciones al azar, en todos
     los lotes de la semilla 0 a 2000 y a 20 000 ticks.
  5. Referencia en Python. Contra ref/trader.py (regla base) y
     ref/candidatos.py (clase Trader), serie por serie, en los bloques, la
     serie completa y una muestra de cada lote a los dos largos.
  6. Rivales. La reversión simple con k=5, a=4, b=0 es la regla base, y la de
     suma móvil coincide con la SumaMovil de ref/protocolo.py.
  7. Frontera anterior. Las cifras de docs/mediciones/frontera.txt (semillas
     0 y 1, 2000 ticks) salen iguales con el arnés.

No usa la semilla 2 (reservada) en nada que compare estrategias: solo se
tocaría para validar aritmética, y no hace falta.
"""
import os
import random
import re
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
RAIZ = os.path.dirname(os.path.dirname(RETORNO))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
sys.path.insert(0, RETORNO)

import candidatos           # noqa: E402
import market               # noqa: E402
import protocolo            # noqa: E402
import series               # noqa: E402
import trader               # noqa: E402
import generar_series       # noqa: E402

ARNES = os.path.join(RETORNO, "build", "retorno")
MOTOR = os.path.join(RETORNO, "build", "motor")
SERIES = os.path.join(RETORNO, "build", "series")
PRACTICA = os.path.join(RAIZ, "tb", "practica.csv")
FRONTERA = os.path.join(RAIZ, "docs", "mediciones", "frontera.txt")

EXTRA = {
    "kalman_base": dict(est=1, E=250, X=-40),
    "activo": dict(E=64, X=16),
    "base_guardia": dict(E=128, X=0, **candidatos.SALTOS, **candidatos.GUARDIA),
    "base_tope": dict(E=128, X=0, **candidatos.PROTECCION),
    "base_fuerte": dict(E=128, X=0, **candidatos.PROTECCION_FUERTE),
    "prud_guardia": dict(E=192, X=-32, **candidatos.SALTOS, **candidatos.GUARDIA),
    "guardia_tope_r": dict(E=96, X=0, **candidatos.PROTECCION, capoff=2000),
    "base_tope_r": dict(E=128, X=0, **candidatos.PROTECCION, capoff=2000),
}
TODOS = {n: v[0] for n, v in candidatos.CANDIDATOS.items()}
TODOS.update(EXTRA)

fallas = 0


def informar(nombre, ok, detalle):
    global fallas
    fallas += 0 if ok else 1
    print(f"{'PASS' if ok else 'FAIL'}  {nombre}: {detalle}", flush=True)


def arnes(*args, entrada=None):
    return subprocess.run([ARNES, *map(str, args)], input=entrada, check=True, capture_output=True, text=True).stdout


def spec_de(par):
    return "param:" + ",".join(f"{k}={v}" for k, v in par.items()) if par else "param"


def leer_lote(nombre, cuantas=None):
    with open(os.path.join(SERIES, nombre), "rb") as f:
        import struct
        ns, n = struct.unpack("<ii", f.read(8))
        ns = ns if cuantas is None else min(ns, cuantas)
        datos = f.read(ns * n)
    return [list(datos[i * n:(i + 1) * n]) for i in range(ns)]


# ---- 1. Mercado -------------------------------------------------------------------------

def prueba_mercado():
    rng = random.Random(2026)
    lineas, esperado = [], []
    flujos = ticks = ejecutadas = 0
    for flujo in range(400):
        caja0 = rng.choice([10000, 10000, 1000, 2500, 50000, 100000, 37, 6])
        comision = rng.choice([5, 5, 0, 1, 20, 50])
        estilo = flujo % 4
        nivel = rng.choice([1, 2, 3, 40, 128, 250, 255])
        m = market.Mercado(caja0, comision)
        lineas.append(f"R {caja0} {comision}")
        for _ in range(rng.choice([50, 400, 2000])):
            if estilo == 0:                                      # todo al azar
                p, d = rng.randint(1, 255), rng.randint(0, 255)
            elif estilo == 1:                                    # paseo con órdenes grandes
                nivel = min(255, max(1, nivel + rng.choice([-2, -1, 0, 0, 1, 2])))
                p, d = nivel, rng.choice([0x7F, 0xBF, 0x00, 0xFF, 0x40, 0x80, 0x41, 0x81])
            elif estilo == 2:                                    # precios en los bordes
                p, d = rng.choice([1, 1, 2, 254, 255, 255]), rng.randint(0, 255)
            else:                                                # órdenes chicas repetidas
                nivel = min(255, max(1, nivel + rng.choice([-1, 0, 1])))
                p, d = nivel, rng.choice([0x4A, 0x8A, 0x45, 0x85, 0x00, 0xC5])
            antes = m.ordenes
            m.ejecutar(d, p)
            ejecutadas += m.ordenes - antes
            lineas.append(f"{p} {d}")
            esperado.append(f"{m.caja} {m.acciones} {m.w} {m.ordenes} {m.max_dd}")
            ticks += 1
        flujos += 1
    salida = arnes("mercado", entrada="\n".join(lineas) + "\n").splitlines()
    distintas = sum(a != b for a, b in zip(salida, esperado)) + abs(len(salida) - len(esperado))
    informar("mercado contra ref/market.py", distintas == 0,
             f"{flujos} flujos, {ticks} ticks, {ejecutadas} ordenes ejecutadas, {distintas} filas distintas")


# ---- 2 y 3. Números conocidos y decisiones.csv --------------------------------------------

def campo(texto, nombre):
    return int(re.search(nombre + r" (-?\d+)", texto).group(1))


def prueba_conocidos():
    s = arnes("correr", "--estrategia", "base", "--serie", PRACTICA)
    ok = campo(s, "patrimonio") == 27062 and campo(s, "ordenes") == 388 and campo(s, "comprar_y_mantener") == 6497
    informar("regla base en la serie completa", ok,
             f"patrimonio {campo(s, 'patrimonio')} (27062), ordenes {campo(s, 'ordenes')} (388), "
             f"comprar y mantener {campo(s, 'comprar_y_mantener')} (6497)")
    fila = arnes("resumen", "--conjunto", "bloques", "--largo", 2000, "--estrategia", "base").splitlines()[1].split()
    informar("regla base en los 10 bloques", round(float(fila[2])) == 11069 and int(fila[7]) == 9720,
             f"media {float(fila[2]):.1f} (11069), peor {fila[7]} (9720)")
    s = arnes("correr", "--estrategia", "base", "--serie", PRACTICA, "--perdidos", 2)
    informar("regla base con los 2 precios perdidos del testbench", campo(s, "patrimonio") == 26795,
             f"patrimonio {campo(s, 'patrimonio')} (26795)")
    s = arnes("correr", "--estrategia", "reversion:tipo=1,n=64,a=4,b=1", "--serie", PRACTICA)
    informar("suma movil de 64, entra 4, sale 1", campo(s, "patrimonio") == 24143, f"patrimonio {campo(s, 'patrimonio')} (24143)")

    precios = market.leer_serie(PRACTICA)
    with tempfile.TemporaryDirectory() as tmp:
        distintos = 0
        for perdidos in (0, 1, 2):
            filas = []
            trader.correr(precios, perdidos=perdidos, filas=filas)
            ref = os.path.join(tmp, "ref.csv")
            market.escribir_csv(ref, filas)
            mio = os.path.join(tmp, "arnes.csv")
            arnes("correr", "--estrategia", "base", "--serie", PRACTICA, "--perdidos", perdidos, "-o", mio)
            with open(ref, "rb") as a, open(mio, "rb") as b:
                distintos += a.read() != b.read()
        informar("decisiones.csv contra ref/trader.py", distintos == 0,
                 f"20000 filas con 0, 1 y 2 precios perdidos: {distintos} archivos distintos")


# ---- 4. Motor ---------------------------------------------------------------------------------

def linea_motor(par):
    return " ".join(f"{k}={v}" for k, v in par.items()) or "k=5"


def prueba_motor():
    sys.path.insert(0, os.path.join(RAIZ, "ref"))
    import test_candidatos
    rng = random.Random(7)
    configs = list(TODOS.items()) + [(f"azar{i}", test_candidatos.configuracion_al_azar(rng)) for i in range(60)]
    lotes = sorted(f for f in os.listdir(SERIES) if f.endswith(".bin") and ("_s0_" in f or f.startswith(("bloques", "practica"))))
    series_total = comparadas = distintas = 0
    for lote in lotes:
        ruta = os.path.join(SERIES, lote)
        # el motor lee todas las configuraciones de una vez
        entrada = "\n".join(linea_motor(par) for _, par in configs) + "\n"
        ref = subprocess.run([MOTOR, ruta, "--detalle"], input=entrada, check=True, capture_output=True, text=True).stdout.splitlines()
        ns = len(ref) // len(configs)
        series_total += ns
        for k, (_, par) in enumerate(configs):
            mio = arnes("detalle", "--lote", ruta, "--estrategia", spec_de(par)).splitlines()
            for a, b in zip(mio, ref[k * ns:(k + 1) * ns]):
                x, y = a.split(), b.split()
                # arnés: w ordenes max_dd veto cortes topes pausas byh. motor: w ordenes max_dd veto cortes topes
                distintas += x[:6] != y[:6]
                comparadas += 1
    informar("familia parametrica contra ref/motor/motor.c", distintas == 0,
             f"{len(configs)} configuraciones ({len(TODOS)} candidatos y 60 al azar), {len(lotes)} lotes, "
             f"{series_total} series, {comparadas} corridas comparadas, {distintas} distintas")


# ---- 5. Referencia en Python --------------------------------------------------------------------

def correr_python(par, precios):
    t = candidatos.Trader(**par)
    m = trader.correr(precios, t)
    return [m.w, m.ordenes, m.max_dd, t.ticks_veto, t.cortes, t.topes, t.pausas]


def prueba_python():
    muestras = [("bloques_n2000.bin", None), ("practica_n20000.bin", None)]
    for plan in generar_series.plan(semillas=[0]):
        archivo, _, _, n, _ = plan
        muestras.append((archivo, 25 if n == 2000 else 3))
    comparadas = distintas = series_n = 0
    for archivo, cuantas in muestras:
        lista = leer_lote(archivo, cuantas)
        series_n += len(lista)
        ruta = os.path.join(SERIES, archivo)
        for nombre, par in TODOS.items():
            mio = [list(map(int, l.split()))[:7] for l in arnes("detalle", "--lote", ruta, "--estrategia", "cand:" + nombre).splitlines()]
            for s, fila in zip(lista, mio):
                distintas += correr_python(par, s) != fila
                comparadas += 1
        # la regla base además contra ref/trader.py, que es la referencia oficial
        mio = [list(map(int, l.split()))[:3] for l in arnes("detalle", "--lote", ruta, "--estrategia", "cand:base").splitlines()]
        for s, fila in zip(lista, mio):
            m = trader.correr(s)
            distintas += [m.w, m.ordenes, m.max_dd] != fila
            comparadas += 1
    informar("candidatos contra ref/candidatos.py y ref/trader.py", distintas == 0,
             f"{len(TODOS)} candidatos, {series_n} series de {len(muestras)} lotes (2000 y 20000 ticks), "
             f"{comparadas} corridas comparadas, {distintas} distintas")


# ---- 6. Rivales ------------------------------------------------------------------------------------

def prueba_rivales():
    distintas = comparadas = 0
    for archivo in ("bloques_n2000.bin", "remuestreo_s0_n2000.bin", "tendencia_s0_n2000.bin", "nivel_bajo_s0_n2000.bin",
                    "borde_bajo_s0_n2000.bin", "remuestreo_s0_n20000.bin"):
        ruta = os.path.join(SERIES, archivo)
        a = [l.split()[:3] for l in arnes("detalle", "--lote", ruta, "--estrategia", "reversion:k=5,a=4,b=0,q=63,rep=1").splitlines()]
        b = [l.split()[:3] for l in arnes("detalle", "--lote", ruta, "--estrategia", "cand:base").splitlines()]
        distintas += sum(x != y for x, y in zip(a, b))
        comparadas += len(a)
    informar("rival reversion k=5 a=4 b=0 igual a la regla base", distintas == 0, f"{comparadas} series, {distintas} distintas")

    distintas = comparadas = 0
    for archivo, cuantas in (("bloques_n2000.bin", None), ("remuestreo_s0_n2000.bin", 40), ("saltos_s0_n2000.bin", 40),
                             ("practica_n20000.bin", None)):
        lista = leer_lote(archivo, cuantas)
        mio = [list(map(int, l.split()))[:3] for l in arnes("detalle", "--lote", os.path.join(SERIES, archivo), "--estrategia",
                                                           "reversion:tipo=1,n=64,a=4,b=1").splitlines()]
        for s, fila in zip(lista, mio):
            m = trader.correr(s, protocolo.SumaMovil(64, 4, 1))
            distintas += [m.w, m.ordenes, m.max_dd] != fila
            comparadas += 1
        mio = [list(map(int, l.split()))[:3] for l in arnes("detalle", "--lote", os.path.join(SERIES, archivo), "--estrategia",
                                                           "byh:q=63,rep=1").splitlines()]
        for s, fila in zip(lista, mio):
            m = trader.correr(s, protocolo.Comprar63())
            distintas += [m.w, m.ordenes, m.max_dd] != fila
            comparadas += 1
        mio = [l.split() for l in arnes("detalle", "--lote", os.path.join(SERIES, archivo), "--estrategia", "nada").splitlines()]
        for s, fila in zip(lista, mio):
            distintas += int(fila[0]) != 10000 or int(fila[7]) != market.comprar_y_mantener(s)
            comparadas += 1
    informar("rivales de suma movil, comprar 63 y no operar contra ref/protocolo.py", distintas == 0,
             f"{comparadas} corridas, {distintas} distintas")


# ---- 7. Frontera anterior ----------------------------------------------------------------------------

def leer_frontera():
    """{semilla: {candidato: [celdas de bloques, remuestreo, plausibles, estres, act]}} de docs/mediciones/frontera.txt."""
    tablas, semilla = {}, None
    with open(FRONTERA) as f:
        for linea in f:
            m = re.match(r"=== Semilla (\d)", linea)
            if m:
                semilla = int(m.group(1))
                tablas[semilla] = {}
                continue
            if linea.startswith("Familias"):
                semilla = None
            partes = linea.rstrip("\n").split("|")
            if semilla is not None and len(partes) == 6 and partes[0].strip() and partes[0].strip() != "candidato":
                tablas[semilla][partes[0].strip()] = [p.split() for p in partes[1:]]
    return tablas


def prueba_frontera():
    tablas = leer_frontera()
    celdas = distintas = 0
    ejemplos = []
    for semilla, tabla in tablas.items():
        nombres = list(tabla)
        mio = {}
        for conjunto in ("bloques", "remuestreo", "plausibles", "estres"):
            salida = arnes("resumen", "--conjunto", conjunto, "--largo", 2000, "--semilla", semilla, "--estrategia", ",".join(nombres))
            for linea in salida.splitlines()[1:]:
                c = linea.split()
                mio[(c[0], conjunto)] = dict(media=float(c[2]), dif=float(c[3]), ee=float(c[4]), p5=float(c[6]), peor=float(c[7]),
                                             byh=float(c[9]), act=float(c[11]))
        for nombre, (blo, rem, pla, est, act) in tabla.items():
            b = mio[(nombre, "bloques")]
            pares = [(blo[0], f"{b['media']:.0f}"), (blo[1], f"{b['dif']:+.0f}"), (blo[2], f"{b['peor']:.0f}")]
            for celda, conjunto in ((rem, "remuestreo"), (pla, "plausibles"), (est, "estres")):
                x = mio[(nombre, conjunto)]
                pares += [(celda[0], f"{x['media']:.0f}"), (celda[1], f"{x['dif']:+.0f}"), (celda[2], f"{x['ee']:.0f}"),
                          (celda[3], f"{x['p5']:.0f}"), (celda[4], f"{x['peor']:.0f}"), (celda[5], f"{100 * x['byh']:.0f}%")]
            pares += [(act[0], f"{100 * mio[(nombre, 'remuestreo')]['act']:.0f}%"), (act[1], f"{100 * mio[(nombre, 'plausibles')]['act']:.0f}%")]
            for esperado, obtenido in pares:
                celdas += 1
                if esperado != obtenido and not (esperado in ("+0", "-0") and obtenido in ("+0", "-0")):
                    distintas += 1
                    ejemplos.append(f"semilla {semilla} {nombre}: {esperado} / {obtenido}")
    informar("frontera anterior (docs/mediciones/frontera.txt)", distintas == 0 and celdas > 0,
             f"semillas {sorted(tablas)}, {celdas} cifras comparadas, {distintas} distintas" + ("".join("\n      " + e for e in ejemplos[:8])))


def main():
    print("Validacion del arnes de retorno")
    prueba_mercado()
    prueba_conocidos()
    prueba_motor()
    prueba_python()
    prueba_rivales()
    prueba_frontera()
    print("PASS: el arnes coincide con todas las referencias" if fallas == 0 else f"FAIL: {fallas} pruebas con diferencias")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
