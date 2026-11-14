#!/usr/bin/env python3
"""rivales_indep.py: segunda implementación de los rivales y de la regla de reversión, contra el arnés.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El evaluador independiente (auditoria/indep.c) reescribe las seis clases de
rivales (cruce de medias, momentum, comprar y mantener, no operar, reversión y
azar), la forma de dimensionar la orden y la regla de reversión de los
candidatos, con otra contabilidad y otro lazo. Aquí se comparan, serie por
serie, su patrimonio final y su número de órdenes con los del comando
`detalle` del arnés.

Los rivales de azar usan otro generador de números al azar, así que no pueden
coincidir serie por serie: se compara la media del patrimonio y de las órdenes
sobre muchas series.

    python3 auditoria/rivales_indep.py            (desde factibilidad/retorno)
"""
import math
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
ARNES = os.path.join(RETORNO, "build", "retorno")
INDEP = os.path.join(RETORNO, "build", "auditoria", "indep")
SERIES = os.path.join(RETORNO, "build", "series")

ARCHIVOS = ["bloques_n2000", "practica_n20000", "remuestreo_s0_n2000", "modelo_vecino_s2_n2000", "tendencia_s0_n2000",
            "cambio_de_caracter_s2_n2000", "nivel_bajo_s0_n2000", "volatil_s2_n2000", "plana_s0_n2000",
            "borde_bajo_s0_n2000", "borde_alto_s2_n2000", "saltos_s0_n20000", "dos_componentes_s0_n20000",
            "remuestreo_s2_n20000"]


def propio(archivo):
    """{regla: [(patrimonio, ordenes), ...]} con el evaluador independiente."""
    r = subprocess.run([INDEP, "detalle-todos", os.path.join(SERIES, archivo + ".bin")], capture_output=True, text=True,
                       check=True, cwd=RETORNO)
    salida, actual = {}, None
    for linea in r.stdout.splitlines():
        if linea.startswith("# "):
            actual = salida.setdefault(linea[2:], [])
        else:
            w, o = linea.split()
            actual.append((int(w), int(o)))
    return salida


def arnes(spec, archivo):
    r = subprocess.run([ARNES, "detalle", "--estrategia", spec, "--lote", os.path.join(SERIES, archivo + ".bin")],
                       capture_output=True, text=True, check=True, cwd=RETORNO)
    return [(int(x.split()[0]), int(x.split()[1])) for x in r.stdout.splitlines()]


def media_ee(x):
    n = len(x)
    m = sum(x) / n
    return m, (math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1) / n) if n > 1 else 0.0)


def main():
    clases = {}
    with open(os.path.join(RETORNO, "mediciones", "rivales.txt")) as f:
        for linea in f:
            c = linea.split()
            if len(c) >= 2 and c[0] in ("cruce", "momentum", "comprar_y_mantener", "no_operar", "reversion", "azar"):
                clases[c[1]] = c[0]
    series = corridas = distintas = 0
    por_clase = {}
    azar = {}
    for archivo in ARCHIVOS:
        mio = propio(archivo)
        ns = len(next(iter(mio.values())))
        series += ns
        for spec, filas in mio.items():
            suyo = arnes(spec, archivo)
            clase = clases.get(spec, "candidatos (regla de reversion)")
            if spec.startswith("azar"):
                azar.setdefault(spec, []).append((archivo, filas, suyo))
                continue
            dif = sum(1 for a, b in zip(filas, suyo) if a != b) + abs(len(filas) - len(suyo))
            t = por_clase.setdefault(clase, [0, 0, 0])
            t[0] += 1 if archivo == ARCHIVOS[0] else 0
            t[1] += len(filas)
            t[2] += dif
            corridas += len(filas)
            distintas += dif
            if dif:
                k = next(i for i, (a, b) in enumerate(zip(filas, suyo)) if a != b)
                print(f"  DISTINTO {spec} en {archivo}, serie {k}: propio {filas[k]}, arnes {suyo[k]}")
    print("Rivales y regla de reversion: implementacion independiente contra el arnes, serie por serie")
    print(f"Archivos: {len(ARCHIVOS)} ({series} series): " + ", ".join(ARCHIVOS))
    print(f"{'clase':34s} {'reglas':>6s} {'corridas':>9s} {'distintas':>9s}")
    for clase, (n, c, d) in por_clase.items():
        print(f"{clase:34s} {n:6d} {c:9d} {d:9d}")
    print(f"{'PASS' if not distintas else 'FAIL'}  reglas deterministas: {corridas} corridas comparadas (patrimonio y ordenes), {distintas} distintas")

    # Azar: otra secuencia de números al azar, se compara la distribución
    print("\nRivales de azar (otro generador): media del patrimonio y de las ordenes por serie, propio contra arnes")
    print(f"{'rival':22s} {'archivo':26s} {'patrimonio propio':>18s} {'arnes':>9s} {'z':>6s} {'ordenes propio':>15s} {'arnes':>8s} {'z':>6s}")
    peor = 0.0
    for spec, casos in azar.items():
        for archivo, filas, suyo in casos:
            if len(filas) < 1000:
                continue
            mw, ew = media_ee([a[0] for a in filas])
            sw, fw = media_ee([a[0] for a in suyo])
            mo, eo = media_ee([a[1] for a in filas])
            so, fo = media_ee([a[1] for a in suyo])
            zw = (mw - sw) / math.hypot(ew, fw) if ew + fw > 0 else 0.0
            zo = (mo - so) / math.hypot(eo, fo) if eo + fo > 0 else 0.0
            peor = max(peor, abs(zw), abs(zo))
            print(f"{spec:22s} {archivo:26s} {mw:18.1f} {sw:9.1f} {zw:+6.2f} {mo:15.2f} {so:8.2f} {zo:+6.2f}")
    ok = peor < 4.0
    print(f"{'PASS' if ok else 'FAIL'}  azar: la mayor diferencia entre medias es {peor:.2f} errores estandar combinados (limite 4)")
    return 0 if ok and not distintas else 1


if __name__ == "__main__":
    sys.exit(main())
