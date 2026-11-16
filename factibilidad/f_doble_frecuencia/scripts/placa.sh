#!/usr/bin/env bash
# placa.sh: construye y revisa la prueba del duplicador para la Go Board (rtl/placa_x2.v).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# 1. Simula tb/tb_placa_x2.v: el caso normal y el control negativo.
# 2. Sintetiza placa_x2 y corre nextpnr con 10 semillas, con la cadena y el
#    anillo fijos (scripts/fijar_cadena.py) y los relojes restringidos por
#    nombre (restricciones/reloj_x2.py): el doblado a 56,4 MHz, que es lo
#    que exige un ciclo de trabajo de 45 %, y el del anillo a 150 MHz, el
#    doble de lo que oscila en la esquina más rápida de la base de tiempos.
# 3. Con la semilla 1 genera el bitstream placa/placa_x2.bin y su SHA-256.
# 4. Sobre ese diseño ruteado calcula, con scripts/sta_icestorm.py, el ancho
#    del pulso con cada botón y el período del anillo, en las tres esquinas
#    de la base de tiempos, y de ahí el número que deberían mostrar los
#    displays con SW4.
# No programa la placa: eso se hace a mano con iceprog (ver README.md).
#
# Uso: scripts/placa.sh [SEMILLAS]
# Resultado: mediciones/placa_x2.txt y placa/placa_x2.bin
source "$(dirname "$0")/comun.sh"

SEMILLAS=${1:-10}
D=$B/placa
P=$F/placa
PCF=$F/restricciones/placa_x2.pcf
mkdir -p "$D" "$P"

sim() {   # sim NOMBRE opciones -P...
  local n=$1; shift
  iverilog -g2012 -DSIM_RETARDO -s tb_placa_x2 -o "$D/$n.vvp" "$@" "$F/rtl/placa_x2.v" "$F/tb/tb_placa_x2.v"
  vvp -n "$D/$n.vvp" > "$D/$n.txt"
}

una() {   # una SEMILLA
  local s=$1
  RELOJ_X2_RED=clk2x RELOJ_X2_MHZ=56.4 RELOJ_EXTRA=clk_ani=150 \
  nextpnr-ice40 --hx1k --package vq100 --seed "$s" --freq 25 --ignore-loops --json "$D/placa.json" --pcf "$PCF" \
    --pre-pack "$F/scripts/fijar_cadena.py" --pre-pack "$F/restricciones/reloj_x2.py" \
    --asc "$D/placa_s$s.asc" --write "$D/placa_s$s.pnr.json" -l "$D/placa_s$s.log" -q > /dev/null 2>&1 || true
}
export -f una; export D F PCF

