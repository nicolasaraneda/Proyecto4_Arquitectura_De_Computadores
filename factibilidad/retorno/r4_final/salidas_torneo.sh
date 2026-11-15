#!/bin/sh
# salidas_torneo.sh: salidas del arnés que no deben cambiar al agregar campos de rivales.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso: sh salidas_torneo.sh BINARIO CARPETA_DE_SALIDA
#
# Corre con BINARIO una lista fija de comandos (rivales, hipotesis y veredicto,
# con estrategias del núcleo y de afuera, en los tres campos originales) y deja
# cada salida en CARPETA_DE_SALIDA. Se corre con el binario compilado con el
# torneo.c anterior y con el nuevo, y las dos carpetas se comparan byte a byte
# (objetivo `sin-cambios` del Makefile).
set -e
BIN=$1
OUT=$2
mkdir -p "$OUT"
"$BIN" rivales > "$OUT/rivales.txt"
"$BIN" hipotesis --largo 2000 --semilla 0 --tsv "$OUT/hipotesis_n2000.tsv.txt" > "$OUT/hipotesis_n2000.txt"
"$BIN" hipotesis --largo 20000 --semilla 0 --interior --campo fuerte --G 5 --tsv "$OUT/hipotesis_n20000_int.tsv.txt" > "$OUT/hipotesis_n20000_int.txt"
"$BIN" veredicto --candidata max_media --referencia base --semilla 0 --parada > "$OUT/veredicto_max_media.txt"
"$BIN" veredicto --candidata kalman --referencia max_media --semilla 0 --campo ingenuo --G 15 > "$OUT/veredicto_kalman_ingenuo15.txt"
"$BIN" veredicto --candidata fondo_rec --referencia max_media --semilla 0 --largo 2000 > "$OUT/veredicto_fondo_rec.txt"
"$BIN" veredicto --candidata "ejec:m=8" --referencia max_media --semilla 0 --largo 2000 --campo fuerte > "$OUT/veredicto_ejec_fuerte.txt"
"$BIN" hipotesis --largo 2000 --semilla 0 --candidatos "max_media;espera;fondo_min" --ref max_media > "$OUT/hipotesis_externas.txt"
ls "$OUT" | wc -l
