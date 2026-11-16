#!/usr/bin/env python3
"""aritmetica.py: qué operaciones usa cada candidata final y con qué frecuencia.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Dos partes:

1. Lectura del código. Lista cada línea de las rutinas `decidir` (y de las que
   llaman) de las candidatas finales en que aparece un producto, un cociente,
   un resto o un tipo de punto flotante o de 64 bits. Es una ayuda para la
   revisión a mano: la clasificación de cada línea (producto por constante,
   producto de precio por cantidad, cociente acotado) está en el README.

2. Corrida. Con los contadores que las estrategias ya llevan (comando
   `detalle` del arnés), cuántas veces por ronda aparece cada operación cara:
   cocientes y productos del espejo de `ejec`, compras suprimidas, ticks con
   objetivo parcial del fondo, y el patrimonio más grande que se ve (para
   saber si las cuentas caben en 32 bits).

    python3 aritmetica.py            (desde factibilidad/retorno/auditoria_r34)
"""
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RETORNO = os.path.dirname(AQUI)
ARNES = os.path.join(AQUI, "build", "arnes")
SERIES = os.path.join(RETORNO, "build", "series")

FUENTES = [
    ("ejec_a (ejec:m=8)", "r3_ejecucion/ejec.c", ["espejo", "decidir"]),
    ("gestores max_media, base, activo y kalman (param)", "nucleo/e_param.c", ["decidir"]),
    ("aprendiz (tabla:ka=12,h=16)", "r4c_aprendizaje/e_tabla.c", ["tabla_iniciar", "decidir"]),
    ("supervisor del fondo (fondoc)", "r4_final/fondoc.c", ["desempeno", "supera", "decidir"]),
    ("contabilidad que el supervisor usa como espejo (cuenta_ejecutar)", "nucleo/nucleo.c", ["cuenta_ejecutar"]),
]


def sin_comentarios(texto):
    texto = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), texto, flags=re.S)
    texto = re.sub(r'"(\\.|[^"\\])*"', '""', texto)
    return texto


def cuerpo(lineas, nombre):
    """(primera, última) línea, base 1, de la función `nombre`."""
    for i, l in enumerate(lineas):
        if re.match(rf"^(static\s+)?(inline\s+)?[\w\s\*]+\b{nombre}\s*\(", l) and not l.rstrip().endswith(";"):
            nivel = 0
            abierto = False
            for j in range(i, len(lineas)):
                nivel += lineas[j].count("{") - lineas[j].count("}")
                abierto = abierto or "{" in lineas[j]
                if abierto and nivel == 0:
                    return i + 1, j + 1
    return None


def leer_codigo():
    print("1. Productos, cocientes, restos y tipos anchos en las rutinas de decision")
    print("   (lineas con ' * ', ' / ', ' % ', long long, double o float; sin comentarios)")
    total = 0
    for titulo, ruta, funciones in FUENTES:
        texto = sin_comentarios(open(os.path.join(RETORNO, ruta)).read())
        lineas = texto.split("\n")
        print(f"\n   {titulo}: {ruta}")
        for fn in funciones:
            rango = cuerpo(lineas, fn)
            if not rango:
                print(f"     {fn}: no se encontro")
                continue
            hallados = 0
            for n in range(rango[0], rango[1] + 1):
                l = lineas[n - 1]
                marcas = []
                if re.search(r"[\w\)\]] \* [\w\(\-]", l):
                    marcas.append("producto")
                if re.search(r"[\w\)\]] / [\w\(]", l):
                    marcas.append("cociente")
                if re.search(r"[\w\)\]] % [\w\(]", l):
                    marcas.append("resto")
                if re.search(r"\blong long\b|\bdouble\b|\bfloat\b", l):
                    marcas.append("tipo ancho")
                if marcas:
                    hallados += 1
                    total += 1
                    print(f"     {fn}:{n:4d}  [{', '.join(marcas):22s}] {l.strip()[:150]}")
            if not hallados:
                print(f"     {fn}: ninguna")
    print(f"\n   {total} lineas en total")


