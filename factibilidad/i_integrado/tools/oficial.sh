#!/usr/bin/env bash
# oficial.sh: el testbench oficial, sin modificar, contra cada configuración.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Compila tb/tb_proyecto_4.sv tal como está en el repositorio (2000 ticks a
# 0,1 ms) contra cada configuración de la lista de abajo y exige:
#   - 4/4;
#   - decisiones.csv idéntico byte a byte al del Espino base de rtl/ con
#     sw/trade.hex;
#   - en las configuraciones con vigilante, que BOOT nunca suba y que la
#     cuenta de precios sin respuesta no pase de 1 (monitor
#     tb/mon_vigilante.sv de factibilidad/e_warmboot, compilado como segundo
#     módulo raíz: el testbench oficial no se toca).
#
# Programas: en el barrel, sw/trade.s sin modificar con la tabla de arranque
# delante (la regla base en el hilo 0, los otros tres hilos en un lazo vacío).
# Las filas marcadas "xd" corren la misma regla escrita con las instrucciones
# nuevas (sw/trade_media.s y sw/trade_emad.s de factibilidad/d_isa): tienen
# que decidir igual.
#
# El testbench lee "sw/trade.hex" y "tb/practica.csv" relativos al directorio
# actual y escribe decisiones.csv ahí. Cada corrida se hace en su propia
# carpeta de build, con esos archivos puestos en ese lugar.
#
# Uso: factibilidad/i_integrado/tools/oficial.sh [FILTRO]   (o make oficial)
# Resultado en mediciones/oficial.txt (si no hay FILTRO). Unos 8 minutos.
# Variable JOBS: simulaciones en paralelo (5).
set -uo pipefail
source "$(dirname "$0")/comun.sh"

FILTRO=${1:-.}
JOBS=${JOBS:-5}
O=$B/oficial
mkdir -p "$O"
programas
MEDIA="$(defs_de media_mul)"

# nombre | fuentes | definiciones | programa | monitor | descripción
LISTA=$(cat <<FIN
base|base||sw/trade.hex|0|Espino base de rtl/ (referencia de las decisiones, I4)
segmentado|base|-DESPINO_SEGMENTADO|sw/trade.hex|0|Pipeline de 3 etapas de rtl/ (I4)
x_ref|barrel||$B/sw/trade_h0.hex|0|Barrel de esta carpeta sin definiciones
x_emad_k5|barrel|$(defs_de emad_k5)|$B/sw/trade_h0.hex|0|(a) emad
x_media_mul|barrel|$MEDIA|$B/sw/trade_h0.hex|0|(b) emad, devk y mulstep
x_alu_todo|barrel|$(defs_de alu_todo)|$B/sw/trade_h0.hex|0|(c) más carriles en la ALU
x_media_bandas|barrel|$(defs_de media_bandas)|$B/sw/trade_h0.hex|0|(d) más carriles en unidad aparte
x_media_muldiv|barrel|$(defs_de media_muldiv)|$B/sw/trade_h0.hex|0|(e) el recomendado más divstep
x_alu_todo_div|barrel|$(defs_de alu_todo_div)|$B/sw/trade_h0.hex|0|(e) carriles en la ALU más divstep
tabla1|barrel|-DI_TABLA=1|$B/sw/trade_h0.hex|0|Barrel con la tabla de 256 x 16
tabla2|barrel|-DI_TABLA=2|$B/sw/trade_h0.hex|0|Barrel con otras 512 palabras de datos
i2|barrel|-DI_VIGILANTE|$B/sw/trade_h0.hex|1|I2: barrel y vigilante
i1a|barrel|$MEDIA -DI_VIGILANTE -DI_TABLA=1|$B/sw/trade_h0.hex|1|I1 con la tabla de 256 x 16
i1b|barrel|$MEDIA -DI_VIGILANTE -DI_TABLA=2|$B/sw/trade_h0.hex|1|I1 con otras 512 palabras de datos
i1a_xd|barrel|$MEDIA -DI_VIGILANTE -DI_TABLA=1|$B/sw/trade_media_h0.hex|1|I1 con la regla base escrita con devk y emad (xd)
i1b_xd|barrel|$MEDIA -DI_VIGILANTE -DI_TABLA=2|$B/sw/trade_media_h0.hex|1|I1 de 16 BRAM con devk y emad (xd)
seg_vig|seg|-DESPINO_SEGMENTADO|sw/trade.hex|1|Segmentado con vigilante, sin extensión
i3a|seg|-DESPINO_SEGMENTADO $(defs_de emad_k5)|sw/trade.hex|1|I3: segmentado, emad y vigilante
i3a_xd|seg|-DESPINO_SEGMENTADO $(defs_de emad_k5)|$B/sw/trade_emad.hex|1|I3 con la regla base escrita con emad (xd)
i3b|seg|-DESPINO_SEGMENTADO $MEDIA|sw/trade.hex|1|I3 con emad, devk y mulstep
i3b_xd|seg|-DESPINO_SEGMENTADO $MEDIA|$B/sw/trade_media.hex|1|I3 con la regla base escrita con devk y emad (xd)
FIN
)