{
  echo "Prueba del duplicador para la Go Board (rtl/placa_x2.v)"
  echo
  echo "1. Simulación (tb/tb_placa_x2.v, modelo de retardo)"
  sim normal
  grep -v "finish called" "$D/normal.txt" | sed 's/^/    /' 
  sim control -Ptb_placa_x2.Control=1 -Ptb_placa_x2.RetCadenaPs=17000
  grep -v "finish called" "$D/control.txt" | sed 's/^/    /' 
  echo

  yosys -q -l "$D/placa.yosys.log" -p "read_verilog $F/rtl/placa_x2.v; synth_ice40 -top placa_x2 -json $D/placa.json" 2>/dev/null
  seq 1 "$SEMILLAS" | xargs -P "$JOBS" -I{} bash -c "una {}"

  echo "2. Recursos y frecuencia máxima según nextpnr ($SEMILLAS semillas; MHz: mínima, mediana y máxima)"
  lc=$(grep -h "ICESTORM_LC:" "$D/placa_s1.log" | head -1 | sed -E 's/.*: *([0-9]+)\/.*/\1/')
  gb=$(grep -h "SB_GB:" "$D/placa_s1.log" | head -1 | sed -E 's/.*: *([0-9]+)\/.*/\1/')
  echo "    celdas lógicas: $lc de 1280. Buffers globales: $gb de 8. BRAM: 0."
  for r in "clk2x" "clk_ani" 'i_Clk$SB_IO_IN_$glb_clk'; do
    obj=$(grep -hF "Max frequency for clock" "$D/placa_s1.log" | grep -F "'$r'" | tail -1 | sed -E 's/.*(PASS|FAIL) at ([0-9.]+) MHz.*/\2/')
    pasan=0
    for s in $(seq 1 "$SEMILLAS"); do
      grep -hF "Max frequency for clock" "$D/placa_s$s.log" | grep -F "'$r'" | tail -1 | grep -q PASS && pasan=$((pasan + 1))
    done
    v=$(for s in $(seq 1 "$SEMILLAS"); do
          grep -hF "Max frequency for clock" "$D/placa_s$s.log" | grep -F "'$r'" | tail -1 | sed -E 's/.*: ([0-9.]+) MHz.*/\1/'
        done | min_med_max)
    printf "    %-26s %s MHz, objetivo %s MHz, cierran %d de %d\n" "$r" "$v" "$obj" "$pasan" "$SEMILLAS"
  done
  echo

  icepack "$D/placa_s1.asc" "$P/placa_x2.bin"
  (cd "$P" && sha256sum placa_x2.bin > placa_x2.sha256)
  echo "3. Bitstream (semilla 1): $P/placa_x2.bin, $(stat -c %s "$P/placa_x2.bin") bytes"
  echo "    SHA-256: $(cut -d' ' -f1 "$P/placa_x2.sha256")"
  echo

  icetime -d hx1k -P vq100 -p "$PCF" -o "$D/placa_s1.ice.v" "$D/placa_s1.asc" > /dev/null 2>&1 || true
  echo "4. Ancho del pulso del reloj doblado con cada botón, en el bitstream (ns, base de tiempos de icestorm)"
  echo "    El multiplexor de tomas suma su retardo: por eso la cadena completa da más que en mediciones/cadena.txt,"
  echo "    y con SW1 queda un pulso aunque no haya ninguna LUT de la cadena en el camino."
  printf "    %-19s | %-19s | %-19s | %-19s\n" "botón" "mínima: sube, baja" "típica: sube, baja" "máxima: sube, baja"
  for caso in "ninguno (8 LUT):" "SW1 (sin cadena):i_Switch[0]=1" "SW2 (1 LUT):i_Switch[1]=1" "SW3 (2 LUT):i_Switch[2]=1"; do
    nom=${caso%%:*}; fij=${caso#*:}
    arg=(); [ -n "$fij" ] && arg=(--fijar "$fij")
    python3 "$F/scripts/sta_icestorm.py" "$D/placa_s1.ice.v" "${arg[@]}" --json "$D/sta_tmp.json" > "$D/sta_${nom%% *}.txt"
    python3 - "$D/sta_tmp.json" "$nom" <<'PY'
import json, sys
j = json.load(open(sys.argv[1]))
dup = [r for r in j["reloj"] if all(r["esquinas"][c]["duplicador"] for c in ("min", "tip", "max"))]
if not dup:
    print("    %-18s | no se comporta como duplicador" % sys.argv[2])
else:
    e = dup[0]["esquinas"]
    print("    %-18s | %s" % (sys.argv[2], " | ".join(
        "%-18s" % ("%.2f, %.2f" % (e[c]["sube"]["ancho_ps"] / 1000, e[c]["baja"]["ancho_ps"] / 1000)) for c in ("min", "tip", "max"))))
PY
  done
  echo "    Pulso mínimo de la red global según la hoja de datos (tW_GBUF, iCE40HX): 0,88 ns."
  echo

  echo "5. Oscilador en anillo (compuerta NAND y 8 LUT de retardo), en el bitstream"
  python3 - "$D/sta_tmp.json" <<'PY'
import json, sys
j = json.load(open(sys.argv[1]))
if not j["lazos"]:
    print("    no se encontró el lazo")
    sys.exit(0)
p = j["lazos"][0]["periodo_ns"]
print("    %-10s %12s %22s %24s" % ("esquina", "período (ns)", "D esperado = 1280 / T", "displays con SW4 (hex)"))
for c, n in (("min", "mínima"), ("tip", "típica"), ("max", "máxima")):
    d = int(1280 / p[c])
    print("    %-10s %12.2f %22d %24s" % (n, p[c], d, "%02X" % d))
print("    Si los displays muestran D, el período real del anillo es 1280 / D ns (D en decimal).")
print("    Retardo real respecto de la esquina máxima de la base: (1280 / D) / %.2f." % p["max"])
PY
} | tee "$M/placa_x2.txt"
if grep -q "RESULTADO: FAIL" "$M/placa_x2.txt"; then echo "placa.sh: la simulación falló"; exit 1; fi
