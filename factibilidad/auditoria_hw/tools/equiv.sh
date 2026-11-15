#!/usr/bin/env bash
# equiv.sh: el fondo en assembly contra su referencia en C, con series que la pieza no usó.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# La pieza comparó la serie de práctica y ocho familias sintéticas con la
# semilla 1. Aquí se repite la comparación con el testbench de la pieza
# (tb/tb_fondo.sv, Verilator), que además de las decisiones deja el estado
# interno, y se agrega:
#   - las 14 familias de ref/series.py con las semillas 2 y 3 (28 series de
#     20 000 ticks que nadie había corrido), a 0,1 ms;
#   - la serie de práctica a 0,1 ms y a 1 ms (repetición);
#   - el mismo programa en el hardware I1 (barrel con extensión, vigilante y
#     tabla, de factibilidad/i_integrado), que es la configuración "fondo en
#     un chip": la práctica completa a 0,1 ms, 3000 ticks a 1 ms y dos series
#     sintéticas.
# En cada caso se exige 4/4, decisiones idénticas byte a byte a las de
# fondo_min en C (con los precios que se pierden durante el reset) y los 13
# campos del estado interno idénticos en todos los ticks
# (tools/comparar_estado.py de la pieza).
#
# Uso: factibilidad/auditoria_hw/tools/equiv.sh   (o make equiv)
# Resultado en mediciones/equiv.txt. Unos 4 minutos con 5 procesos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"
arnes || exit 1

O=$B/equiv
mkdir -p "$O/series" "$O/prog"
NT=${NT:-20000}
FAMILIAS="modelo modelo_vecino dos_componentes cambio_volatilidad paseo tendencia reversion saltos cambio_de_caracter volatil nivel_bajo plana borde_bajo borde_alto"

cp $F/sw/fondo.s "$O/prog/fondo.s"
$PYTHON tools/pochoasm.py "$O/prog/fondo.s" -o "$O/prog/fondo.hex" > /dev/null || exit 1
$PYTHON $F/tools/simbolos.py "$O/prog/fondo.s" --vh "$O/prog/simbolos.vh" || exit 1

compilar() {   # compilar NOMBRE "definiciones" FUENTES...
  local n=$1 defs=$2; shift 2
  mkdir -p "$O/$n"
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_fondo -O3 $defs \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS "-DPROGRAMA=\"$O/prog/fondo.hex\"" "-I$O/prog" --Mdir "$O/$n/obj" -o sim \
    "$CELLS_SIM" "$@" $F/tb/tb_fondo.sv > "$O/$n/verilator.log" 2>&1
}
compilar barrel "" $SRC_BARREL_PROTO &
compilar i1a "$DEFS_I1A" $SRC_I &
wait
[ -x "$O/barrel/obj/sim" ] && [ -x "$O/i1a/obj/sim" ] || { echo "FAIL Verilator no compila tb_fondo"; exit 1; }

# caso HARDWARE ETIQUETA SERIE NTICKS PERIODO
caso() {
  local d=$O/$1 e=$2 k c dec est
  k=$(perdidos "$5")
  "$d/obj/sim" "+serie=$3" "+nticks=$4" "+periodo=$5" +inicio=4000 "+ticks_csv=$d/$e.t.csv" "+dec_csv=$d/$e.dec.csv" > "$d/$e.log" 2>&1
  FONDO_TRAZA=$d/$e.traza.csv HILOS=1 "$ARNES" correr --estrategia fondo_min --serie "$3" --nticks "$4" --perdidos "$k" -o "$d/$e.ref.csv" > "$d/$e.ref.log" 2>&1
  c=$(grep -o "Chequeos aprobados: [0-9]/4" "$d/$e.log" | grep -o "[0-9]/4")
  if cmp -s "$d/$e.dec.csv" "$d/$e.ref.csv"; then dec=ok; else dec="decisiones distintas desde la fila $(cmp "$d/$e.dec.csv" "$d/$e.ref.csv" | grep -o 'line [0-9]*' | grep -o '[0-9]*')"; fi
  if $PYTHON $F/tools/comparar_estado.py "$d/$e.t.csv" "$d/$e.traza.csv" > "$d/$e.estado.log" 2>&1; then est=ok; else est="estado distinto: $(grep -m1 'primera diferencia' "$d/$e.estado.log" | cut -c1-80)"; fi
  local filas ordenes pesos
  filas=$(grep -o 'PASS [0-9]* filas' "$d/$e.estado.log" | grep -o '[0-9]*')
  ordenes=$(grep 'Ordenes' "$d/$e.log" | grep -o '[0-9]*$')
  pesos=$(grep -o '[0-9]* cambios de pesos' "$d/$e.estado.log" | grep -o '^[0-9]*')
  if [ "$c" = 4/4 ] && [ "$dec" = ok ] && [ "$est" = ok ]; then
    printf "PASS %-7s %-24s %6s ticks a %7s ns: 4/4, %5s filas de decisiones y %5s de estado idénticas; peor caso %4s ciclos, %5s órdenes, %2s cambios de pesos, patrimonio %s\n" \
      "$1" "$e" "$4" "$5" "$(($(wc -l < "$d/$e.dec.csv") - 1))" "${filas:-?}" "$(grep 'Peor caso' "$d/$e.log" | grep -o ': [0-9]*' | grep -o '[0-9]*' | head -1)" "$ordenes" "${pesos:-?}" "$(tail -1 "$d/$e.dec.csv" | cut -d, -f6)"
  else
    printf "FAIL %-7s %-24s %6s ticks a %7s ns: %s, %s, %s\n" "$1" "$e" "$4" "$5" "${c:-sin resultado}" "$dec" "$est"
  fi > "$d/$e.resultado.txt"
}
export -f caso perdidos
export O F ARNES PYTHON

