#!/usr/bin/env bash
# riesgos.sh: pruebas de riesgos de datos y de control del core segmentado.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Corre sw/hazard_test.s, sw/hazard_review.s y sw/hazard_cycles.s (los
# programas de riesgos de nuestro Proyecto 3) en tres variantes del core y
# compara sus trazas (tb/core_trace_tb.v y tb/comparar_trazas.py):
#
#   1. Funcional: el pipeline de 3 etapas hace las mismas escrituras al banco
#      de registros, los mismos accesos al bus y los mismos cambios de salidas
#      que el Espino base, en el mismo orden. El base no tiene ninguno de
#      estos riesgos, porque espera un ciclo por instrucción.
#      En hazard_cycles.s solo se comparan las salidas: los valores leídos
#      dependen del ciclo y el ciclo cambia por diseño.
#   2. Ciclo a ciclo: el pipeline con la memoria leída en el flanco de bajada
#      y el pipeline con ROM combinacional dan exactamente la misma traza.
#   3. Ciclo a ciclo contra el modelo de ciclos esperado: la traza de
#      tb/tb_cpi.sv con el pipeline es idéntica a la del gemelo digital con
#      --pipeline (1 ciclo por instrucción, 2 los loads y 2 los saltos tomados).
#   4. Cada programa se revisa a sí mismo: debe terminar con los LEDs en 1111.
#   5. Ningún valor desconocido (X) llega a usarse.
#
# Uso, desde la raíz del repositorio: tools/riesgos.sh
# Variables de entorno:
#   PROGS   programas (por defecto los tres)
#   MUTA    definiciones extra solo para el core segmentado. Lo usa
#           tools/mutaciones.sh para comprobar que estas pruebas detectan un
#           error puesto a propósito (por ejemplo MUTA=-DMUTA_FWD).
#   ETQ     sufijo de la carpeta de salida (build/riesgos_ETQ)
#   CICLOS  ciclos que corre cada traza (6000)
set -uo pipefail

