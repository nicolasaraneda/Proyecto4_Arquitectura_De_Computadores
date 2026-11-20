#!/usr/bin/env bash
# reales.sh: equivalencia de un peldaño con su referencia en las dos series reales de
# la clase del 18/11 (Tesla y AMD desde el 10/1/2022 a las 10:20, 20 000 minutos,
# normalizadas entre 100 y 255), por el RTL y por el gemelo.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Las series no están en el repositorio (son datos de mercado de una cuenta y una
# captura de la maestra): se leen de $P4_DATOS. Tesla es la captura del registrador
# (capturas/ronda_10ms_clase.csv); AMD se arma desde los minutos de Alpaca
# (minuto/AMD.csv) con la normalización del profesor (ref/cotas/comun.py). Como
# control, Tesla se arma igual desde minuto/TSLA.csv y tiene que ser idéntica a la
# captura.
#
#   R0      copia parametrizada del testbench oficial (tools/equiv.sh, Verilator) a
#           0,1 y 1 ms contra ref/trader.py, y el gemelo a los tres períodos.
#   R1, R2  tb/fondo/tb_fondo.sv (bytes, estado, telemetría) a 0,1 y 1 ms contra
#           ref/fondo.py, y el gemelo del barrel (R1) a los tres períodos.
# A 10 ms el RTL queda fuera (unos 25 minutos por serie): el gemelo está validado
# contra el RTL (make cosim, make cosim-barrel).
#
# Uso: P4_DATOS=~/proyectos/datos_p4 tools/reales.sh r0|r1|r2
# Resultado en docs/mediciones/reales/PELDANO.txt.
set -uo pipefail
RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$RAIZ"
P=${1:?uso: tools/reales.sh r0|r1|r2}
PYTHON=${PYTHON:-python3}
DATOS=${P4_DATOS:?falta P4_DATOS (carpeta con capturas/ y minuto/)}
DATOS=${DATOS/#\~/$HOME}
SR=build/reales   # no B: tools/barrel/comun.sh define B=build/barrel
SALIDA=docs/mediciones/reales/$P.txt
mkdir -p "$SR" docs/mediciones/reales

$PYTHON - "$DATOS" "$SR" <<'PY' || { echo "FAIL: no se pudieron armar las series"; exit 1; }
import os, sys
sys.path.insert(0, "ref"); sys.path.insert(0, "ref/cotas")
import comun
datos, b = sys.argv[1], sys.argv[2]
def ventana(emp, fecha="2022-01-10", minuto=50, largo=20000):
    filas = [l.split(",") for l in open(os.path.join(datos, "minuto", emp + ".csv")).read().splitlines()[1:]]
    i = next(k for k, r in enumerate(filas) if r[0] == fecha and int(r[1]) == minuto)
    return comun.normalizar([float(r[2]) for r in filas[i:i + largo]])
def escribir(ruta, p):
    open(ruta, "w", newline="\n").write("tick,price\n" + "".join(f"{i},{x}\n" for i, x in enumerate(p)))
cap = [int(l.split(",")[1]) for l in open(os.path.join(datos, "capturas", "ronda_10ms_clase.csv")).read().splitlines()[1:]]
if ventana("TSLA") != cap:
    raise SystemExit("la ventana de TSLA no es la captura")
escribir(os.path.join(b, "tesla.csv"), cap)
escribir(os.path.join(b, "amd.csv"), ventana("AMD"))
PY

if [ "$P" = r0 ]; then
  HEX=sw/trade.hex
  $PYTHON tools/pochoasm.py sw/trade.s -o "$SR/r0.hex" > /dev/null && cmp -s "$SR/r0.hex" "$HEX" || { echo "FAIL: sw/trade.hex no corresponde a sw/trade.s"; exit 1; }
  make -s build/gemelo > /dev/null
  for s in tesla amd; do
    for per in 100000 1000000; do
      echo "SIM=verilator tools/equiv.sh reales_${s}_$per $per 20000 $SR/$s.csv > $SR/r0_${s}_$per.txt 2>&1"
    done
  done | xargs -P 4 -I{} bash -c "{}"
  {
    echo "Series reales de la clase del 18/11 en R0 (sw/trade.s) contra ref/trader.py"
    echo "Generado por tools/reales.sh r0, commit $(git rev-parse --short HEAD)."
    echo "Tesla: la captura del registrador (identica a TSLA desde el 10/1/2022 10:20, normalizada). AMD: el mismo inicio."
    echo
    for s in tesla amd; do
      for per in 100000 1000000; do tail -1 "$SR/r0_${s}_$per.txt"; done
      SERIE=$SR/$s.csv ETQ=$s tools/equiv_gemelo.sh 20000 2>&1 | tail -3
    done
  } | tee "$SALIDA"
else
  HW=$P
  export HW
  source tools/fondo/comun.sh
  ensamblar_fondo || { echo "FAIL: no ensambla"; exit 1; }
  compilar_sim || exit 1
  O=$BF/reales; mkdir -p "$O"
  for s in tesla amd; do
    for per in 100000 1000000; do echo "caso $O/${s}_$per sw/fondo.s $RAIZ/$SR/$s.csv 20000 $per 4000"; done
  done | en_paralelo
  make -s build/gemelo > /dev/null
  {
    cabecera "Series reales de la clase del 18/11 en $HW contra ref/fondo.py" tools/reales.sh "tools/reales.sh $HW"
    echo "Tesla: la captura del registrador (identica a TSLA desde el 10/1/2022 10:20, normalizada). AMD: el mismo inicio."
    echo
    echo "1. RTL con tb/fondo/tb_fondo.sv (Verilator)"
    for s in tesla amd; do for per in 100000 1000000; do cat "$O/${s}_$per/resultado.txt"; done; done
    echo
    echo "2. Gemelo del barrel (el de R1: el vigilante no existe en el gemelo) a los tres periodos"
    for s in tesla amd; do
      for per in 100000 1000000 10000000; do
        build/gemelo --barrel --xd 3 --tabla "$TABLA_HEX" --hex "$FONDO_HEX" --serie "$SR/$s.csv" --periodo-ns $per --nticks 20000 \
          --csv "$O/gem_${s}_$per.csv" > "$O/gem_${s}_$per.log"
        $PYTHON ref/fondo.py "$SR/$s.csv" --nticks 20000 --periodo-ns $per -o "$O/ref_${s}_$per.csv" > /dev/null
        r="gemelo, $s, periodo $per ns, 20000 ticks, $(grep 'Peor caso' "$O/gem_${s}_$per.log" | sed 's/  */ /g')"
        if ! grep -q "Testbenchs aprobados: 4/4" "$O/gem_${s}_$per.log"; then echo "FAIL $r: no entrega 4/4"
        elif cmp -s "$O/gem_${s}_$per.csv" "$O/ref_${s}_$per.csv"; then
          echo "PASS $r, 4/4, 20000 filas identicas a ref/fondo.py, patrimonio $(tail -1 "$O/gem_${s}_$per.csv" | cut -d, -f6)"
        else echo "FAIL $r: decisiones distintas a la referencia"; fi
      done
    done
  } | tee "$SALIDA"
fi
! grep -q "^FAIL" "$SALIDA"
