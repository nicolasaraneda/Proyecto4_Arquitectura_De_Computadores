#!/usr/bin/env bash
# medir_ticks.sh: latencia de respuesta de max_media en un hilo del barrel,
# contra el Espino base y el pipeline de 3 etapas medidos en la misma corrida.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El programa es sw/trade.s sin modificar. En el barrel va precedido por la
# tabla de arranque: max_media corre en el hilo 0 y los otros tres hilos
# quedan en un lazo vacío.
#
#   1. 200 ticks de la serie de práctica con el timing del testbench oficial
#      (período de la ronda 3). Respuesta (de byte_done a la escritura de
#      DECISION) y tick completo, promedio y peor caso.
#   2. Barrido de la fase: el peor caso depende de en qué punto del lazo de
#      sondeo llega el precio. Se repite la medición corriendo el inicio de la
#      serie de a un ciclo, 12 veces (el lazo de sondeo del barrel dura 12
#      ciclos, el del base 8 y el del segmentado 5), y se informa el máximo.
#
# Base y segmentado se miden con tb/tb_cpi.sv, sin modificar. El barrel con
# tb/barrel/tb_barrel_ticks.sv, que es su adaptación.
#
# Uso: tools/barrel/medir_ticks.sh   (o make barrel-ticks)
# Resultado en docs/mediciones/barrel/ticks.txt.
set -euo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/ticks
mkdir -p "$O"
programas
JOBS=${JOBS:-6}

# correr VARIANTE ETIQUETA NTICKS INICIO_NS
correr() {
  local v=$1 e=$2 nt=$3 ini=$4
  local comun=("-DSERIE=\"tb/practica.csv\"" -DNTICKS="$nt" -DINICIO_NS="$ini")
  case $v in
    base)       iverilog -g2012 -s tb_cpi "${comun[@]}" '-DPROGRAMA="sw/trade.hex"' \
                  -o "$O/${v}_$e.vvp" "$CELLS_SIM" $BASE_SRC tb/tb_cpi.sv ;;
    segmentado) iverilog -g2012 -s tb_cpi -DESPINO_SEGMENTADO "${comun[@]}" '-DPROGRAMA="sw/trade.hex"' \
                  -o "$O/${v}_$e.vvp" "$CELLS_SIM" $BASE_SRC tb/tb_cpi.sv ;;
    barrel)     iverilog -g2012 -s tb_barrel_ticks "${comun[@]}" "-DPROGRAMA=\"$B/sw/trade_h0.hex\"" \
                  -o "$O/${v}_$e.vvp" "$CELLS_SIM" $BARREL_SRC $TB/tb_barrel_ticks.sv ;;
  esac
  vvp -n "$O/${v}_$e.vvp" > "$O/${v}_$e.log"
  grep -q "^PASS el modelo de costo" "$O/${v}_$e.log" || { echo "FAIL $v $e"; exit 1; }
}
export -f correr; export O B T TB SW FO CELLS_SIM BASE_SRC BARREL_SRC

{
  for v in base segmentado barrel; do
    echo "correr $v 200 200 4000"
    for f in $(seq 0 11); do echo "correr $v fase$f 40 $((4000 + 40 * f))"; done
  done
} | xargs -P "$JOBS" -I{} bash -c "{}"

{
echo "Latencia de max_media (sw/trade.s) por tick: Espino base, pipeline de 3 etapas y barrel"
echo "Generado por tools/barrel/medir_ticks.sh (make barrel-ticks). No editar a mano."
echo
versiones
echo
$PYTHON - "$O" <<'PYEOF'
import re, sys
D = sys.argv[1]
PRESUPUESTO = {"ronda 1 (10 ms)": 249762, "ronda 2 (1 ms)": 24762, "ronda 3 (0,1 ms)": 2262}

def leer(nombre):
    t = open(f"{D}/{nombre}.log").read()
    r = {}
    for clave, pat in (("r_prom", "respuesta, promedio"), ("r_peor", "respuesta, peor caso"),
                       ("t_prom", "tick completo, promedio"), ("t_peor", "tick completo, peor caso")):
        m = re.search(pat + r"\s+IC\s+([\d.]+)\s+ciclos\s+([\d.]+)", t)
        r[clave] = (float(m.group(1)), float(m.group(2)))
    r["ticks"] = int(re.search(r"Por tick, (\d+) ticks medidos", t).group(1))
    return r

nombres = [("base", "Espino base"), ("segmentado", "Pipeline de 3 etapas"), ("barrel", "Barrel, max_media en el hilo 0")]
print("1. 200 ticks de la serie de practica, timing del testbench oficial, periodo de 0,1 ms")
print()
print(f"  {'Core':<34} {'Respuesta: IC':>14} {'ciclos prom.':>13} {'peor':>6} {'Tick completo: IC':>18} {'ciclos prom.':>13} {'peor':>6}")
res = {}
for v, texto in nombres:
    r = leer(f"{v}_200")
    res[v] = r
    print(f"  {texto:<34} {r['r_prom'][0]:>14.2f} {r['r_prom'][1]:>13.2f} {r['r_peor'][1]:>6.0f} {r['t_prom'][0]:>18.2f} {r['t_prom'][1]:>13.2f} {r['t_peor'][1]:>6.0f}")
print()
print(f"  Ticks medidos: {res['barrel']['ticks']} (los dos primeros precios llegan durante el reset, igual que en el testbench oficial).")
print("  En el barrel el IC es el del hilo 0. Cada instrucción suya ocupa 4 ciclos.")
print()
print("2. Barrido de la fase del sondeo: 12 corridas de 40 ticks, el inicio se corre un ciclo cada vez")
print()
print(f"  {'Core':<34} {'Respuesta, peor caso por fase':<52} {'maximo':>7}")
peor = {}
for v, texto in nombres:
    xs = [int(leer(f"{v}_fase{f}")["r_peor"][1]) for f in range(12)]
    peor[v] = max(xs + [int(res[v]["r_peor"][1])])
    print(f"  {texto:<34} {' '.join(f'{x:>3}' for x in xs):<52} {peor[v]:>7}")
print()
print("3. Contra el presupuesto de cada ronda (peor caso con el barrido de la fase)")
print()
print(f"  {'Core':<34} {'peor caso':>10} " + " ".join(f"{k:>18}" for k in PRESUPUESTO))
for v, texto in nombres:
    print(f"  {texto:<34} {peor[v]:>10} " + " ".join(f"{100 * peor[v] / p:>16.3f} %" for p in PRESUPUESTO.values()))
print()
b, s, x = res["base"], res["segmentado"], res["barrel"]
print(f"  Respuesta promedio del barrel contra el base: {x['r_prom'][1] / b['r_prom'][1]:.2f} veces mas lenta. Contra el segmentado: {x['r_prom'][1] / s['r_prom'][1]:.2f} veces.")
print(f"  Ciclos libres por tick en la ronda 3 con el barrel: {2262 - peor['barrel']} de 2262 en el hilo gestor,")
print(f"  o sea unas {(2262 - peor['barrel']) // 4} instrucciones por hilo y por tick antes de pasarse del plazo.")
PYEOF
echo
echo "4. Salida de tb_barrel_ticks, 200 ticks"
echo
grep -v '\$finish' "$O/barrel_200.log" | sed 's/^/  /'
} | tee "$M/ticks.txt"
