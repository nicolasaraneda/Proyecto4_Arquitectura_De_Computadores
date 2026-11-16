#!/usr/bin/env bash
# medir_restricciones.sh: cómo se restringe el reloj doblado en nextpnr y qué analiza.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Usa la prueba de placa (rtl/placa_x2.v) sin su oscilador en anillo
# (ConAnillo = 0), que tiene los dos dominios: el reloj de 25 MHz del pin y
# el reloj doblado, con un cruce entre ellos.
#   1. Las tres formas de restringir: --freq, ctx.addClock por --pre-pack y
#      SDC. Para cada una, qué objetivo le queda a cada reloj.
#   2. Qué comandos de SDC acepta esta versión de nextpnr.
#   3. Qué dice nextpnr de la relación entre los dos relojes, y si cambia con
#      el largo de la cadena.
#   4. Si la cadena aparece en alguna ruta analizada.
#   5. Lo que informa icetime sobre el mismo diseño ruteado.
#   6. En el SoC: qué informa nextpnr de las entradas del esclavo SPI.
#
# Uso: scripts/medir_restricciones.sh
# Resultado: mediciones/restricciones.txt
source "$(dirname "$0")/comun.sh"

D=$B/restricciones
mkdir -p "$D"
PCF=$F/restricciones/placa_x2.pcf

sintetizar() {   # sintetizar N
  yosys -q -l "$D/placa_n$1.yosys.log" -p "read_verilog $F/rtl/duplicador_reloj.v $F/rtl/placa_x2.v; \
    chparam -set NRet $1 -set ConAnillo 0 placa_x2; synth_ice40 -top placa_x2 -json $D/placa_n$1.json" 2>/dev/null
}
pnr() {   # pnr ETIQUETA JSON opciones...
  local e=$1 j=$2; shift 2
  timeout 120 nextpnr-ice40 --hx1k --package vq100 --seed 1 --json "$j" --pcf "$PCF" \
    --timing-allow-fail --asc "$D/$e.asc" -l "$D/$e.log" -q "$@" > "$D/$e.out" 2>&1 || true
}
despues_de_rutear() {   # líneas del último informe de un log
  awk '/Routing complete|Router1 time/{p=1} p' "$1"
}

sintetizar 8
J=$D/placa_n8.json

{
  echo "Restricciones del reloj doblado en nextpnr ($(nextpnr-ice40 --version 2>&1 | sed -E 's/.*Version //; s/\)//'))"
  echo "Diseño: rtl/placa_x2.v sin el anillo, cadena de 8 LUT, semilla 1. Dos relojes: el del pin y clk2x."
  echo

  echo "1. Formas de restringir y objetivo que le queda a cada reloj"
  pnr sin "$J"
  pnr freq50 "$J" --freq 50
  RELOJ_X2_RED=clk2x RELOJ_X2_MHZ=50 pnr addclock "$J" --freq 25 --pre-pack "$F/restricciones/reloj_x2.py"
  pnr sdc "$J" --sdc "$F/restricciones/relojes.sdc"
  for e in sin freq50 addclock sdc; do
    case $e in
      sin)      d="sin restricción" ;;
      freq50)   d="--freq 50" ;;
      addclock) d="--freq 25 y --pre-pack restricciones/reloj_x2.py (ctx.addClock)" ;;
      sdc)      d="--sdc restricciones/relojes.sdc (create_clock)" ;;
    esac
    echo "  $d:"
    despues_de_rutear "$D/$e.log" | grep -E "Max frequency for clock" | sed -E 's/^Info: /    /'
  done
  echo

  echo "2. Comandos de SDC (cada uno agregado a relojes.sdc, solo hasta el empaquetado)"
  while IFS= read -r cmd; do
    cp "$F/restricciones/relojes.sdc" "$D/prueba.sdc"
    printf '%s\n' "$cmd" >> "$D/prueba.sdc"
    if timeout 60 nextpnr-ice40 --hx1k --package vq100 --json "$J" --pcf "$PCF" --sdc "$D/prueba.sdc" \
         --pack-only -l "$D/prueba.log" -q > "$D/prueba.out" 2>&1; then
      echo "  acepta    $cmd"
    else
      echo "  rechaza   $cmd"
      grep -h "ERROR" "$D/prueba.out" | head -1 | sed 's/^/              /'
    fi
  done <<'SDC'