# una NOMBRE: compila y corre el testbench oficial en su carpeta
una() {
  local nombre=$1 fuentes defs hex mon desc src
  IFS='|' read -r _ fuentes defs hex mon desc <<< "$(echo "$LISTA" | grep "^$nombre|")"
  case $fuentes in base) src=$BASE_SRC ;; barrel) src=$INT_SRC ;; seg) src=$SEG_SRC ;; esac
  rm -rf "${O:?}/${nombre:?}"; mkdir -p "$O/$nombre/sw" "$O/$nombre/tb"
  ln -s "$RAIZ/tb/practica.csv" "$O/$nombre/tb/practica.csv"
  cp "$hex" "$O/$nombre/sw/trade.hex"
  if [ "$mon" = 1 ]; then
    iverilog -g2012 $defs -s tb_proyecto_4 -s mon_vigilante -o "$O/$nombre/sim" "$CELLS_SIM" $src tb/tb_proyecto_4.sv $E/tb/mon_vigilante.sv > "$O/$nombre/iverilog.log" 2>&1 || return 0
  else
    iverilog -g2012 $defs -s tb_proyecto_4 -o "$O/$nombre/sim" "$CELLS_SIM" $src tb/tb_proyecto_4.sv > "$O/$nombre/iverilog.log" 2>&1 || return 0
  fi
  ( cd "$O/$nombre" && vvp -n sim > salida.txt 2>&1 )
  return 0
}
export -f una
export O LISTA BASE_SRC INT_SRC SEG_SRC CELLS_SIM RAIZ E

NOMBRES=$(echo "$LISTA" | cut -d'|' -f1 | grep -E "$FILTRO")
echo "$NOMBRES" | grep -qx base || NOMBRES="base
$NOMBRES"
inicio=$(date +%s)
echo "$NOMBRES" | xargs -P "$JOBS" -I{} bash -c 'una {}'
fin=$(date +%s)

informe() {
echo "Testbench oficial sin modificar contra cada configuración"
echo "Generado por factibilidad/i_integrado/tools/oficial.sh (make oficial). No editar a mano."
echo
versiones
if git diff --quiet HEAD -- tb/tb_proyecto_4.sv; then
  echo "tb/tb_proyecto_4.sv: sin cambios respecto del repositorio (sha256 $(sha256sum tb/tb_proyecto_4.sv | cut -c1-16)...)"
else
  echo "ATENCION: tb/tb_proyecto_4.sv tiene cambios locales"
fi
echo "2000 ticks a 0,1 ms. Referencia de las decisiones: Espino base de rtl/ con sw/trade.hex,"
echo "decisiones.csv con sha256 $(sha256sum "$O/base/decisiones.csv" 2>/dev/null | cut -c1-16)..."
echo
printf "%-15s %-5s %-10s %-9s %-12s %-22s %s\n" configuración 4/4 decisiones "peor caso" patrimonio vigilante "qué es"
fallas=0
for n in $NOMBRES; do
  IFS='|' read -r _ fuentes defs hex mon desc <<< "$(echo "$LISTA" | grep "^$n|")"
  s=$O/$n/salida.txt
  if [ ! -f "$s" ]; then printf "%-15s FAIL no compila o no corrió (ver %s)\n" "$n" "$O/$n/iverilog.log"; fallas=$((fallas + 1)); continue; fi
  if grep -q "Testbenchs aprobados: 4/4" "$s"; then c44=si; else c44=NO; fallas=$((fallas + 1)); fi
  if cmp -s "$O/$n/decisiones.csv" "$O/base/decisiones.csv"; then dec=idénticas; else dec=DISTINTAS; fallas=$((fallas + 1)); fi
  peor=$(grep -iE "peor caso" "$s" | head -1 | grep -oE "[0-9]+" | head -1)
  pat=$(tail -1 "$O/$n/decisiones.csv" 2>/dev/null | awk -F, '{print $NF}')
  vig="-"
  if [ "$mon" = 1 ]; then
    if grep -q "max_sin_respuesta=1 ciclos_con_BOOT=0 " "$O/$n/mon_vigilante.txt" 2>/dev/null; then vig="cuenta 1, BOOT 0"
    else vig="FALLA: $(cat "$O/$n/mon_vigilante.txt" 2>/dev/null | cut -c1-60)"; fallas=$((fallas + 1)); fi
  fi
  printf "%-15s %-5s %-10s %-9s %-12s %-22s %s\n" "$n" "$c44" "$dec" "${peor:-?}" "${pat:-?}" "$vig" "$desc"
done
echo
echo "Definiciones de cada configuración"
for n in $NOMBRES; do
  IFS='|' read -r _ fuentes defs hex mon desc <<< "$(echo "$LISTA" | grep "^$n|")"
  printf "  %-15s fuentes %-7s programa %-55s %s\n" "$n" "$fuentes" "$hex" "${defs:-(sin definiciones)}"
done
echo
echo "Salida completa del testbench oficial con la configuración I1 (i1a)"
[ -f "$O/i1a/salida.txt" ] && grep -v '\$finish' "$O/i1a/salida.txt" | sed 's/^/  /'
[ -f "$O/i1a/mon_vigilante.txt" ] && echo "  monitor del vigilante: $(cat "$O/i1a/mon_vigilante.txt")"
echo
echo "Tiempo de las simulaciones: $((fin - inicio)) s con $JOBS procesos."
if [ $fallas = 0 ]; then echo "RESULTADO: PASS, $(echo "$NOMBRES" | wc -l) configuraciones con 4/4 y decisiones idénticas a las del Espino base"
else echo "RESULTADO: FAIL, $fallas problemas"; fi
}

if [ "$FILTRO" = . ]; then informe | tee "$M/oficial.txt"; grep -q "^RESULTADO: PASS" "$M/oficial.txt"
else informe; fi
