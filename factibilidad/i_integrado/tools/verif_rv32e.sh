#!/usr/bin/env bash
# verif_rv32e.sh: cada hilo del barrel integrado contra el Espino base,
# instrucción por instrucción, para las instrucciones de RV32E.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# La pregunta es si agregar la extensión, el vigilante y la memoria de la
# tabla rompió algo de lo que el barrel ya hacía bien. Se responde con el
# mismo método con que se verificó el prototipo (factibilidad/a_barrel,
# sección 6 de su README), sin copiarlo: se compila tb/tb_verif.sv de ese
# estudio, sin modificar, con el SoC y el core de esta carpeta en lugar de
# los del prototipo. El testbench instancia el barrel y cuatro SoC originales
# con el Espino base (rtl/, sin tocar), uno por hilo, y compara cada
# instrucción completada: contador de programa, escritura al banco, acceso al
# bus, los 16 registros del contexto y la palabra de memoria o el registro de
# periférico escrito. Al final compara la memoria completa.
#
# Configuraciones del barrel que se comparan (el hardware nuevo está presente
# en todas menos en la primera, aunque los programas son de RV32E):
#   ref           sin definiciones (control: es el prototipo)
#   media_mul     (b) emad, devk y mulstep en el sumador de la ALU
#   alu_todo_div  (c) y (e): xd_alu en vez de espino_alu, más divstep
#   media_bandas  (d) carriles en unidad aparte
#   i1a           I1: (b) con vigilante y tabla de 256 x 16
#   i1b           I1 con la tabla en otras 512 palabras de datos
#
# Grupos de corridas, los de a_barrel/tools/verif.sh con menos semillas:
#   U  un hilo con un programa aleatorio y los otros tres en un lazo vacío
#   H  sw/hazard_test.s y sw/hazard_review.s en cada hilo
#   B  cuatro hilos a la vez, zonas de datos separadas
#   C  cuatro hilos, uno solo con el SPI y precios nuevos
#   T  sw/trade.s en un hilo y programas aleatorios en los otros tres
#   D  cuatro hilos sobre la misma zona de datos
# Los programas pasan por tools/sin_custom0.py: las palabras con el opcode
# custom-0, que en el Espino base no hacen nada y aquí son instrucciones, se
# reemplazan por nop. Las instrucciones nuevas se prueban con tools/tb_xd.sh.
#
# Uso: factibilidad/i_integrado/tools/verif_rv32e.sh [FILTRO]  (o make verif)
# Resultado en mediciones/verif_rv32e.txt (si no hay FILTRO). Unos 3 minutos,
# casi todo compilando con Verilator.
# Variables: ESCALA (multiplica las semillas, por defecto 1) y JOBS (5).
set -uo pipefail
source "$(dirname "$0")/comun.sh"
source "$I/tools/verif_comun.sh"

FILTRO=${1:-.}
O=$B/verif
JOBS=${JOBS:-5}
ESCALA=${ESCALA:-1}
mkdir -p "$O/prog"

esc() { $PYTHON -c "import sys; print(max(1, round(float(sys.argv[1]) * float(sys.argv[2]))))" "$1" "$ESCALA"; }
SEM_U=$(esc 5);  INSTR_U=6000      # por hilo: 4 x SEM_U corridas
SEM_B=$(esc 10); INSTR_B=5000
SEM_C=$(esc 3);  INSTR_C=5000      # por hilo con el SPI
SEM_T=$(esc 2);  INSTR_T=5000      # por hilo con trade.s
SEM_D=$(esc 10); INSTR_D=5000
INSTR_H=1500

preparar_spi "$O" || exit 1

