#!/usr/bin/env bash
# tb_duplicador.sh: corre tb/tb_duplicador.v con los retardos medidos, en cada esquina y ciclo de trabajo.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Los retardos salen de una corrida de scripts/medir_cadena.sh (por defecto
# la cadena de 8 LUT, modo 0, fija en X1/Y8, semilla 1): ancho del pulso para
# cada flanco y diferencia de latencia entre flancos, en las esquinas
# mínima, típica y máxima de la base de tiempos de icestorm. Se simulan los
# ciclos de trabajo de 45, 50 y 55 % del oscilador de 25 MHz. Al final hay
# dos controles negativos, que tienen que fallar: una cadena más larga que
# el semiperíodo y una cadena demasiado corta.
#
# Uso: scripts/tb_duplicador.sh [STA_JSON]
# Resultado: mediciones/tb_duplicador.txt
source "$(dirname "$0")/comun.sh"

STA=${1:-$B/cadena/m0_n8_fijo_1_8_s1.sta.json}
D=$B/tb_dup
mkdir -p "$D"
[ -f "$STA" ] || { echo "Falta $STA: correr antes scripts/medir_cadena.sh"; exit 1; }

correr() {   # correr NOMBRE ESPERADO ALTO BAJO SUBE BAJA COMUN
  iverilog -g2012 -DSIM_RETARDO -s tb_duplicador -o "$D/$1.vvp" \
    -Ptb_duplicador.AltoPs=$3 -Ptb_duplicador.BajoPs=$4 \
    -Ptb_duplicador.RetSubePs=$5 -Ptb_duplicador.RetBajaPs=$6 -Ptb_duplicador.RetComunPs=$7 \
    "$F/rtl/duplicador_reloj.v" "$F/tb/tb_duplicador.v"
  vvp -n "$D/$1.vvp" > "$D/$1.txt"
  local res; res=$(grep -c "RESULTADO: PASS" "$D/$1.txt" || true)
  local obt=FAIL; [ "$res" = 1 ] && obt=PASS
  local ok="como se esperaba"; [ "$obt" != "$2" ] && ok="DISTINTO DE LO ESPERADO"
  printf "%-26s alto %5d bajo %5d cadena %5d/%5d ps: %s (%s)\n" "$1" "$3" "$4" "$5" "$6" "$obt" "$ok"
  grep -E "Tiempo en alto|FAIL" "$D/$1.txt" | sed 's/^/      /'
  [ "$obt" = "$2" ]
}

{
  echo "Testbench del duplicador (tb/tb_duplicador.v), retardos de $STA"
  echo "Semiperíodos en ps, ya corregidos por la diferencia de latencia entre flancos."
  echo
  mal=0
  while read -r nombre esperado alto bajo sube baja comun; do
    correr "$nombre" "$esperado" "$alto" "$bajo" "$sube" "$baja" "$comun" || mal=$((mal + 1))
  done < <(python3 "$F/scripts/casos_tb.py" "$STA")
  echo
  if [ "$mal" = 0 ]; then echo "TODOS LOS CASOS COMO SE ESPERABA"; else echo "CASOS DISTINTOS DE LO ESPERADO: $mal"; fi
} | tee "$M/tb_duplicador.txt"
grep -q "TODOS LOS CASOS COMO SE ESPERABA" "$M/tb_duplicador.txt"
