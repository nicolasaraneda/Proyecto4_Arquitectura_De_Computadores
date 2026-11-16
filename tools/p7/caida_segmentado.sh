#!/usr/bin/env bash
# caida_segmentado.sh: por qué la frecuencia mínima del segmentado bajó de
# 51,59 MHz (P1, docs/mediciones/barrel/recursos.txt) a 45,34 MHz (P7,
# docs/mediciones/p7/recursos.txt) sin que cambiara su RTL.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Mide el SoC con -DESPINO_SEGMENTADO y sw/trade.hex con el mismo comando en
# cada commit:
#   DEFS=-DESPINO_SEGMENTADO HEX=sw/trade.hex tools/medir_variante.sh ETIQUETA N
# El script de medición es siempre el del commit actual; lo que cambia es
# rtl/, sw/trade.hex y goboard.pcf, que se extraen de cada commit con
# git archive en build/p7/caida/ (rtl/ del repositorio no se toca).
#
#   1. Síntesis sola en cada commit que cambió rtl/, sw/trade.hex, goboard.pcf
#      o tools/medir_variante.sh desde la medición de P1: celdas por tipo y
#      huella de la netlist (dónde cambia la netlist).
#   2. nextpnr con las semillas 1 a N en cuatro commits: el de P1, el anterior
#      al salto, el del salto y el actual.
#   3. Mismas fuentes del commit actual leídas en otro orden (ORDENES órdenes
#      con N_ORDEN semillas): netlists de la misma lógica, para ver cuánto
#      cambia la frecuencia solo por la síntesis.
#   4. Equivalencia formal (yosys equiv_*) del SoC segmentado de P1 contra el
#      actual y del anterior al salto contra el salto, con la memoria del SoC y
#      las BRAM del banco de registros cortadas en sus puertos. Control
#      negativo: el actual contra una copia con la selección de la tabla
#      activa, que tiene que fallar.
#
# Deja docs/mediciones/p7/caida_segmentado.txt.
# Uso: tools/p7/caida_segmentado.sh [N] [N_ORDEN]   (o make p7-caida-seg)
#      Por defecto N = 40 y N_ORDEN = N (unos 3 minutos con 24 núcleos).
# Variables: JOBS (procesos de nextpnr por corrida, por defecto 6; las 4 más
#            ORDENES corridas van a la vez), ORDENES (por defecto 10).
set -euo pipefail
source "$(dirname "$0")/comun.sh"

SEMILLAS=${1:-40}
SEM_ORDEN=${2:-$SEMILLAS}
ORDENES=${ORDENES:-10}
export JOBS=${JOBS:-6}
SAL=$M/caida_segmentado.txt

P1=$(git rev-parse --short=7 e118269)        # medición de P1 (barrel/recursos.txt)
SALTO=$(git rev-parse --short=7 c293cf4)     # tabla de parámetros y vigilante en el SoC
ANTES=$(git rev-parse --short=7 "$SALTO^")
ACTUAL=$(git rev-parse --short=7 HEAD)

C=$B/caida
rm -rf "$C"; mkdir -p "$C"
cp tools/medir_variante.sh "$C/medir_variante.sh"

