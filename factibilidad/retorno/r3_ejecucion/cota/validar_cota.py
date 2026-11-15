#!/usr/bin/env python3
"""validar_cota.py: la copia del núcleo de la cota da lo mismo que el arnés con el límite real de 63.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    make validar-cota

Compara, serie por serie, el arnés (núcleo sin tocar) con la copia de
cota/parche.sh:

  1. Candidatos del núcleo y una muestra de rivales de las seis clases, con el
     comando `detalle` (patrimonio, órdenes, pérdida máxima y contadores de
     cada serie) en lotes de los dos largos. Debe haber cero líneas distintas.
  2. `lim:L=63` de la copia contra `max_media` del arnés: es la misma regla
     con el límite real. Cero líneas distintas.
  3. Control negativo: `lim:L=126` debe ser distinto de `lim:L=63`. Si no, la
     copia no estaría aceptando órdenes anchas y la cota no mediría nada.
  4. El comando `veredicto` completo (torneo con los 61 rivales) de
     `max_media` contra `base`, texto idéntico en los dos binarios.
"""
import argparse
import os
import subprocess
import sys

LOTES = ["bloques_n2000", "practica_n20000", "remuestreo_s0_n2000", "modelo_s0_n2000", "dos_componentes_s0_n2000",
         "saltos_s0_n2000", "nivel_bajo_s0_n2000", "borde_bajo_s0_n2000", "borde_alto_s0_n2000", "remuestreo_s0_n20000",
         "cambio_volatilidad_s0_n20000", "tendencia_s0_n20000"]
CANDIDATOS = ["base", "max_media", "kalman", "activo", "guardia_tope", "prudente"]


def correr(binario, *args):
    return subprocess.run([binario, *args], check=True, capture_output=True, text=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arnes", required=True)
    ap.add_argument("--cota", required=True)
    ap.add_argument("--series", required=True)
    a = ap.parse_args()
    fallas = 0

    # una muestra de rivales: uno de cada cuatro de la lista, que cubre las seis clases
    rivales = []
    for linea in correr(a.arnes, "rivales").splitlines():
        partes = linea.split()
        if len(partes) >= 3 and "|" in linea and partes[0] != "clase":
            rivales.append((partes[0], partes[1]))
    muestra = [spec for i, (_, spec) in enumerate(rivales) if i % 4 == 0]
    clases = sorted({c for i, (c, _) in enumerate(rivales) if i % 4 == 0})
    print(f"Validacion de la copia del nucleo usada para la cota (limite por orden hipotetico)")
    print(f"Estrategias comparadas: {len(CANDIDATOS)} candidatos y {len(muestra)} rivales de las clases {', '.join(clases)}")

    print("\n1. Arnes contra copia, comando detalle, serie por serie")
    total_series = total_corridas = total_dif = 0
    for lote in LOTES:
        ruta = os.path.join(a.series, lote + ".bin")
        dif = series = 0
        for e in CANDIDATOS + muestra:
            x = correr(a.arnes, "detalle", "--estrategia", e, "--lote", ruta).splitlines()
            y = correr(a.cota, "detalle", "--estrategia", e, "--lote", ruta).splitlines()
            series = len(x)
            dif += sum(1 for u, v in zip(x, y) if u != v) + abs(len(x) - len(y))
            total_corridas += len(x)
        total_series += series
        total_dif += dif
        print(f"  {lote:32s} {series:5d} series x {len(CANDIDATOS) + len(muestra)} estrategias: {dif} lineas distintas")
    print(f"  total: {total_series} series, {total_corridas} corridas, {total_dif} distintas")
    fallas += total_dif

    print("\n2. lim:L=63 (copia) contra max_media (arnes): patrimonio, ordenes y perdida maxima de cada serie")
    dif2 = n2 = 0
    for lote in LOTES:
        ruta = os.path.join(a.series, lote + ".bin")
        x = [l.split()[:3] for l in correr(a.arnes, "detalle", "--estrategia", "max_media", "--lote", ruta).splitlines()]
        y = [l.split()[:3] for l in correr(a.cota, "detalle", "--estrategia", "lim:L=63", "--lote", ruta).splitlines()]
        d = sum(1 for u, v in zip(x, y) if u != v) + abs(len(x) - len(y))
        dif2 += d
        n2 += len(x)
    print(f"  {n2} series, {dif2} distintas")
    fallas += dif2

    print("\n3. Control negativo: lim:L=126 contra lim:L=63 en la copia (deben diferir)")
    ruta = os.path.join(a.series, "remuestreo_s0_n2000.bin")
    x = correr(a.cota, "detalle", "--estrategia", "lim:L=63", "--lote", ruta).splitlines()
    y = correr(a.cota, "detalle", "--estrategia", "lim:L=126", "--lote", ruta).splitlines()
    d = sum(1 for u, v in zip(x, y) if u != v)
    print(f"  remuestreo_s0_n2000: {d} de {len(x)} series distintas")
    if d < len(x) // 2:
        fallas += 1
    # y contra el núcleo real, que ignora los bits altos: lim:L=126 allí es 126 mod 64 = 62 acciones por orden
    z = correr(a.arnes, "listar")
    print(f"  (el arnes real no conoce la estrategia lim: {'lim ' not in z})")

    print("\n4. Comando veredicto completo, max_media contra base, semilla 0, texto de los dos binarios")
    for largo in ("2000", "20000"):
        x = correr(a.arnes, "veredicto", "--candidata", "max_media", "--referencia", "base", "--semilla", "0", "--largo", largo, "--parada")
        y = correr(a.cota, "veredicto", "--candidata", "max_media", "--referencia", "base", "--semilla", "0", "--largo", largo, "--parada")
        igual = x == y
        print(f"  {largo} ticks: {len(x.splitlines())} lineas, {'identico' if igual else 'DISTINTO'}")
        fallas += 0 if igual else 1

    print(f"\n{'PASS' if fallas == 0 else 'FAIL'}: {fallas} diferencias")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
