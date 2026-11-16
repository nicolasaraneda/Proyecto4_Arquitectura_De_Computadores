#!/bin/sh
# parche.sh: copia local del núcleo del arnés para la cota hipotética del límite por orden.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso: sh cota/parche.sh DIRECTORIO_DEL_NUCLEO DIRECTORIO_DE_LA_COPIA
#
# El núcleo fija el límite de 63 acciones por orden, igual que la maestra: la
# cantidad son los 6 bits bajos del byte de decisión. Para saber cuánto se
# ganaría como máximo arreglando la ejecución hace falta una maestra que no
# existe, una que acepte órdenes más grandes. Esta copia cambia dos líneas de
# nucleo.c y nada más:
#
#   1. cuenta_ejecutar: la cantidad son los 6 bits bajos MÁS lo que venga sobre
#      el bit 8 de la decisión (cantidad = bits[5:0] | bits[31:8] << 6).
#   2. instancia_decidir: deja pasar esos bits altos en vez de cortar a un byte.
#
# Una estrategia que devuelve un byte (todas las del núcleo y todos los
# rivales) se ejecuta exactamente igual que en el arnés: los bits altos son
# cero. Solo la estrategia `lim` de cota/lim.c los usa. La copia se valida
# contra el arnés serie por serie (make validar-cota) y se usa SOLO para la
# cota: ninguna candidata de este estudio se evalúa con ella.
set -eu
origen="$1"
destino="$2"
mkdir -p "$destino"
for f in nucleo.h nucleo.c torneo.h torneo.c e_param.c e_rivales.c main.c; do
  cp "$origen/$f" "$destino/$f"
done

sed -i 's/^  int q = decision \& 63, accion = (decision >> 6) \& 3, hecho = 0;$/  int q = (decision \& 63) | ((decision >> 8) << 6), accion = (decision >> 6) \& 3, hecho = 0;   \/* COTA: cantidad ancha *\//' "$destino/nucleo.c"
sed -i 's/^  return i->e->decidir(i->estado, precio, propia) \& 0xFF;$/  return i->e->decidir(i->estado, precio, propia) \& 0x3FFFFFFF;   \/* COTA: deja pasar la cantidad ancha *\//' "$destino/nucleo.c"

# El parche debe haber cambiado exactamente dos líneas de nucleo.c y ningún otro archivo.
cambiadas=$(diff "$origen/nucleo.c" "$destino/nucleo.c" | grep -c '^>' || true)
if [ "$cambiadas" != "2" ]; then
  echo "parche.sh: se esperaban 2 lineas cambiadas en nucleo.c y hay $cambiadas (cambio el nucleo?)" >&2
  exit 1
fi
for f in nucleo.h torneo.h torneo.c e_param.c e_rivales.c main.c; do
  cmp -s "$origen/$f" "$destino/$f" || { echo "parche.sh: $f no deberia cambiar" >&2; exit 1; }
done
echo "Copia del nucleo para la cota: 2 lineas cambiadas en nucleo.c, los otros 6 archivos identicos."
diff "$origen/nucleo.c" "$destino/nucleo.c" || true