extraer() {   # extraer COMMIT DIR
  mkdir -p "$2"
  git archive "$1" rtl sw/trade.hex goboard.pcf | tar -x -C "$2"
}
fuentes() {   # fuentes DIR: lo mismo que lee tools/medir_variante.sh, uno por línea
  for f in "$1"/rtl/*.v "$1"/rtl/espino_core/*.v; do
    case "$f" in "$1"/rtl/00_*) ;; *) echo "$f" ;; esac
  done
}

# --- 1. Netlist en cada commit que cambió las entradas de la medición --------
COMMITS="$P1 $(git rev-list --reverse --date-order --abbrev-commit --abbrev=7 "$P1..HEAD" -- \
  rtl sw/trade.hex goboard.pcf tools/medir_variante.sh | tr '\n' ' ')"
sintetizar() {   # sintetizar COMMIT
  local c=$1 d=$C/sintesis/$1
  extraer "$c" "$d"
  ( cd "$d"
    yosys -q -l yosys.log -p "read_verilog -DESPINO_SEGMENTADO $(fuentes . | tr '\n' ' '); \
      chparam -set MemFile \"sw/trade.hex\" pochoco_soc; synth_ice40 -top pochoco_soc -json soc.json" )
}
for c in $COMMITS; do sintetizar "$c" & done
wait
: > "$C/commits.txt"
for c in $COMMITS; do
  d=$C/sintesis/$c
  # conteo final de Yosys: una línea por tipo
  stat=$(awk '/=== pochoco_soc ===/{p=1} p' "$d/yosys.log")
  n() { echo "$stat" | grep -E "^ +[0-9]+ +$1\$" | head -1 | awk '{print $1+0; f=1} END {if (!f) print 0}'; }
  dff=$(echo "$stat" | grep -E '^ +[0-9]+ +SB_DFF' | awk '{s+=$1} END {print s+0}')
  ram=$(( $(n SB_RAM40_4K) + $(n SB_RAM40_4KNR) ))
  printf '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n' "$c" "$c" \
    "$(git log -1 --format=%ad --date=format:'%d/%m %H:%M' "$c")" "$(git log -1 --format=%s "$c")" \
    "$($PYTHON tools/p7/caida_segmentado.py huella "$d/soc.json")" \
    "$(n SB_LUT4)" "$(n SB_CARRY)" "$dff" "$ram" "$(sha256sum < "$d/sw/trade.hex" | cut -c1-16)" >> "$C/commits.txt"
done

# --- 2 y 3. nextpnr ------------------------------------------------------------
: > "$C/corridas.txt"
medir() {   # medir ETIQUETA DIR SEMILLAS [RTL]
  local e=$1 d=$2 s=$3 r=${4:-rtl}
  ( cd "$d" && RTL=$r DEFS=-DESPINO_SEGMENTADO HEX=sw/trade.hex "$RAIZ/$C/medir_variante.sh" "caida_$e" "$s" \
      > "build/variantes/caida_$e.linea" 2>&1 || true
    mkdir -p "build/variantes/caida_$e"; mv "build/variantes/caida_$e.linea" "build/variantes/caida_$e/linea.txt" )
}
mkdir -p "$C/arbol"
for par in "p1:$P1:commit de P1, el de docs/mediciones/barrel/recursos.txt" \
           "antes:$ANTES:commit anterior al salto (padre de $SALTO)" \
           "salto:$SALTO:tabla de parametros y vigilante en pochoco_soc.v" \
           "actual:$ACTUAL:commit actual"; do
  IFS=: read -r e c desc <<< "$par"
  extraer "$c" "$C/arbol/$e"
  mkdir -p "$C/arbol/$e/build/variantes"
  echo "$e|$desc|$C/arbol/$e/build/variantes/caida_$e|$c" >> "$C/corridas.txt"
done
# Árboles con el orden de lectura cambiado: rtl/ plano con enlaces pNN_nombre.v
# (el glob de medir_variante.sh los lee en ese orden) y el último archivo en
# espino_core/, que se lee después.
mapfile -t BASE < <(fuentes "$C/arbol/actual")
for k in $(seq 0 $((ORDENES - 1))); do
  t=$C/arbol/orden$k
  mkdir -p "$t/rtl/espino_core" "$t/sw" "$t/build/variantes"
  ln -s "$RAIZ/$C/arbol/actual/sw/trade.hex" "$t/sw/trade.hex"
  ln -s "$RAIZ/$C/arbol/actual/goboard.pcf" "$t/goboard.pcf"
  mapfile -t ORD < <($PYTHON tools/p7/caida_segmentado.py orden "$k" "${BASE[@]}")
  for i in "${!ORD[@]}"; do
    if [ "$i" = $((${#ORD[@]} - 1)) ]; then dst=$t/rtl/espino_core; else dst=$t/rtl; fi
    ln -s "$RAIZ/${ORD[$i]}" "$dst/p$(printf '%02d' "$i")_$(basename "${ORD[$i]}")"
  done
  echo "orden$k|fuentes de $ACTUAL en el orden $k|$t/build/variantes/caida_orden$k|$ACTUAL" >> "$C/corridas.txt"
done
for e in p1 antes salto actual; do medir "$e" "$C/arbol/$e" "$SEMILLAS" & done
for k in $(seq 0 $((ORDENES - 1))); do medir "orden$k" "$C/arbol/orden$k" "$SEM_ORDEN" & done
wait

# --- 4. Equivalencia formal ---------------------------------------------------
# Se cortan la memoria del SoC (u_ram) y las BRAM del banco de registros: sus
# salidas pasan a ser entradas libres con el mismo nombre en los dos diseños y
# sus entradas pasan a ser salidas que se comparan. Así se compara toda la
# lógica del SoC y del core sin modelar las memorias, que son iguales.
preparar() {   # preparar DIR NOMBRE
  echo "design -reset; read_verilog -DESPINO_SEGMENTADO $(fuentes "$1" | tr '\n' ' ');
hierarchy -top pochoco_soc; proc; delete pochoco_soc/u_ram;
expose -input pochoco_soc/w:instr_rdata pochoco_soc/w:ram_a_next pochoco_soc/w:ram_b_rdata;
expose pochoco_soc/w:instr_req pochoco_soc/w:instr_addr pochoco_soc/w:ram_b_req pochoco_soc/w:data_we pochoco_soc/w:data_be pochoco_soc/w:data_addr pochoco_soc/w:data_wdata;
flatten; opt_clean;
expose -input t:SB_RAM40_4K %co:+[RDATA] w:* %i;
expose t:SB_RAM40_4K %ci:+[WDATA,WADDR,RADDR,WE,WCLKE,RE,RCLKE,MASK] w:* %i;
delete t:SB_RAM40_4K; memory -nomap; memory_map; opt -full; async2sync;
rename pochoco_soc $2; design -stash $2"
}
equivalencia() {   # equivalencia DIR_A DIR_B NOMBRE: escribe una línea
  local f=$C/equiv_$3
  { preparar "$1" gold; preparar "$2" gate
    echo "design -copy-from gold -as gold gold; design -copy-from gate -as gate gate;
equiv_make gold gate equiv; hierarchy -top equiv; equiv_simple -seq 5; equiv_induct -seq 5; equiv_status"
  } > "$f.ys"
  yosys -q -l "$f.log" -s "$f.ys" > /dev/null 2>&1 || true
  local r
  r=$(grep -E "Of those cells [0-9]+ are proven and [0-9]+ are unproven" "$f.log" | tail -1 | sed -E 's/^ *//')
  if grep -q "Equivalence successfully proven" "$f.log"; then echo "EQUIVALENTES ($r)"; else echo "DISTINTOS (${r:-sin resultado, ver $f.log})"; fi
}
# Control negativo: la selección de la tabla activa aunque Tabla = 0
CTRL=$C/arbol/control
mkdir -p "$CTRL"; cp -r "$C/arbol/actual/rtl" "$CTRL/"
sed -i -E 's/^( *assign tab_sel = \(Tabla != 0\) \? \(is_mmio & data_addr\[17\]\) : )1'"'"'b0;/\1(is_mmio \& data_addr[17]);/' "$CTRL/rtl/pochoco_soc.v"
[ "$(diff "$C/arbol/actual/rtl/pochoco_soc.v" "$CTRL/rtl/pochoco_soc.v" | grep -c '^>')" = 1 ] || { echo "FAIL: la copia de control no quedo como se esperaba"; exit 1; }
echo "p1 ($P1) contra actual ($ACTUAL): $(equivalencia "$C/arbol/p1" "$C/arbol/actual" p1_actual)" > "$C/equiv1.txt" &
echo "antes ($ANTES) contra salto ($SALTO): $(equivalencia "$C/arbol/antes" "$C/arbol/salto" antes_salto)" > "$C/equiv2.txt" &
echo "control, actual contra una copia con tab_sel activo (tiene que dar DISTINTOS): $(equivalencia "$C/arbol/actual" "$CTRL" control)" > "$C/equiv3.txt" &
wait
cat "$C/equiv1.txt" "$C/equiv2.txt" "$C/equiv3.txt" > "$C/equiv.txt"

# --- Informe ------------------------------------------------------------------
{
  echo "Caida de la frecuencia minima del segmentado entre P1 y P7"
  echo "Generado por tools/p7/caida_segmentado.sh (make p7-caida-seg). No editar a mano."
  echo
  versiones
  echo
  echo "Comando en cada commit (script de medicion del commit actual; rtl/, sw/trade.hex y"
  echo "goboard.pcf del commit medido, extraidos con git archive):"
  echo "  DEFS=-DESPINO_SEGMENTADO HEX=sw/trade.hex tools/medir_variante.sh ETIQUETA N"
  echo "yosys synth_ice40 y nextpnr-ice40 --hx1k --package vq100 --freq 25, goboard.pcf."
  echo "Semillas: 1 a $SEMILLAS en los cuatro commits, 1 a $SEM_ORDEN en cada orden de lectura."
  echo
  $PYTHON tools/p7/caida_segmentado.py informe "$C" "$SEMILLAS" "$SEM_ORDEN" | sed "s|$RAIZ/||g"
} > "$SAL"
cat "$SAL"
