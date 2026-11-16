#!/usr/bin/env bash
# medir_opciones.sh: ¿alcanzan las opciones de nextpnr para cerrar el reloj doblado con margen?
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El objetivo de frecuencia no cambia lo que hace nextpnr (mediciones/soc_x2.txt,
# punto 5). Aquí se prueban las opciones que sí cambian la ubicación o el
# ruteo, sobre los mismos SoC con reloj doblado de scripts/medir_soc.sh
# (hay que correrlo antes): --opt-timing, --tmg-ripup, las dos juntas y más
# peso del timing en el colocador. Una corrida por defecto demora unos 3 s y
# una con --opt-timing unos 6 s. Con --opt-timing y --tmg-ripup juntas
# demora minutos y puede no converger, porque el ruteo sigue deshaciendo
# rutas mientras quede holgura negativa: cada corrida tiene un tiempo límite
# (TLIMITE, 300 s por defecto) y las que no terminan se informan aparte, sin
# frecuencia. Para cada caso se
# informa la frecuencia máxima de las semillas que terminaron y cuántas
# llegan a lo que exige un ciclo de trabajo de 45 a 55 % (56,4 MHz) y a eso
# más el skew de la red global (58,8 MHz).
#
# Uso: scripts/medir_opciones.sh [SEMILLAS]
# Variables: TLIMITE (segundos por corrida), REHACER=1 (repite las terminadas)
# Resultado: mediciones/opciones_nextpnr.txt
source "$(dirname "$0")/comun.sh"

SEMILLAS=${1:-10}
TLIMITE=${TLIMITE:-300}
D=$B/opciones
S=$B/soc
mkdir -p "$D"
for v in base_x2 seg_x2; do
  [ -f "$S/$v.json" ] || { echo "Falta $S/$v.json: correr antes scripts/medir_soc.sh"; exit 1; }
done

una() {   # una VARIANTE ETIQUETA SEMILLA opciones...
  local v=$1 e=$2 s=$3; shift 3
  local log=$D/${v}_${e}_s$s.log
  # Una corrida que ya terminó, o que ya se cortó por el tiempo límite, no
  # se repite (REHACER=1 las repite todas)
  if [ "${REHACER:-0}" != 1 ] && grep -q "Program finished normally\|^Cortada por el tiempo límite" "$log" 2>/dev/null; then return 0; fi
  local rc=0
  CADENA_X=1 CADENA_Y=8 RELOJ_X2_MHZ=56.4 timeout "$TLIMITE" nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed "$s" \
    --json "$S/$v.json" --pcf goboard.pcf --timing-allow-fail \
    --pre-pack "$F/scripts/fijar_cadena.py" --pre-pack "$F/restricciones/reloj_x2.py" "$@" \
    -l "$log" -q > /dev/null 2>&1 || rc=$?
  # timeout devuelve 124 cuando corta la corrida
  if [ "$rc" = 124 ]; then echo "Cortada por el tiempo límite de $TLIMITE s" >> "$log"; fi
  return 0
}
export -f una; export D S F TLIMITE

# VARIANTE:ETIQUETA:OPCIONES. El Espino base está lejos (le falta cerca de
# 20 % de frecuencia): se prueba solo con --opt-timing, como control.
CASOS=(
  "seg_x2:defecto:"
  "seg_x2:opt:--opt-timing"
  "seg_x2:ripup:--tmg-ripup"
  "seg_x2:opt_ripup:--opt-timing --tmg-ripup"
  "seg_x2:peso30:--placer-heap-timingweight 30"
  "base_x2:defecto:"
  "base_x2:opt:--opt-timing"
)
# Ojo: xargs -L une una línea que termina en blanco con la siguiente, así
# que cada línea termina en un marcador que una() descarta.
for c in "${CASOS[@]}"; do
  v=${c%%:*}; r=${c#*:}; e=${r%%:*}; o=${r#*:}
  for s in $(seq 1 "$SEMILLAS"); do echo "$v $e $s $o --"; done
done | xargs -P "$JOBS" -L1 bash -c 'a=("$@"); unset "a[${#a[@]}-1]"; una "${a[@]}"' _

{
  echo "Opciones de nextpnr sobre el SoC con reloj doblado ($SEMILLAS semillas, objetivo 56,4 MHz en la red clk)"
  echo "Frecuencia máxima según nextpnr (MHz: mínima, mediana y máxima). 56,4 MHz: ciclo de trabajo de 45 a 55 %."
  echo "58,8 MHz: lo mismo más 0,727 ns de skew de la red global."
  echo
  printf "%-8s %-36s | %-9s | %-22s | %-9s %-9s %-9s\n" "variante" "opciones" "terminan" "nextpnr" ">= 50" ">= 56,4" ">= 58,8"
  for c in "${CASOS[@]}"; do
    v=${c%%:*}; r=${c#*:}; e=${r%%:*}; o=${r#*:}; [ -z "$o" ] && o="(por defecto)"
    # Solo cuentan las corridas que terminaron: una cortada por el tiempo
    # límite deja en el log estimaciones intermedias, no el resultado.
    fs=$(for s in $(seq 1 "$SEMILLAS"); do
           l=$D/${v}_${e}_s$s.log
           grep -q "Program finished normally" "$l" 2>/dev/null && fmax_de "$l" clk
         done || true)
    n=$(echo "$fs" | grep -c . || true)
    printf "%-8s %-36s | %-9s | %-22s | %-9s %-9s %-9s\n" "$v" "$o" "$n de $SEMILLAS" "$(echo "$fs" | min_med_max)" \
      "$(echo "$fs" | awk '$1>=50{c++} END{print c+0}') de $n" \
      "$(echo "$fs" | awk '$1>=56.4{c++} END{print c+0}') de $n" \
      "$(echo "$fs" | awk '$1>=58.8{c++} END{print c+0}') de $n"
  done
  echo
  echo "terminan: corridas que nextpnr completó dentro del tiempo límite de $TLIMITE s. Las demás no tienen resultado."
  echo
  echo "Detalle por semilla (MHz; -: no terminó)"
  printf "%-8s %-36s |" "variante" "opciones"; for s in $(seq 1 "$SEMILLAS"); do printf " %6s" "s$s"; done; echo
  for c in "${CASOS[@]}"; do
    v=${c%%:*}; r=${c#*:}; e=${r%%:*}; o=${r#*:}; [ -z "$o" ] && o="(por defecto)"
    printf "%-8s %-36s |" "$v" "$o"
    for s in $(seq 1 "$SEMILLAS"); do
      l=$D/${v}_${e}_s$s.log
      if grep -q "Program finished normally" "$l" 2>/dev/null; then printf " %6s" "$(fmax_de "$l" clk)"; else printf " %6s" "-"; fi
    done
    echo
  done
} | tee "$M/opciones_nextpnr.txt"
