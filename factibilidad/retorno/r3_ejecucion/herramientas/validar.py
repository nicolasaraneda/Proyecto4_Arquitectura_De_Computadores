#!/usr/bin/env python3
"""validar.py: comprobaciones de la estrategia `ejec` antes de creerle a sus números.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    make validar

  1. `ejec` sin opciones decide lo mismo que `max_media`: patrimonio, órdenes
     y pérdida máxima iguales en cada serie.
  2. El espejo de la contabilidad (caja y acciones que lleva la estrategia)
     coincide con la cuenta oficial en todos los ticks, para las candidatas
     finales y para una variante de cada familia. Lo cuenta el contador
     aux[0] de la estrategia (ticks distintos).
  3. Control negativo del punto 2: con otra caja real el espejo debe fallar.
  4. Causalidad (comando `causal` del arnés): ninguna variante mira el futuro
     ni guarda estado entre rondas.
"""
import argparse
import os
import subprocess
import sys

LOTES = ["bloques_n2000", "practica_n20000", "remuestreo_s0_n2000", "modelo_s0_n2000", "modelo_vecino_s0_n2000",
         "dos_componentes_s0_n2000", "cambio_volatilidad_s0_n2000", "saltos_s0_n2000", "nivel_bajo_s0_n2000", "tendencia_s0_n2000",
         "borde_bajo_s0_n2000", "borde_alto_s0_n2000", "plana_s0_n2000", "remuestreo_s0_n20000", "modelo_s0_n20000",
         "cambio_volatilidad_s0_n20000", "volatil_s0_n20000"]
ESPEJO = ["ejec", "ejec:m=8", "ejec:m=12", "ejec:m=8,m2=24,e2=32", "ejec:mv=8", "ejec:K=2", "ejec:F=12", "ejec:eo=16", "ejec:ec=1,eo=16",
          "ejec:ea=0,eo=32", "ejec:xo=16", "ejec:xa=0,xo=16", "ejec:xc=1,xo=16", "ejec:nr=1", "ejec:nt=3"]


def correr(binario, *args, entorno=None):
    return subprocess.run([binario, *args], check=True, capture_output=True, text=True, env=entorno).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arnes", required=True)
    ap.add_argument("--series", required=True)
    a = ap.parse_args()
    fallas = 0

    print("Validacion de la estrategia ejec (ejecucion con contabilidad propia)")
    print("\n1. ejec sin opciones contra max_media: patrimonio, ordenes y perdida maxima de cada serie")
    n1 = d1 = 0
    for lote in LOTES:
        ruta = os.path.join(a.series, lote + ".bin")
        x = [l.split()[:3] for l in correr(a.arnes, "detalle", "--estrategia", "max_media", "--lote", ruta).splitlines()]
        y = [l.split()[:3] for l in correr(a.arnes, "detalle", "--estrategia", "ejec", "--lote", ruta).splitlines()]
        d1 += sum(1 for u, v in zip(x, y) if u != v) + abs(len(x) - len(y))
        n1 += len(x)
    print(f"  {len(LOTES)} lotes, {n1} series, {d1} distintas")
    fallas += d1

    print("\n2. Espejo de la contabilidad contra la cuenta oficial (ticks en que caja o acciones no coinciden)")
    total = 0
    for e in ESPEJO:
        series = malas = ticks = 0
        for lote in LOTES:
            ruta = os.path.join(a.series, lote + ".bin")
            largo = int(lote.rsplit("_n", 1)[1])
            for linea in correr(a.arnes, "detalle", "--estrategia", e, "--lote", ruta).splitlines():
                series += 1
                ticks += largo
                malas += int(linea.split()[3])
        print(f"  {e:26s} {series} series, {ticks} ticks, {malas} ticks distintos")
        total += malas
    fallas += total

    print("\n3. Control negativo: con otra caja real (--caja 9000) el espejo de ejec:m=8, que supone 10000, debe fallar")
    ruta = os.path.join(a.series, "remuestreo_s0_n2000.bin")
    malas = sum(int(l.split()[3]) > 0 for l in correr(a.arnes, "detalle", "--estrategia", "ejec:m=8", "--lote", ruta, "--caja", "9000").splitlines())
    print(f"  remuestreo_s0_n2000: {malas} de 5000 series con el espejo distinto")
    if malas < 4000:
        fallas += 1

    print("\n4. Causalidad")
    for e in ESPEJO + ["ejec:m=8,caja0=9000"]:
        salida = correr(a.arnes, "causal", "--estrategia", e)
        ok = "PASS" in salida.splitlines()[-1]
        print(f"  {e:26s} {salida.splitlines()[-1]}")
        fallas += 0 if ok else 1

    print(f"\n{'PASS' if fallas == 0 else 'FAIL'}: {fallas} fallas")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
