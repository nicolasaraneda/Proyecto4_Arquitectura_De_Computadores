#!/usr/bin/env bash
# validar_sta.sh: compara scripts/sta_icestorm.py con nextpnr y con icetime.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# 1. Rutas por flanco. rtl/top_clases.v tiene una ruta larga de una clase
#    conocida: del flanco de bajada al de subida (Caso = 0) o del de subida
#    al de bajada (Caso = 1). nextpnr informa su ruta crítica con los flancos
#    y el retardo. Se compara con la peor ruta de esa clase según
#    sta_icestorm.py, en la esquina máxima, en 5 semillas por caso.
# 2. Ruta de un período en el SoC. Con las corridas de scripts/medir_soc.sh
#    (si existen): la ruta de subida a subida según sta_icestorm.py contra
#    el período mínimo de nextpnr y de icetime, semilla por semilla.
#
# Uso: scripts/validar_sta.sh
# Resultado: mediciones/validacion_sta.txt
source "$(dirname "$0")/comun.sh"

D=$B/validar
mkdir -p "$D"

{
  echo "Validación de scripts/sta_icestorm.py"
  echo
  echo "1. Rutas por flanco (rtl/top_clases.v). Retardo de la ruta crítica en ns."
  printf "   %-34s %3s | %-22s %8s | %-10s %8s | %s\n" "caso" "sem" "nextpnr: flancos" "retardo" "sta: clase" "retardo" "diferencia"
  for caso in 0 1; do
    yosys -q -l "$D/c$caso.yosys.log" -p "read_verilog $F/rtl/top_clases.v; chparam -set Caso $caso top_clases; \
      synth_ice40 -top top_clases -json $D/c$caso.json" 2>/dev/null
    [ "$caso" = 0 ] && nom="larga de bajada a subida" || nom="larga de subida a bajada"
    [ "$caso" = 0 ] && clase="neg>pos" || clase="pos>neg"
    for s in 1 2 3 4 5; do
      b=$D/c${caso}_s$s
      nextpnr-ice40 --hx1k --package vq100 --freq 25 --seed "$s" --json "$D/c$caso.json" --pcf goboard.pcf \
        --pcf-allow-unconstrained --timing-allow-fail --asc "$b.asc" --write "$b.pnr.json" --report "$b.rpt.json" \
        -l "$b.log" -q > /dev/null 2>&1
      icetime -d hx1k -P vq100 -p goboard.pcf -o "$b.ice.v" "$b.asc" > /dev/null 2>&1
      python3 "$F/scripts/sta_icestorm.py" "$b.ice.v" --pnr-json "$b.pnr.json" --json "$b.sta.json" > "$b.sta.txt"
      python3 - "$b.rpt.json" "$b.sta.json" "$clase" "$nom" "$s" <<'PY'
import json, sys
rpt, sta, clase, nom, s = sys.argv[1:]
r = json.load(open(rpt))
# ruta crítica del reloj (no las de entradas o salidas asíncronas)
cp = [c for c in r["critical_paths"] if "async" not in c["from"] and "async" not in c["to"]]
c = max(cp, key=lambda c: sum(x["delay"] for x in c["path"]))
d_np = sum(x["delay"] for x in c["path"])
fl = "%s -> %s" % (c["from"].split()[0], c["to"].split()[0])
d_sta = json.load(open(sta))["rutas"][clase]["max"]
print("   %-34s %3s | %-22s %8.2f | %-10s %8.2f | %+.2f ns (%+.1f %%)" %
      (nom, s, fl, d_np, clase, d_sta, d_sta - d_np, 100 * (d_sta - d_np) / d_np))
PY
    done
  done
  echo "   nextpnr usa un solo valor por arco (el máximo de la base, con la entrada lógica de la LUT) y sta_icestorm.py"
  echo "   la entrada física que quedó ruteada. Lo que se valida es que la clase y el orden de magnitud coinciden."
  echo

  echo "2. Ruta de un período en el SoC (corridas de scripts/medir_soc.sh, objetivo 50 MHz), en ns"
  if ls "$B"/soc/*_f50_s1.sta.json > /dev/null 2>&1; then
    python3 - "$B/soc" <<'PY'
import glob, json, os, re, sys
d = sys.argv[1]
print("   %-8s %3s | %8s %8s %8s | %s" % ("variante", "sem", "sta", "icetime", "nextpnr", "sta menos icetime, sta menos nextpnr"))
difs_i, difs_n = [], []
for v in ("base_x1", "base_x2", "seg_x1", "seg_x2"):
    for p in sorted(glob.glob(os.path.join(d, "%s_f50_s*.sta.json" % v)), key=lambda x: int(re.search(r"_s(\d+)\.", x).group(1))):
        s = int(re.search(r"_s(\d+)\.", p).group(1))
        sta = json.load(open(p))["rutas"]["pos>pos"]["max"]
        ice = npn = None
        for l in open(p.replace(".sta.json", ".icetime.txt"), errors="replace"):
            m = re.search(r"Total path delay: ([0-9.]+) ns", l)
            if m:
                ice = float(m.group(1))
        for l in open(p.replace(".sta.json", ".log"), errors="replace"):
            m = re.search(r"Max frequency for clock\s+'[^']+': ([0-9.]+) MHz", l)
            if m:
                npn = 1000.0 / float(m.group(1))
        difs_i.append(sta - ice)
        difs_n.append(sta - npn)
        if s in (1, 2):
            print("   %-8s %3d | %8.2f %8.2f %8.2f | %+.2f, %+.2f" % (v, s, sta, ice, npn, sta - ice, sta - npn))
print("   (se muestran dos semillas por variante)")
print("   En las %d corridas: sta menos icetime de %+.2f a %+.2f ns. sta menos nextpnr de %+.2f a %+.2f ns." %
      (len(difs_i), min(difs_i), max(difs_i), min(difs_n), max(difs_n)))
print("   En el segmentado nextpnr puede informar una ruta de medio ciclo como la crítica (la cuenta doble):")
print("   por eso su período mínimo no siempre es la ruta de subida a subida.")
PY
  else
    echo "   (faltan las corridas: correr antes scripts/medir_soc.sh)"
  fi
} | tee "$M/validacion_sta.txt"
