#!/usr/bin/env bash
# oficial.sh: el testbench oficial sin modificar, repetido para la auditoría.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Compila tb/tb_proyecto_4.sv tal como está, con el comando de su encabezado
# (iverilog -g2012 -s tb_proyecto_4 ... cells_sim.v FUENTES tb/tb_proyecto_4.sv)
# y las listas de fuentes de tools/comun.sh de esta carpeta. Cada corrida se
# hace en su propia carpeta, con el programa puesto como sw/trade.hex.
#
#   base       Espino base de rtl/ con sw/trade.hex (referencia de las decisiones)
#   i1a        I1 con la regla base en el hilo 0            debe decidir igual que base
#   i2         I2 con la regla base en el hilo 0            debe decidir igual que base
#   i3a        I3 con sw/trade.hex                          debe decidir igual que base
#   fondo      el fondo (sw/fondo.s) en el barrel prototipo debe decidir igual que fondo_min en C
#   fondo_i1a  el fondo en el hardware I1: la configuración "fondo en un chip"
#              completa, que ninguna de las dos piezas había corrido junta
#
# En las configuraciones con vigilante se agrega el monitor de e_warmboot como
# segundo módulo raíz: BOOT no debe subir y la cuenta no debe pasar de 1.
#
# Uso: factibilidad/auditoria_hw/tools/oficial.sh   (o make oficial)
# Resultado en mediciones/oficial.txt. Unos 6 minutos con 5 procesos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"
arnes || exit 1

O=$B/oficial
mkdir -p "$O"
regla_base_h0 "$O/trade_h0.hex" || exit 1
$PYTHON tools/pochoasm.py $F/sw/fondo.s -o "$O/fondo.hex" > /dev/null || exit 1

# nombre | fuentes | definiciones | programa | monitor | referencia | qué es
LISTA="base|$SRC_BASE||sw/trade.hex|0|-|Espino base de rtl/ con sw/trade.hex
i1a|$SRC_I|$DEFS_I1A|$O/trade_h0.hex|1|base|I1 con la regla base en el hilo 0
i2|$SRC_I|$DEFS_I2|$O/trade_h0.hex|1|base|I2 con la regla base en el hilo 0
i3a|$SRC_SEG|$DEFS_I3A|sw/trade.hex|1|base|I3 (segmentado, emad y vigilante) con sw/trade.hex
fondo|$SRC_BARREL_PROTO||$O/fondo.hex|0|fondo_min|El fondo de cuatro hilos en el barrel prototipo
fondo_i1a|$SRC_I|$DEFS_I1A|$O/fondo.hex|1|fondo_min|El fondo de cuatro hilos en el hardware I1 (fondo en un chip)"

una() {
  local n=$1 src defs hex mon ref desc
  IFS='|' read -r _ src defs hex mon ref desc <<< "$(echo "$LISTA" | grep "^$n|")"
  rm -rf "${O:?}/${n:?}"; mkdir -p "$O/$n/sw" "$O/$n/tb"
  ln -s "$RAIZ/tb/practica.csv" "$O/$n/tb/practica.csv"
  cp "$hex" "$O/$n/sw/trade.hex"
  if [ "$mon" = 1 ]; then
    iverilog -g2012 $defs -s tb_proyecto_4 -s mon_vigilante -o "$O/$n/sim" "$CELLS_SIM" $src tb/tb_proyecto_4.sv $E/tb/mon_vigilante.sv > "$O/$n/iverilog.log" 2>&1 || return 0
  else
    iverilog -g2012 $defs -s tb_proyecto_4 -o "$O/$n/sim" "$CELLS_SIM" $src tb/tb_proyecto_4.sv > "$O/$n/iverilog.log" 2>&1 || return 0
  fi
  ( cd "$O/$n" && vvp -n sim > salida.txt 2>&1 )
  return 0
}
export -f una
export O LISTA CELLS_SIM RAIZ E