# programa GRUPO SEMILLA HILO: genera, limpia y ensambla el programa (una vez
# para todas las configuraciones). Deja prog/G_sS_hT.hex.
programa() {
  local g=$1 s=$2 t=$3 n=$O/prog/$1_s$2_h$3
  case $g in
    U) $PYTHON $A/tools/prog_hilos.py "$s" --modo uno --hilo-spi "$t" -n 300 -o "$n.orig.s" ;;
    H) local p=hazard_test; [ "$s" = 2 ] && p=hazard_review
       $PYTHON $A/tools/tabla.py "$t" sw/$p.s > "$n.orig.s" ;;
    B) $PYTHON $A/tools/prog_hilos.py "$s" --modo separado -o "$n.orig.s" ;;
    C) $PYTHON $A/tools/prog_hilos.py "$s" --modo spi1 --hilo-spi "$t" -o "$n.orig.s" ;;
    T) $PYTHON $A/tools/prog_hilos.py "$s" --modo trade --hilo-spi "$t" --trade sw/trade.s -n 90 -o "$n.orig.s" ;;
    D) $PYTHON $A/tools/prog_hilos.py "$s" --modo compartido -o "$n.orig.s" ;;
  esac
  $PYTHON $I/tools/sin_custom0.py "$n.orig.s" > "$n.s" 2> "$n.filtro.txt"
  $PYTHON tools/pochoasm.py --allow-shifts "$n.s" -o "$n.hex" > /dev/null 2> "$n.asm.log"
  return 0
}
# una CONFIG GRUPO SEMILLA HILO: corre la comparación
una() {
  local c=$1 g=$2 s=$3 t=$4 args
  case $g in
    U) args="+instrucciones=$INSTR_U +precio_cada=97 +hilo_spi=$t" ;;
    H) args="+instrucciones=$INSTR_H" ;;
    B) args="+instrucciones=$INSTR_B" ;;
    C) args="+instrucciones=$INSTR_C +precio_cada=29 +hilo_spi=$t" ;;
    T) args="+instrucciones=$INSTR_T +precio_cada=61 +hilo_spi=$t" ;;
    D) args="+instrucciones=$INSTR_D +compartida=1" ;;
  esac
  mkdir -p "$O/$c/logs/$g"
  "$O/$c/obj/sim" "+hex=$O/prog/${g}_s${s}_h${t}.hex" $args > "$O/$c/logs/$g/${g}_s${s}_h${t}.log" 2>&1
  return 0
}
export -f programa una
export O A I PYTHON INSTR_U INSTR_B INSTR_C INSTR_T INSTR_D INSTR_H

MEDIA="$(defs_de media_mul)"
CONFIGS=$(cat <<FIN
ref||sin definiciones: es el prototipo del barrel (control)
media_mul|$MEDIA|(b) emad, devk y mulstep en el sumador de la ALU
alu_todo_div|$(defs_de alu_todo_div)|(c) y (e): xd_alu en vez de espino_alu, más divstep
media_bandas|$(defs_de media_bandas)|(d) carriles de bandas en unidad aparte
i1a|$MEDIA -DI_VIGILANTE -DI_TABLA=1|I1: (b) con vigilante y tabla de 256 x 16
i1b|$MEDIA -DI_VIGILANTE -DI_TABLA=2|I1 con la tabla en otras 512 palabras de datos
FIN
)
CONFIGS=$(echo "$CONFIGS" | grep -E "^($FILTRO)" || true)
[ -n "$CONFIGS" ] || { echo "verif_rv32e.sh: ningún nombre calza con $FILTRO"; exit 1; }
NOMBRES=$(echo "$CONFIGS" | cut -d'|' -f1)

# Lista de corridas (la misma para todas las configuraciones)
: > "$O/corridas.txt"
lista() { local g=$1 n=$2; shift 2; for t in "$@"; do for s in $(seq 1 "$n"); do echo "$g $s $t" >> "$O/corridas.txt"; done; done; }
lista U "$SEM_U" 0 1 2 3
lista H 2 0 1 2 3
lista B "$SEM_B" x
lista C "$SEM_C" 0 1 2 3
lista T "$SEM_T" 0 1 2 3
lista D "$SEM_D" x