def detalle(spec, archivo, extra=()):
    env = dict(os.environ)
    env.setdefault("HILOS", "5")
    r = subprocess.run([ARNES, "detalle", "--estrategia", spec, "--lote", os.path.join(SERIES, archivo + ".bin"), *extra],
                       capture_output=True, text=True, cwd=RETORNO, env=env, check=True)
    return [[int(x) for x in l.split()] for l in r.stdout.splitlines() if l.strip()]


def evidencia(spec, largo, semilla=0):
    """Filas de `detalle` del conjunto evidencia: todo el remuestreo y la misma cantidad de plausibles."""
    rem = detalle(spec, f"remuestreo_s{semilla}_n{largo}")
    filas = list(rem)
    for fam in ("modelo", "modelo_vecino", "dos_componentes", "cambio_volatilidad"):
        filas += detalle(spec, f"{fam}_s{semilla}_n{largo}")[: len(rem) // 4]
    return filas


def media(filas, col):
    return sum(f[col] for f in filas) / len(filas)


def correr():
    print("\n2. Frecuencia de las operaciones caras, conjunto evidencia, semilla 0 (comando detalle del arnes)")
    print("   Columnas de detalle: patrimonio, ordenes, perdida maxima, aux0..aux3, comprar y mantener.")
    for largo in (2000, 20000):
        print(f"\n   Rondas de {largo} ticks")
        for nombre, spec in (("ejec_a", "ejec:m=8"), ("ejec_b", "ejec:m=8,m2=24,e2=32")):
            f = evidencia(spec, largo)
            n = len(f)
            # aux0: ticks con el espejo distinto; aux1: cocientes; aux2: productos que no son por 63; aux3: compras suprimidas
            div, mul, sup, dif = media(f, 4), media(f, 5), media(f, 6), sum(x[3] for x in f)
            print(f"     {nombre:13s} {n} series: ordenes {media(f, 1):7.1f}; cocientes {div:6.2f} por ronda ({100 * div / largo:.2f} % de los ticks); "
                  f"productos de resto {mul:6.2f} ({100 * mul / largo:.2f} %); compras suprimidas {sup:5.2f}; ticks con el espejo distinto {dif}")
        for nombre, spec in (("fondo_rec", "cand:fondo_rec"), ("rec_e", "cand:rec_e"), ("completo", "cand:completo"), ("completo_min", "cand:completo_min"),
                             ("fondo_min", "cand:fondo_min")):
            f = evidencia(spec, largo)
            n = len(f)
            # aux0: cambios de pesos; aux1: peso final del gestor 0; aux2: ticks con el espejo distinto; aux3: ticks con objetivo parcial
            par = media(f, 6)
            print(f"     {nombre:13s} {n} series: ordenes {media(f, 1):7.1f}; ticks con objetivo parcial {par:8.1f} por ronda ({100 * par / largo:5.2f} %); "
                  f"cambios de pesos {media(f, 3):5.2f}; ticks con el espejo distinto {sum(x[5] for x in f)}")
    print("\n   Patrimonio final mas grande, todas las series de la evidencia de 20 000 ticks (para las cuentas en 32 bits)")
    for nombre, spec in (("max_media", "cand:max_media"), ("ejec_a", "ejec:m=8"), ("completo", "cand:completo"), ("completo_min", "cand:completo_min")):
        f = evidencia(spec, 20000)
        mayor = max(x[0] for x in f)
        sobre27 = sum(1 for x in f if x[0] >= 2 ** 27)
        sobre24 = sum(1 for x in f if x[0] >= 2 ** 24)
        print(f"     {nombre:13s} maximo {mayor:12d}; series con patrimonio final de 2^24 o mas: {sobre24} de {len(f)}; de 2^27 o mas: {sobre27}")


def main():
    leer_codigo()
    correr()
    print("\nLISTO: lectura del codigo y frecuencias medidas. La clasificacion de cada linea esta en el README.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