create_clock -period 20 -name otro [get_nets clk2x]
create_clock -period 20 -waveform {0 8} -name otro [get_nets clk2x]
create_generated_clock -name gen -source [get_ports i_Clk] -multiply_by 2 [get_nets clk2x]
set_clock_groups -asynchronous -group osc -group clk2x
set_clock_uncertainty 0.5 osc
set_clock_latency 3 clk2x
set_max_delay 5 -from [get_ports i_Clk] -to [get_ports o_Prueba]
set_input_delay 2 -clock osc [get_ports {i_Switch[0]}]
set_multicycle_path 2 -from [get_ports i_Clk] -to [get_ports o_Prueba]
set_false_path -from [get_ports i_Clk] -to [get_ports o_Prueba]
set_false_path -from [get_clocks osc] -to [get_clocks clk2x]
SDC
  echo

  echo "3. Relación entre los dos relojes según nextpnr (--sdc, después de rutear)"
  despues_de_rutear "$D/sdc.log" | grep -E "Max frequency for posedge|Clock to clock delay|Max delay" | sed -E 's/^Info: /    /'
  echo "  Con --ignore-rel-clk:"
  pnr sdc_ign "$J" --sdc "$F/restricciones/relojes.sdc" --ignore-rel-clk
  despues_de_rutear "$D/sdc_ign.log" | grep -E "Max frequency for posedge|Clock to clock delay" | sed -E 's/^Info: /    /'
  echo "  El mismo dato con otros largos de cadena (si nextpnr viera la cadena, cambiaría):"
  for n in 4 16; do
    sintetizar $n
    pnr sdc_n$n "$D/placa_n$n.json" --sdc "$F/restricciones/relojes.sdc"
    echo "    N = $n: $(despues_de_rutear "$D/sdc_n$n.log" | grep -E 'Clock to clock delay' | head -1 | sed -E 's/^Info: //')"
    echo "            $(despues_de_rutear "$D/sdc_n$n.log" | grep -E 'Max delay <async> +-> <async>' | sed -E 's/^Info: //')"
  done
  echo "    N = 8: $(despues_de_rutear "$D/sdc.log" | grep -E 'Clock to clock delay' | head -1 | sed -E 's/^Info: //')"
  echo "            $(despues_de_rutear "$D/sdc.log" | grep -E 'Max delay <async> +-> <async>' | sed -E 's/^Info: //')"
  echo

  echo "4. ¿Aparece la cadena en alguna ruta que nextpnr informa? (--sdc, después de rutear)"
  for r in "for clock 'clk2x'" "for clock 'i_Clk" "for cross-domain path '<async>' -> '<async>'" \
           "for cross-domain path '<async>' -> 'posedge clk2x'" \
           "for cross-domain path 'posedge i_Clk\$SB_IO_IN_\$glb_clk' -> 'posedge clk2x'"; do
    n=$(despues_de_rutear "$D/sdc.log" | awk -v r="Critical path report $r" 'index($0, r){p=1; next} /Critical path report/{p=0} p' | grep -c "Source g_ret" || true)
    echo "    ruta crítica $r: $n LUT de la cadena"
  done
  echo "  La cadena aparece solo en la ruta combinacional de pin a pin (i_Clk hasta o_Prueba, el pin de prueba),"
  echo "  que nextpnr informa como retardo sin compararlo con nada. En las rutas de los dos relojes no está:"
  echo "  para nextpnr el reloj doblado nace en la salida del buffer global."
  echo

  echo "5. icetime sobre el mismo diseño ruteado (--sdc)"
  icetime -d hx1k -P vq100 -p "$PCF" -t -c 50 "$D/sdc.asc" > "$D/sdc.icetime.txt" 2>&1 || true
  grep -E "Total path delay|Checking|PASSED|FAILED" "$D/sdc.icetime.txt" | sed 's/^/    /'
  echo "    primera y última celda de la ruta que informa:"
  grep -E "^ +[a-z0-9_]+ \(" "$D/sdc.icetime.txt" | sed -n '1p;$p' | sed 's/^ */      /'
  echo "    tramos de la cadena en esa ruta: $(grep -c "g_ret\|d\[" "$D/sdc.icetime.txt" || true)"
  echo

  echo "6. En el SoC con el reloj doblado (Espino base, semilla 1, ctx.addClock a 50 MHz)"
  if [ ! -f "$D/soc.json" ]; then
    yosys -q -l "$D/soc.yosys.log" -p "read_verilog $SOC_X2; chparam -set MemFile \"sw/trade.hex\" pochoco_soc; \
      synth_ice40 -top pochoco_soc -json $D/soc.json" 2>/dev/null
  fi
  CADENA_X=1 CADENA_Y=8 RELOJ_X2_MHZ=50 timeout 300 nextpnr-ice40 --hx1k --package vq100 --seed 1 --freq 25 \
    --json "$D/soc.json" --pcf goboard.pcf --timing-allow-fail \
    --pre-pack "$F/scripts/fijar_cadena.py" --pre-pack "$F/restricciones/reloj_x2.py" \
    --asc "$D/soc.asc" -l "$D/soc.log" -q > "$D/soc.out" 2>&1 || true
  despues_de_rutear "$D/soc.log" | grep -E "Max frequency|Max delay|Clock to clock" | sed -E 's/^(Info|Warning|ERROR): /    /'
  echo "  Ruta crítica de las entradas asíncronas (SCLK, MOSI, CS_n e interruptores) al reloj doblado:"
  despues_de_rutear "$D/soc.log" | awk "/Critical path report for cross-domain path '<async>' -> 'posedge clk'/{p=1; next} /Critical path report|^Info: Max/{p=0} p" \
    | grep -E "Source|Sink|ns logic" | sed -E 's/^Info: +/      /' | head -8
  icetime -d hx1k -P vq100 -p goboard.pcf -t -c 50 "$D/soc.asc" > "$D/soc.icetime.txt" 2>&1 || true
  echo "  icetime: $(grep -E "Total path delay" "$D/soc.icetime.txt")"
} | tee "$M/restricciones.txt"