PROGS=${PROGS:-"hazard_test hazard_review hazard_cycles"}
MUTA=${MUTA:-}
ETQ=${ETQ:-}
CICLOS=${CICLOS:-6000}
PYTHON=${PYTHON:-python3}
SRC=$(echo rtl/*.v rtl/espino_core/*.v)
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
G=build/gemelo
O=build/riesgos${ETQ:+_$ETQ}
mkdir -p "$O"
[ -x "$G" ] || { echo "falta $G: correr make gemelo"; exit 1; }

fallas=0
falla() { echo "FAIL $1"; fallas=$((fallas + 1)); }

# traza PROG VARIANTE [definiciones y fuentes extra...]: deja $O/PROG/VARIANTE.txt y .log
traza() {
  local p=$1 v=$2; shift 2
  iverilog -g2012 -s core_trace_tb "-DPROGRAMA=\"$O/$p/$p.hex\"" "-DTRAZA=\"$O/$p/$v.txt\"" \
    -DCICLOS="$CICLOS" "$@" -o "$O/$p/$v.vvp" "$CELLS_SIM" $SRC tb/core_trace_tb.v \
    && vvp -n "$O/$p/$v.vvp" > "$O/$p/$v.log"
}

for p in $PROGS; do
  mkdir -p "$O/$p"
  $PYTHON tools/pochoasm.py "sw/$p.s" -o "$O/$p/corto.hex" --rom "$O/$p/pochoco_rom.v" > /dev/null || { falla "$p: no ensambla"; continue; }
  # Relleno con ceros hasta 512 palabras, igual que queda la memoria en la placa
  $PYTHON -c "
import sys
w = open(sys.argv[1]).read().split()
open(sys.argv[2], 'w').write('\n'.join(w + ['00000000'] * (512 - len(w))) + '\n')" "$O/$p/corto.hex" "$O/$p/$p.hex"

  sw=""; tipos="rf,bus,io"
  if [ "$p" = hazard_cycles ]; then sw="-DSWITCH_CONTADOR"; tipos="io"; fi

  traza "$p" base $sw &
  traza "$p" seg  $sw -DESPINO_SEGMENTADO $MUTA &
  traza "$p" rom  $sw -DESPINO_ROM $MUTA "$O/$p/pochoco_rom.v" &
  wait
  for v in base seg rom; do
    [ -s "$O/$p/$v.log" ] || { falla "$p ($v): la simulacion no corrio"; continue 2; }
  done

  # 1. Funcional contra el Espino base
  if $PYTHON tb/comparar_trazas.py --modo funcional --tipos "$tipos" "$O/$p/base.txt" "$O/$p/seg.txt" > "$O/$p/funcional.txt"; then
    echo "PASS $p, funcional (base contra segmentado): $(grep 'eventos iguales' "$O/$p/funcional.txt" | sed 's/ (ref.*//' | tr '\n' ',' | sed 's/,$//; s/,/, /g')"
  else
    falla "$p, funcional (base contra segmentado): $(grep -m1 DIFIEREN "$O/$p/funcional.txt")"
  fi

  # 2. Ciclo a ciclo entre las dos formas de traer la instrucción
  if $PYTHON tb/comparar_trazas.py --modo ciclo "$O/$p/seg.txt" "$O/$p/rom.txt" > "$O/$p/ciclo.txt"; then
    echo "PASS $p, ciclo a ciclo (flanco de bajada contra ROM): $(cat "$O/$p/ciclo.txt")"
  else
    falla "$p, ciclo a ciclo (flanco de bajada contra ROM): $(head -1 "$O/$p/ciclo.txt")"
  fi

  # 3. Ciclo a ciclo contra el gemelo (no aplica a hazard_cycles: el gemelo no
  #    modela interruptores que cambian)
  if [ "$p" != hazard_cycles ]; then
    if iverilog -g2012 -s tb_cpi -DESPINO_SEGMENTADO $MUTA "-DPROGRAMA=\"$O/$p/$p.hex\"" "-DSERIE=\"tb/practica.csv\"" -DNTICKS=3 \
         "-DTRAZA=\"$O/$p/cpi_rtl.txt\"" -o "$O/$p/cpi.vvp" "$CELLS_SIM" $SRC tb/tb_cpi.sv \
       && vvp -n "$O/$p/cpi.vvp" > "$O/$p/cpi.log" \
       && "$G" --pipeline --hex "$O/$p/$p.hex" --nticks 3 --traza "$O/$p/cpi_gem.txt" --callado \
       && cmp -s "$O/$p/cpi_rtl.txt" "$O/$p/cpi_gem.txt"; then
      echo "PASS $p, ciclo a ciclo (segmentado contra el gemelo): $(wc -l < "$O/$p/cpi_rtl.txt") eventos identicos"
    else
      falla "$p, ciclo a ciclo (segmentado contra el gemelo): la traza difiere"
    fi
  fi

  # 4 y 5. Resultado del propio programa y monitor de X
  for v in base seg rom; do
    if ! grep ' io ' "$O/$p/$v.txt" | tail -1 | grep -q 'led=1111'; then
      falla "$p ($v): el programa no termina con los LEDs en 1111"
    fi
    if ! grep -q 'monitor de X: 0 valores' "$O/$p/$v.log"; then
      falla "$p ($v): $(grep 'monitor de X' "$O/$p/$v.log" | sed 's/core_trace_tb: //')"
    fi
  done
  echo "     $p: CPI base $(grep CPI "$O/$p/base.log" | sed -E 's/.*= ([0-9.]+) \(.*/\1/'), segmentado $(grep CPI "$O/$p/seg.log" | sed -E 's/.*= ([0-9.]+) \(.*/\1/') ($(grep CPI "$O/$p/seg.log" | sed -E 's/.*CPI = (.*) = .*/\1/'))"
done

if [ "$fallas" -ne 0 ]; then
  echo "FAIL riesgos: $fallas comprobaciones fallaron"; exit 1
fi
echo "PASS riesgos: el core segmentado ejecuta los programas de riesgos igual que el Espino base"
