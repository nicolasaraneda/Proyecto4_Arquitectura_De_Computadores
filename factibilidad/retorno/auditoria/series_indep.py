#!/usr/bin/env python3
"""series_indep.py: comprobación independiente de las series guardadas del estudio de retorno.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Revisa build/series/ sin usar pruebas/validar_series.py:

  1. Cada archivo: cabecera, tamaño, cantidad de series y largo según su
     nombre, precios entre 1 y 255 y huella igual a la del manifiesto
     versionado (mediciones/series_manifiesto.txt).
  2. Bloques y serie completa: iguales a tb/practica.csv.
  3. Tres series de cada archivo regeneradas con ref/series.py: la última, la
     del medio más uno y una elegida al azar. Son índices distintos de los que
     usa la validación original, y caen en trozos distintos de la generación
     en paralelo.
  4. Semillas: ninguna serie repetida dentro de un archivo ni entre las
     semillas 0, 1 y 2 de una misma familia.
  5. Cronología de la semilla reservada: fecha de los fuentes que fijan
     candidatos, rivales, campos, umbrales y criterio, contra la fecha del
     primer resultado de la semilla 2. Es un indicio y no una prueba.

    python3 auditoria/series_indep.py            (desde factibilidad/retorno)
"""
import glob
import hashlib
import os
import random
import struct
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
RAIZ = os.path.dirname(os.path.dirname(RETORNO))
SERIES = os.path.join(RETORNO, "build", "series")

sys.path.insert(0, os.path.join(RAIZ, "ref"))
import series        # noqa: E402

CANTIDAD = {2000: {"remuestreo": 5000, "plausible": 2500, "estres": 1000, "degenerada": 200},
            20000: {"remuestreo": 4000, "plausible": 1000, "estres": 400, "degenerada": 50}}
DEGENERADAS = ("plana", "borde_bajo", "borde_alto")


def grupo(familia):
    if familia == "remuestreo":
        return "remuestreo"
    if familia in series.PLAUSIBLES:
        return "plausible"
    return "degenerada" if familia in DEGENERADAS else "estres"


def leer(ruta):
    with open(ruta, "rb") as f:
        datos = f.read()
    ns, n = struct.unpack("<ii", datos[:8])
    return ns, n, datos


