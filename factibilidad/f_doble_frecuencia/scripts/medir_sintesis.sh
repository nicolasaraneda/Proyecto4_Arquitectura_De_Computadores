#!/usr/bin/env bash
# medir_sintesis.sh: qué flujos de Yosys conservan la cadena de retardo y cuáles se la llevan.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Sintetiza rtl/top_cadena.v con una cadena de 8 LUT escrita de varias formas
# y con varias opciones de synth_ice40, y cuenta en la netlist cuántas LUT de
# la cadena quedan, si queda el XOR y si la entrada del buffer global es una
# señal o una constante. Para la forma que se usa (primitivas con keep) corre
# además nextpnr y cuenta las celdas lógicas del duplicador ya empaquetadas.
#
# Uso: scripts/medir_sintesis.sh
# Resultado: mediciones/sintesis_cadena.txt
source "$(dirname "$0")/comun.sh"

D=$B/sintesis
mkdir -p "$D"
N=8

caso() {   # caso ETIQUETA "DESCRIPCION" "DEFINICIONES" MODO "OPCIONES DE synth_ice40"
  local e=$1 desc=$2 defs=$3 modo=$4 opts=$5
  yosys -q -l "$D/$e.yosys.log" -p "read_verilog $defs $F/rtl/duplicador_reloj.v $F/rtl/top_cadena.v; \
    chparam -set N $N -set Modo $modo top_cadena; synth_ice40 $opts -top top_cadena -json $D/$e.json" 2>/dev/null
  python3 - "$D/$e.json" "$desc" <<'PY'
import json, sys
j = json.load(open(sys.argv[1]))
m = j["modules"]["top_cadena"]
cad = [n for n, c in m["cells"].items() if c["type"] == "SB_LUT4" and "g_ret" in n]
xor = [n for n, c in m["cells"].items() if c["type"] == "SB_LUT4" and n.endswith("u_xor")]
luts = sum(1 for c in m["cells"].values() if c["type"] == "SB_LUT4")
gb = [c for c in m["cells"].values() if c["type"] == "SB_GB"]
ent = gb[0]["connections"]["USER_SIGNAL_TO_GLOBAL_BUFFER"][0] if gb else None
if not gb:
    estado = "no queda buffer global"
elif isinstance(ent, str):
    estado = "entrada del buffer global constante (%s): el reloj doblado desapareció" % ent
else:
    # ¿de qué celda sale la entrada del buffer global?
    drv = [n for n, c in m["cells"].items() if c["type"] == "SB_LUT4" and c["connections"]["O"][0] == ent]
    estado = "buffer global alimentado por %s" % (drv[0] if drv else "otra celda")
print("%-58s | %d de 8 | %-3s | %4d | %s" % (sys.argv[2], len(cad), "sí" if xor else "no", luts, estado))
PY
}

{
  echo "Cadena de $N LUT del duplicador después de synth_ice40 (Yosys $(yosys -V | cut -d' ' -f2))"
  echo
  printf "%-58s | %-7s | %-3s | %-4s | %s\n" "forma de escribirla y opciones" "cadena" "XOR" "LUT4" "qué llega al buffer global"
  caso a "primitivas SB_LUT4 con keep, flujo por defecto"           ""             0 ""
  caso b "primitivas SB_LUT4 sin keep, flujo por defecto"           "-DSIN_KEEP"   0 ""
  caso c "primitivas con keep, synth_ice40 -relut"                  ""             0 "-relut"
  caso d "primitivas sin keep, synth_ice40 -relut"                  "-DSIN_KEEP"   0 "-relut"
  caso e "primitivas con keep, synth_ice40 -abc9"                   ""             0 "-abc9"
  caso f "primitivas sin keep, synth_ice40 -abc9"                   "-DSIN_KEEP"   0 "-abc9"
  caso g "asignaciones comunes (CADENA_RTL), flujo por defecto"     "-DCADENA_RTL" 0 ""
  caso h "AND y OR de 4 entradas con keep, flujo por defecto"       ""             1 ""
  caso i "AND y OR de 4 entradas sin keep, synth_ice40 -relut"      "-DSIN_KEEP"   1 "-relut"
  echo
  echo "nextpnr sobre el caso a (primitivas con keep), cadena fija en X1/Y8:"
  CADENA_X=1 CADENA_Y=8 nextpnr-ice40 --hx1k --package vq100 --freq 50 --seed 1 --json "$D/a.json" \
    --pcf goboard.pcf --pcf-allow-unconstrained --pre-pack "$F/scripts/fijar_cadena.py" \
    --write "$D/a.pnr.json" -l "$D/a.log" -q > /dev/null 2>&1
  python3 - "$D/a.pnr.json" <<'PY'
import json, sys
m = list(json.load(open(sys.argv[1]))["modules"].values())[0]
dup = sorted((c["attributes"].get("NEXTPNR_BEL", "?"), n) for n, c in m["cells"].items() if "u_dup" in n)
lc = [x for x in dup if "/lc" in x[0]]
print("  celdas lógicas del duplicador después de empaquetar: %d (8 de la cadena y el XOR)" % len(lc))
for bel, n in dup:
    print("    %-12s %s" % (bel, n))
PY
} | tee "$M/sintesis_cadena.txt"
