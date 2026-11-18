#!/usr/bin/env bash
# oficial.sh: el testbench oficial sin modificar y la equivalencia con la
# referencia, sobre el barrel con la extensión de la ISA.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Dos programas en el hilo 0, los dos con la tabla de arranque delante:
#   trade     sw/trade.s sin modificar. No usa la extensión: comprueba que el
#             hardware agregado no cambia nada (criterio 1 de la puerta).
#   trade_xd  sw/xd/trade_xd.s, max_media escrita con devk y emad (la regla de R0
#             hasta el 17/11, sw/historico/trade_max_media.s). Comprueba de punta a
#             punta el ensamblador y las dos instrucciones; se compara con el Espino
#             base corriendo ese programa y con ref/trader.py --regla max_media.
# Con cada uno:
#   1. tb/tb_proyecto_4.sv sin modificar, con Icarus y el comando de su
#      encabezado (más las definiciones del barrel con la extensión): 4/4 y
#      decisiones.csv idéntico al del Espino base con sw/trade.hex.
#   2. Copia parametrizada del testbench (solo cambian el programa, el período,
#      la cantidad de ticks y el archivo de salida) con Verilator: los 20 000
#      ticks de la serie de práctica a 0,1 ms y a 1 ms, idénticos a
#      ref/trader.py.
# Informa además el peor caso de la respuesta que mide el testbench.
#
# Uso: tools/xd/oficial.sh   (o make xd-oficial)
# Resultado en docs/mediciones/xd/oficial.txt. Demora unos 4 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$BX/oficial
NTICKS=${NTICKS:-20000}
mkdir -p "$O"
programas
$PYTHON $T/tabla.py 0 $SWX/trade_xd.s > "$BX/sw/trade_xd_h0.s"
$PYTHON tools/pochoasm.py "$BX/sw/trade_xd_h0.s" -o "$BX/sw/trade_xd_h0.hex" > /dev/null || { echo "FAIL: no ensambla trade_xd"; exit 1; }

# --- 1. Testbench oficial sin modificar -------------------------------------------
oficial() {   # oficial ETIQUETA PROGRAMA.hex FUENTES
  local d=$O/$1
  mkdir -p "$d/sw" "$d/tb"
  ln -sf "$RAIZ/tb/practica.csv" "$d/tb/practica.csv"
  cp "$2" "$d/sw/trade.hex"
  iverilog -g2012 -s tb_proyecto_4 -o "$d/tb_p4" "$CELLS_SIM" $3 tb/tb_proyecto_4.sv || return 1
  ( cd "$d" && vvp -n tb_p4 > salida.txt )
}
oficial base     sw/trade.hex               "$BASE_SRC" &
$PYTHON tools/pochoasm.py sw/historico/trade_max_media.s -o "$O/trade_max_media.hex" > /dev/null
oficial base_mm  "$O/trade_max_media.hex"   "$BASE_SRC" &
oficial trade    "$B/sw/trade_h0.hex"       "$XD_SRC" &
oficial trade_xd "$BX/sw/trade_xd_h0.hex"   "$XD_SRC" &
wait

# --- 2. Los 20 000 ticks contra ref/trader.py ---------------------------------------
caso() {   # caso PROGRAMA PERIODO_NS
  local e=$1_$2 per=$2 d=$O/$1_$2 hex
  [ "$1" = trade ] && hex=$B/sw/trade_h0.hex || hex=$BX/sw/trade_xd_h0.hex
  mkdir -p "$d"
  sed -e "s|PROGRAMA   = \"[^\"]*\";|PROGRAMA   = \"$hex\";|" \
      -e "s|PERIODO_NS = [0-9]*;|PERIODO_NS = $per;|" \
      -e "s|NTICKS     = [0-9]*;|NTICKS     = $NTICKS;|" \
      -e "s|\"decisiones.csv\"|\"$d/tb.csv\"|" \
      tb/tb_proyecto_4.sv > "$d/tb_p4.sv"
  if [ "$(diff tb/tb_proyecto_4.sv "$d/tb_p4.sv" | grep -c '^>')" -gt 4 ]; then
    echo "FAIL $e: la copia del testbench cambio mas de lo esperado" > "$d/resultado.txt"; return
  fi
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_proyecto_4 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS -O3 --Mdir "$d/obj" -o sim \
    "$CELLS_SIM" $XD_SRC "$d/tb_p4.sv" > "$d/verilator.log" 2>&1 || { echo "FAIL $e: Verilator no compila" > "$d/resultado.txt"; return; }
  "$d/obj/sim" > "$d/tb.log"
  local regla=oficial; [ "$1" = trade_xd ] && regla=max_media
  $PYTHON ref/trader.py tb/practica.csv --nticks "$NTICKS" --periodo-ns "$per" --regla $regla -o "$d/ref.csv" > "$d/ref.log"
  local resumen="$1, periodo $per ns, $NTICKS ticks, $(grep 'Peor caso' "$d/tb.log" | sed 's/  */ /g')"
  if ! grep -q "Testbenchs aprobados: 4/4" "$d/tb.log"; then echo "FAIL $resumen: el testbench no entrega 4/4" > "$d/resultado.txt"; return; fi
  if ! cmp -s "$d/tb.csv" "$d/ref.csv"; then echo "FAIL $resumen: decisiones distintas a la referencia" > "$d/resultado.txt"; return; fi
  echo "PASS $resumen, 4/4, $(($(wc -l < "$d/tb.csv") - 1)) filas identicas a ref/trader.py, patrimonio $(tail -1 "$d/tb.csv" | cut -d, -f6)" > "$d/resultado.txt"
}
for p in trade trade_xd; do for per in 100000 1000000; do caso $p $per & done; done; wait

{
echo "Testbench oficial y equivalencia con la referencia, barrel con la extension de la ISA ($XD_DEFS)"
echo "Generado por tools/xd/oficial.sh (make xd-oficial). No editar a mano."
echo
versiones
echo "  $(verilator --version)"
if git diff --quiet HEAD -- tb/tb_proyecto_4.sv; then
  echo "tb/tb_proyecto_4.sv: sin cambios respecto del repositorio (sha256 $(sha256sum tb/tb_proyecto_4.sv | cut -c1-16)...)"
else
  echo "ATENCION: tb/tb_proyecto_4.sv tiene cambios locales"
fi
echo
echo "1. Testbench oficial sin modificar (Icarus, 2000 ticks a 0,1 ms)"
for p in trade trade_xd; do
  [ $p = trade ] && que="sw/trade.s sin modificar en el hilo 0" || que="sw/xd/trade_xd.s (devk y emad) en el hilo 0"
  echo "--- $que ---"
  grep -E 'Peor caso|Patrimonio|aprobados' "$O/$p/salida.txt" | sed 's/^/  /'
  if grep -q "Testbenchs aprobados: 4/4" "$O/$p/salida.txt"; then echo "PASS $p: 4/4"; else echo "FAIL $p: no obtiene 4/4"; fi
  [ $p = trade ] && b=base || b=base_mm
  if cmp -s "$O/$p/decisiones.csv" "$O/$b/decisiones.csv"; then echo "PASS $p: decisiones.csv identico byte a byte al del Espino base con el mismo programa"
  else echo "FAIL $p: decisiones.csv difiere del Espino base"; fi
done
echo
echo "2. Serie de practica completa contra ref/trader.py (Verilator)"
for p in trade trade_xd; do for per in 100000 1000000; do cat "$O/${p}_$per/resultado.txt"; done; done
echo
} | tee "$MX/oficial.txt"

! grep -q "^FAIL" "$MX/oficial.txt"