def main():
    mal = 0
    manifiesto = {}
    with open(os.path.join(RETORNO, "mediciones", "series_manifiesto.txt")) as f:
        for linea in f:
            c = linea.split()
            if len(c) == 4 and not linea.startswith("#"):
                manifiesto[c[0]] = (int(c[1]), int(c[2]), c[3])
    archivos = sorted(glob.glob(os.path.join(SERIES, "*.bin")))
    print("Comprobacion independiente de las series guardadas")
    practica = series.practica()
    rng = random.Random(4242)
    total_series = regeneradas = distintas = fuera = mal_cabecera = mal_huella = 0
    huellas = {}                      # familia -> {largo -> {semilla -> conjunto de huellas de serie}}
    repetidas_dentro = 0
    for ruta in archivos:
        nombre = os.path.basename(ruta)
        ns, n, datos = leer(ruta)
        total_series += ns
        cuerpo = memoryview(datos)[8:]
        if len(datos) != 8 + ns * n or min(cuerpo) < 1:      # el máximo de un byte es 255 por construcción
            fuera += 1
        m = manifiesto.get(nombre)
        if not m or m[0] != ns or m[1] != n or m[2] != hashlib.sha256(datos).hexdigest()[:16]:
            mal_huella += 1
        base = nombre[:-4]
        if base == "bloques_n2000":
            esperado = b"".join(bytes(practica[i:i + 2000]) for i in range(0, 20000, 2000))
            ok = ns == 10 and n == 2000 and bytes(cuerpo) == esperado
            print(f"{'PASS' if ok else 'FAIL'}  bloques_n2000: los 10 tramos de 2000 ticks de tb/practica.csv, en orden")
            mal += not ok
            continue
        if base == "practica_n20000":
            ok = ns == 1 and n == 20000 and bytes(cuerpo) == bytes(practica)
            print(f"{'PASS' if ok else 'FAIL'}  practica_n20000: tb/practica.csv completa ({len(practica)} ticks, precio entre "
                  f"{min(practica)} y {max(practica)})")
            mal += not ok
            continue
        familia, resto = base.rsplit("_s", 1)
        semilla, largo = int(resto.split("_n")[0]), int(resto.split("_n")[1])
        if n != largo or ns != CANTIDAD[largo][grupo(familia)]:
            mal_cabecera += 1
        # huella de cada serie, para buscar repetidas
        hs = [hashlib.blake2b(cuerpo[i * n:(i + 1) * n], digest_size=8).digest() for i in range(ns)]
        if familia not in DEGENERADAS:
            repetidas_dentro += ns - len(set(hs))
            huellas.setdefault((familia, largo), {})[semilla] = set(hs)
        # regenerar tres series con ref/series.py
        base_rem = practica if familia == "remuestreo" else None
        for i in sorted({ns - 1, ns // 2 + 1, rng.randrange(ns)}):
            r = random.Random(series.semilla_de(familia, semilla, i))
            s = series.remuestreo(base_rem, n, r) if familia == "remuestreo" else series.FAMILIAS[familia](n, r)
            regeneradas += 1
            distintas += bytes(s) != bytes(cuerpo[i * n:(i + 1) * n])
    print(f"{'PASS' if not fuera else 'FAIL'}  {len(archivos)} archivos, {total_series} series: tamano segun la cabecera y precios entre 1 y 255 "
          f"({fuera} archivos con problemas)")
    print(f"{'PASS' if not mal_cabecera else 'FAIL'}  cantidad de series y largo segun el nombre de cada archivo ({mal_cabecera} distintos)")
    print(f"{'PASS' if not mal_huella else 'FAIL'}  huella sha256 igual a la de mediciones/series_manifiesto.txt ({mal_huella} distintas)")
    print(f"{'PASS' if not distintas else 'FAIL'}  {regeneradas} series regeneradas con ref/series.py (ultima, medio mas uno y una al azar de cada archivo): "
          f"{distintas} distintas")
    mal += fuera + mal_cabecera + mal_huella + distintas

    cruces = 0
    pares = 0
    for (familia, largo), por_semilla in sorted(huellas.items()):
        sems = sorted(por_semilla)
        for a in range(len(sems)):
            for b in range(a + 1, len(sems)):
                pares += 1
                cruces += len(por_semilla[sems[a]] & por_semilla[sems[b]])
    print(f"{'PASS' if not repetidas_dentro else 'FAIL'}  series repetidas dentro de un mismo archivo (sin contar las degeneradas): {repetidas_dentro}")
    print(f"{'PASS' if not cruces else 'FAIL'}  series repetidas entre semillas de una misma familia y largo: {cruces} en {pares} pares de archivos")
    mal += repetidas_dentro + cruces
    sem_por_largo = {}
    for (familia, largo), por_semilla in huellas.items():
        sem_por_largo.setdefault(largo, set()).update(por_semilla)
    print("Semillas generadas: " + "; ".join(f"{l} ticks: {sorted(s)}" for l, s in sorted(sem_por_largo.items())))

    # Cronología de la semilla reservada
    print("\nCronologia de la semilla reservada (2): fecha de modificacion de lo que fija el estudio y de sus resultados")
    def fecha(t):
        return time.strftime("%d/%m %H:%M:%S", time.localtime(t))
    fijan = ["nucleo/e_param.c", "nucleo/e_rivales.c", "nucleo/nucleo.c", "nucleo/nucleo.h", "nucleo/torneo.c", "nucleo/torneo.h",
             "nucleo/main.c", "pruebas/veredictos.py", "pruebas/tablas.py"]
    ultimo = 0
    for rel in fijan:
        t = os.path.getmtime(os.path.join(RETORNO, rel))
        ultimo = max(ultimo, t)
        print(f"  {rel:24s} {fecha(t)}")
    res = [os.path.getmtime(p) for p in glob.glob(os.path.join(RETORNO, "build", "resultados", "*_s2_*", "*.res"))]
    res0 = [os.path.getmtime(p) for p in glob.glob(os.path.join(RETORNO, "build", "resultados", "*_s0_*", "*.res"))]
    if res:
        print(f"  resultados de la semilla 0: {len(res0)} archivos, del {fecha(min(res0))} al {fecha(max(res0))}")
        print(f"  resultados de la semilla 2: {len(res)} archivos, del {fecha(min(res))} al {fecha(max(res))}")
        ok = min(res) > ultimo
        print(f"{'PASS' if ok else 'AVISO'}  el primer resultado guardado de la semilla 2 es {'posterior' if ok else 'anterior'} a la ultima "
              f"modificacion de los fuentes que fijan candidatos, rivales, campos, umbrales y criterio ({fecha(ultimo)})")
    else:
        print("  no hay resultados guardados de la semilla 2 en build/resultados")
    print("  (indicio, no prueba: las fechas no dicen que nadie haya mirado la semilla 2 antes por otra via)")
    print("PASS" if not mal else "FAIL")
    return 1 if mal else 0


if __name__ == "__main__":
    sys.exit(main())
