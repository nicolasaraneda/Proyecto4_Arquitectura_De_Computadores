#!/usr/bin/env bash
# probar_soc.sh: el testbench oficial, sin modificar, sobre el SoC con vigilante.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Cuatro corridas de tb/tb_proyecto_4.sv tal como está en el repositorio
# (2000 ticks a 0,1 ms, sw/trade.hex):
#
#   repo_base   rtl/ del repositorio, core base                 (referencia)
#   vig_base    copia del SoC con vigilante, core base
#   repo_seg    rtl/ del repositorio, core segmentado           (referencia)
#   vig_seg     copia del SoC con vigilante, core segmentado
#
# En las corridas con vigilante se compila además tb/mon_vigilante.sv como
# segundo módulo raíz. Se exige:
#   - 4/4 en las cuatro corridas;
#   - decisiones.csv idéntico byte a byte entre cada copia y su referencia;
#   - que el vigilante nunca suba BOOT y que la cuenta de precios sin
#     respuesta no pase de 1.
#
# El testbench escribe decisiones.csv en el directorio desde donde se corre.
# Para no pisar el de la raíz del repositorio, cada simulación se ejecuta en
# una carpeta propia con enlaces a sw/ y tb/.
#
# Uso, desde la raíz del repositorio:
#   factibilidad/e_warmboot/scripts/probar_soc.sh
# Resultado en mediciones/vigilante_soc.txt.
set -euo pipefail

E=factibilidad/e_warmboot
D=$E/build/soc
RAIZ=$(pwd)
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
mkdir -p "$D" "$E/mediciones"
RTLV=$($E/scripts/armar_rtl.sh)

compilar() {   # compilar NOMBRE CARPETA_RTL DEFS MONITOR
  local nombre=$1 rtl=$2 defs=$3 mon=$4
  rm -rf "$D/$nombre"; mkdir -p "$D/$nombre"
  ln -s "$RAIZ/sw" "$D/$nombre/sw"; ln -s "$RAIZ/tb" "$D/$nombre/tb"
  if [ "$mon" = 1 ]; then
    iverilog -g2012 $defs -s tb_proyecto_4 -s mon_vigilante -o "$D/$nombre/sim" \
      "$CELLS_SIM" $rtl/*.v $rtl/espino_core/*.v tb/tb_proyecto_4.sv $E/tb/mon_vigilante.sv
  else
    iverilog -g2012 $defs -s tb_proyecto_4 -o "$D/$nombre/sim" \
      "$CELLS_SIM" $rtl/*.v $rtl/espino_core/*.v tb/tb_proyecto_4.sv
  fi
}

compilar repo_base rtl      ""                    0
compilar vig_base  "$RTLV"  ""                    1
compilar repo_seg  rtl      "-DESPINO_SEGMENTADO" 0
compilar vig_seg   "$RTLV"  "-DESPINO_SEGMENTADO" 1

for n in repo_base vig_base repo_seg vig_seg; do
  ( cd "$D/$n" && vvp -n sim > tb.log 2>&1 ) &
done
wait

ok=1
{
  echo "Testbench oficial sin modificar sobre el SoC con vigilante"
  echo "Comando: factibilidad/e_warmboot/scripts/probar_soc.sh"
  echo "tb/tb_proyecto_4.sv, sha256 $(sha256sum tb/tb_proyecto_4.sv | cut -c1-16)..., 2000 ticks a 0,1 ms, sw/trade.hex"
  echo
  for n in repo_base vig_base repo_seg vig_seg; do
    echo "--- $n ---"
    grep -v "finish called" "$D/$n/tb.log" | sed 's/^/  /'
    [ -f "$D/$n/mon_vigilante.txt" ] && echo "  monitor: $(cat "$D/$n/mon_vigilante.txt")"
    echo "  decisiones.csv: sha256 $(sha256sum "$D/$n/decisiones.csv" | cut -d' ' -f1)"
    grep -q "4/4" "$D/$n/tb.log" || { echo "  FALLA: no entrega 4/4"; ok=0; }
  done
  echo
  for par in "repo_base vig_base" "repo_seg vig_seg"; do
    set -- $par
    if cmp -s "$D/$1/decisiones.csv" "$D/$2/decisiones.csv"; then
      echo "decisiones.csv de $2 idéntico al de $1: sí"
    else
      echo "decisiones.csv de $2 idéntico al de $1: NO"; ok=0
    fi
  done
  for n in vig_base vig_seg; do
    if grep -q "max_sin_respuesta=1 ciclos_con_BOOT=0 " "$D/$n/mon_vigilante.txt"; then
      echo "$n: el vigilante no dispara y la cuenta no pasa de 1: sí"
    else
      echo "$n: el vigilante no dispara y la cuenta no pasa de 1: NO"; ok=0
    fi
  done
  [ $ok = 1 ] && echo "RESULTADO: correcto" || echo "RESULTADO: con fallas"
} | tee $E/mediciones/vigilante_soc.txt
grep -q "RESULTADO: correcto" $E/mediciones/vigilante_soc.txt