T0=$(date +%s)
echo "$LISTA" | cut -d'|' -f1 | xargs -P "$JOBS" -I{} bash -c 'una {}'
T1=$(date +%s)
"$ARNES" correr --estrategia fondo_min --serie tb/practica.csv --nticks 2000 --perdidos "$(perdidos 100000)" -o "$O/ref_fondo.csv" > "$O/ref_fondo.txt" 2>&1

{
echo "Auditoría: testbench oficial sin modificar"
echo "Generado por factibilidad/auditoria_hw/tools/oficial.sh (make oficial). No editar a mano."
echo
versiones
if git diff --quiet HEAD -- tb/tb_proyecto_4.sv; then
  echo "tb/tb_proyecto_4.sv: sin cambios respecto de HEAD (sha256 $(sha256sum tb/tb_proyecto_4.sv | cut -c1-16)...)"
else
  echo "FAIL tb/tb_proyecto_4.sv tiene cambios locales"
fi
echo "Simulador: Icarus Verilog, 2000 ticks a 0,1 ms. Demora: $((T1 - T0)) s con $JOBS procesos."
echo "Referencia de la regla base: decisiones.csv del Espino base (sha256 $(sha256sum "$O/base/decisiones.csv" 2>/dev/null | cut -c1-16)...)."
echo "Referencia del fondo: fondo_min en C, $(perdidos 100000) precios sin ver por el reset (sha256 $(sha256sum "$O/ref_fondo.csv" | cut -c1-16)...)."
echo
printf "%-10s %-5s %-28s %-9s %-10s %-8s %-18s %s\n" config 4/4 decisiones "peor caso" patrimonio órdenes vigilante "qué es"
fallas=0
for n in $(echo "$LISTA" | cut -d'|' -f1); do
  IFS='|' read -r _ src defs hex mon ref desc <<< "$(echo "$LISTA" | grep "^$n|")"
  s=$O/$n/salida.txt
  if [ ! -f "$s" ]; then printf "%-10s FAIL no compila o no corrió\n" "$n"; fallas=$((fallas + 1)); continue; fi
  if grep -q "Testbenchs aprobados: 4/4" "$s"; then c=si; else c=NO; fallas=$((fallas + 1)); fi
  case $ref in
    -)         dec="(referencia)" ;;
    base)      if cmp -s "$O/$n/decisiones.csv" "$O/base/decisiones.csv"; then dec="idénticas a base"; else dec="DISTINTAS de base"; fallas=$((fallas + 1)); fi ;;
    fondo_min) if cmp -s "$O/$n/decisiones.csv" "$O/ref_fondo.csv"; then dec="idénticas a fondo_min en C"; else dec="DISTINTAS de fondo_min"; fallas=$((fallas + 1)); fi ;;
  esac
  v="-"
  if [ "$mon" = 1 ]; then
    if grep -q "max_sin_respuesta=1 ciclos_con_BOOT=0 " "$O/$n/mon_vigilante.txt" 2>/dev/null; then v="cuenta 1, BOOT 0"; else v="FALLA"; fallas=$((fallas + 1)); fi
  fi
  printf "%-10s %-5s %-28s %-9s %-10s %-8s %-18s %s\n" "$n" "$c" "$dec" "$(grep -i 'peor caso' "$s" | grep -oE '[0-9]+' | head -1)" \
    "$(grep 'Patrimonio final' "$s" | grep -oE '[0-9]+')" "$(grep 'Ordenes' "$s" | grep -oE '[0-9]+')" "$v" "$desc"
done
echo
echo "Salida completa del testbench oficial con el fondo en el hardware I1 (fondo_i1a)"
grep -v '\$finish' "$O/fondo_i1a/salida.txt" 2>/dev/null | sed 's/^/  /'
echo "  monitor del vigilante: $(cat "$O/fondo_i1a/mon_vigilante.txt" 2>/dev/null)"
echo
if [ $fallas = 0 ]; then echo "RESULTADO: PASS, las seis corridas dan 4/4 y las decisiones esperadas"
else echo "RESULTADO: FAIL, $fallas problemas"; fi
} | tee "$M/oficial.txt"

grep -q "^RESULTADO: PASS" "$M/oficial.txt"