xargs -P "$JOBS" -L 1 bash -c 'programa "$0" "$1" "$2"' < "$O/corridas.txt"
cat "$O"/prog/*.filtro.txt | awk '{c += $1; d += $6} END {printf "%d palabras de codigo y %d de datos con opcode custom-0 reemplazadas en %d programas\n", c, d, NR}' > "$O/filtro_total.txt"

# Compilación, una por configuración, hasta JOBS a la vez
while IFS='|' read -r c defs desc; do
  echo "$defs" > "$O/$c.defs"
done <<< "$CONFIGS"
compilar_config() { compilar_verif "$O/$1" "$(cat "$O/$1.defs")"; }
export -f compilar_config
echo "$NOMBRES" | xargs -P "$JOBS" -I{} bash -c 'compilar_config {}'
for c in $NOMBRES; do
  if [ ! -x "$O/$c/obj/sim" ] || grep -q "^%Error" "$O/$c/verilator.log"; then
    echo "FAIL verif: tb_verif no compila con la configuracion $c (ver $O/$c/verilator.log)"; grep -m5 "^%Error" "$O/$c/verilator.log"; exit 1
  fi
done

inicio=$(date +%s)
for c in $NOMBRES; do
  mkdir -p "$O/$c/logs"
  find "$O/$c/logs" -name '*.log' -delete
  sed "s/^/$c /" "$O/corridas.txt"
done | xargs -P "$JOBS" -L 1 bash -c 'una "$0" "$1" "$2" "$3"'
fin=$(date +%s)

informe() {
echo "Cada hilo del barrel integrado contra el Espino base, instruccion por instruccion (instrucciones de RV32E)"
echo "Generado por factibilidad/i_integrado/tools/verif_rv32e.sh (make verif). No editar a mano."
echo
versiones
echo "  $(verilator --version)"
echo "Testbench: $A/tb/tb_verif.sv, sin modificar (sha256 $(sha256sum $A/tb/tb_verif.sv | cut -c1-16)...)."
echo "Programas: $(wc -l < "$O/corridas.txt") por configuracion, los mismos para todas. $(cat "$O/filtro_total.txt")."
echo
fallas=0; resumen=""
while IFS='|' read -r c defs desc; do
  echo "=================================================================================================="
  echo "Configuracion $c: $desc"
  echo "Definiciones: ${defs:-(ninguna)}"
  echo
  $PYTHON $A/tools/resumen_verif.py "$O/$c/logs" "$O/corridas.txt" > "$O/$c/resumen.txt"; rc=$?
  cat "$O/$c/resumen.txt"
  [ $rc = 0 ] || fallas=$((fallas + 1))
  tot=$(grep -E "^   total:" "$O/$c/resumen.txt" | sed -E 's/^   total: +([0-9 ]+[0-9]) +de ellas distintas: +([0-9 ]+[0-9]).*/\1|\2/')
  resumen="$resumen$(printf '   %-13s %-5s %14s %14s   %s' "$c" "$([ $rc = 0 ] && echo PASS || echo FAIL)" "${tot%%|*}" "${tot##*|}" "$desc")"$'\n'
done <<< "$CONFIGS"
echo "=================================================================================================="
echo "Resumen por configuracion: instrucciones de programa comparadas una por una y cuantas de ellas son distintas"
printf '   %-13s %-5s %14s %14s\n' configuracion "" instrucciones distintas
printf '%s' "$resumen"
echo
echo "Tiempo de las simulaciones: $((fin - inicio)) s con $JOBS procesos."
if [ $fallas = 0 ]; then echo "RESULTADO GENERAL: PASS, cero diferencias con el Espino base en las $(echo "$CONFIGS" | wc -l) configuraciones"
else echo "RESULTADO GENERAL: FAIL, $fallas configuraciones con diferencias"; fi
}

if [ "$FILTRO" = . ]; then informe | tee "$M/verif_rv32e.txt"; grep -q "^RESULTADO GENERAL: PASS" "$M/verif_rv32e.txt"
else informe; fi