LISTA="barrel practica_0p1ms tb/practica.csv $NT 100000
barrel practica_1ms tb/practica.csv 3000 1000000
i1a practica_0p1ms tb/practica.csv $NT 100000
i1a practica_1ms tb/practica.csv 3000 1000000"
for s in 2 3; do
  for f in $FAMILIAS; do
    a=$O/series/${f}_$s.csv
    [ -s "$a" ] || $PYTHON ref/series.py "$f" --n "$NT" --semilla "$s" -o "$a" > /dev/null
    LISTA="$LISTA
barrel ${f}_s$s $a $NT 100000"
  done
done
LISTA="$LISTA
i1a volatil_s2 $O/series/volatil_2.csv $NT 100000
i1a modelo_s3 $O/series/modelo_3.csv $NT 100000"

T0=$(date +%s)
echo "$LISTA" | xargs -P "$JOBS" -L 1 bash -c 'caso "$@"' _
T1=$(date +%s)

{
echo "Auditoría: el fondo en assembly (sw/fondo.s) contra su referencia en C (fondo_min), con series nuevas"
echo "Generado por factibilidad/auditoria_hw/tools/equiv.sh (make equiv). No editar a mano."
echo
versiones
echo "Programa: $F/sw/fondo.s, imagen con sha256 $(sha256sum "$O/prog/fondo.hex" | cut -c1-16)..."
echo "Referencia: factibilidad/retorno/r4b_fondo/fondo.c sin modificar, compilada en build/arnes de esta carpeta."
echo "Testbench: $F/tb/tb_fondo.sv con Verilator. Hardware: 'barrel' es el prototipo de factibilidad/a_barrel;"
echo "  'i1a' es el SoC de factibilidad/i_integrado con $DEFS_I1A."
echo "Series sintéticas: ref/series.py FAMILIA --n $NT --semilla 2 y 3. Demora: $((T1 - T0)) s con $JOBS procesos."
echo
echo "$LISTA" | while read -r h e resto; do cat "$O/$h/$e.resultado.txt" 2>/dev/null || echo "FAIL $h $e: sin resultado"; done
echo
n=$(echo "$LISTA" | wc -l)
ok=$(echo "$LISTA" | while read -r h e resto; do cat "$O/$h/$e.resultado.txt" 2>/dev/null; done | grep -c "^PASS")
ticks=$(echo "$LISTA" | awk '{s += $4} END {print s}')
filas=$(echo "$LISTA" | while read -r h e resto; do grep -o 'PASS [0-9]* filas' "$O/$h/$e.estado.log" 2>/dev/null | grep -o '[0-9]*'; done | awk '{s += $1} END {print s + 0}')
echo "Casos: $n. PASS: $ok. Ticks simulados: $ticks. Filas de estado comparadas (13 campos): $filas."
echo "  En el barrel prototipo: $(echo "$LISTA" | grep -c '^barrel') casos. En el hardware I1: $(echo "$LISTA" | grep -c '^i1a') casos."
if [ "$ok" = "$n" ]; then echo "RESULTADO: PASS, cero diferencias"; else echo "RESULTADO: FAIL"; fi
} | tee "$M/equiv.txt"

grep -q "^RESULTADO: PASS" "$M/equiv.txt"
