#!/usr/bin/env bash
# mixto.sh: la regla base en el hilo 0 con el testbench oficial, mientras los
# otros tres hilos ejecutan instrucciones nuevas sin parar.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Es la forma de uso del fondo de estrategias: un hilo supervisor que atiende
# a la maestra con instrucciones de RV32E y tres hilos que calculan con la
# extensión. Las otras pruebas cubren cada mitad por separado (tools/tb_xd.sh
# las instrucciones nuevas, tools/verif_rv32e.sh las de RV32E). Esta las junta
# y mira las dos direcciones:
#   - el testbench oficial, sin modificar, tiene que entregar 4/4 y un
#     decisiones.csv idéntico byte a byte al del Espino base. Si una
#     instrucción nueva de otro hilo alterara un load, un store, un salto o un
#     acceso al SPI del hilo 0, las decisiones cambiarían;
#   - tb/mon_mixto.sv, compilado como segundo módulo raíz, compara cada
#     pareja (suma, vuelta) que publican los hilos 1, 2 y 3 con la que predice
#     tools/modelo_kernel.py usando el modelo ref/xd.py de d_isa;
#   - el vigilante no debe disparar (tb/mon_vigilante.sv de e_warmboot).
#
# Corridas (2000 ticks a 0,1 ms cada una):
#   media        I1 (emad, devk, mulstep, vigilante y tabla). Hilo 0: sw/trade.s.
#                Hilos 1 a 3: sw/kernel_media.s.
#   media_xd     Lo mismo con la regla base escrita con devk y emad en el hilo
#                0 (sw/trade_media.s de d_isa): los cuatro hilos usan la
#                extensión.
#   carriles     I1 más los carriles en el sumador de la ALU (xd_alu). Hilo 0:
#                sw/trade.s. Hilos 1 a 3: sw/kernel_carriles.s.
#   base         El Espino base de rtl/ con sw/trade.hex: la referencia.
#
# Uso: factibilidad/i_integrado/tools/mixto.sh   (o make mixto)
# Resultado en mediciones/mixto.txt. Unos 5 minutos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/mixto
JOBS=${JOBS:-5}
VUELTAS=200000
# Vueltas mínimas que debe haber comparado el hilo 1 para dar la prueba por
# buena. En 2000 ticks a 0,1 ms cada hilo ejecuta cerca de 1 250 000
# instrucciones: unas 155 000 vueltas de kernel_media.s (8 instrucciones por
# vuelta) y unas 95 000 de kernel_carriles.s (13 por vuelta).
MIN_VUELTAS=90000
mkdir -p "$O"
programas
MEDIA="$(defs_de media_mul)"

# Programas: kernel (tabla de arranque y hilos 1 a 3) + programa del hilo 0
armar() {   # armar NOMBRE KERNEL.s PROGRAMA_HILO0.s
  local n=$1 k=$2 p=$3
  cat "$k" "$p" > "$O/$n.xd.s"
  $PYTHON $D/tools/xd_word.py --pre "$O/$n.xd.s" -o "$O/$n.s" > "$O/$n.pre.log"
  ensamblar "$O/$n.s" "$O/$n.hex"
}
armar media    $I/sw/kernel_media.s    sw/trade.s          || { echo "FAIL mixto: no ensambla media"; exit 1; }
armar media_xd $I/sw/kernel_media.s    $D/sw/trade_media.s || { echo "FAIL mixto: no ensambla media_xd"; exit 1; }
armar carriles $I/sw/kernel_carriles.s sw/trade.s          || { echo "FAIL mixto: no ensambla carriles"; exit 1; }
$PYTHON $I/tools/modelo_kernel.py media    $VUELTAS "$O/esp_media"    > /dev/null &
$PYTHON $I/tools/modelo_kernel.py carriles $VUELTAS "$O/esp_carriles" > /dev/null &
wait

# una NOMBRE: compila y corre el testbench oficial con los dos monitores
una() {
  local n=$1 defs hex esp
  case $n in
    base)     defs="";                                             hex=sw/trade.hex ;;
    media)    defs="$MEDIA -DI_VIGILANTE -DI_TABLA=1";             hex=$O/media.hex;    esp=$O/esp_media ;;
    media_xd) defs="$MEDIA -DI_VIGILANTE -DI_TABLA=1";             hex=$O/media_xd.hex; esp=$O/esp_media ;;
    carriles) defs="$(defs_de alu_todo) -DI_VIGILANTE -DI_TABLA=1"; hex=$O/carriles.hex; esp=$O/esp_carriles ;;
  esac
  rm -rf "${O:?}/run_${n:?}"; mkdir -p "$O/run_$n/sw" "$O/run_$n/tb"
  ln -s "$RAIZ/tb/practica.csv" "$O/run_$n/tb/practica.csv"
  cp "$hex" "$O/run_$n/sw/trade.hex"
  if [ "$n" = base ]; then
    iverilog -g2012 -s tb_proyecto_4 -o "$O/run_$n/sim" "$CELLS_SIM" $BASE_SRC tb/tb_proyecto_4.sv > "$O/run_$n/iverilog.log" 2>&1 || return 0
  else
    iverilog -g2012 $defs "-DESP_PREFIJO=\"$RAIZ/$esp\"" -DVUELTAS_MAX=$VUELTAS -s tb_proyecto_4 -s mon_vigilante -s mon_mixto \
      -o "$O/run_$n/sim" "$CELLS_SIM" $INT_SRC tb/tb_proyecto_4.sv $E/tb/mon_vigilante.sv $I/tb/mon_mixto.sv > "$O/run_$n/iverilog.log" 2>&1 || return 0
  fi
  ( cd "$O/run_$n" && vvp -n sim > salida.txt 2>&1 )
  return 0
}
export -f una defs_de
export O MEDIA VUELTAS BASE_SRC INT_SRC CELLS_SIM RAIZ E I

inicio=$(date +%s)
printf 'base\nmedia\nmedia_xd\ncarriles\n' | xargs -P "$JOBS" -I{} bash -c 'una {}'
fin=$(date +%s)

{
echo "Prueba mixta: la regla base en el hilo 0 con el testbench oficial y tres hilos ejecutando instrucciones nuevas"
echo "Generado por factibilidad/i_integrado/tools/mixto.sh (make mixto). No editar a mano."
echo
versiones
echo "tb/tb_proyecto_4.sv sin modificar (sha256 $(sha256sum tb/tb_proyecto_4.sv | cut -c1-16)...), 2000 ticks a 0,1 ms."
echo "Referencia de las decisiones: Espino base de rtl/ con sw/trade.hex ($(grep -o 'Testbenchs aprobados: ./.' "$O/run_base/salida.txt" 2>/dev/null))."
echo
fallas=0
for n in media media_xd carriles; do
  case $n in
    media)    desc="I1; hilo 0 con sw/trade.s; hilos 1 a 3 con mulstep, emad y devk (sw/kernel_media.s)" ;;
    media_xd) desc="I1; hilo 0 con la regla base escrita con devk y emad; hilos 1 a 3 con mulstep, emad y devk" ;;
    carriles) desc="I1 más carriles en la ALU; hilo 0 con sw/trade.s; hilos 1 a 3 con seis operaciones de carril y emad (sw/kernel_carriles.s)" ;;
  esac
  s=$O/run_$n/salida.txt
  echo "--- $n: $desc"
  if [ ! -f "$s" ]; then echo "   FAIL no compila o no corrió (ver $O/run_$n/iverilog.log)"; fallas=$((fallas + 1)); continue; fi
  if grep -q "Testbenchs aprobados: 4/4" "$s"; then echo "   PASS testbench oficial 4/4, $(grep -i 'peor caso' "$s" | sed 's/^ *//')"
  else echo "   FAIL el testbench oficial no entrega 4/4"; fallas=$((fallas + 1)); fi
  if cmp -s "$O/run_$n/decisiones.csv" "$O/run_base/decisiones.csv"; then echo "   PASS decisiones.csv idéntico byte a byte al del Espino base (patrimonio $(tail -1 "$O/run_$n/decisiones.csv" | awk -F, '{print $NF}'))"
  else echo "   FAIL decisiones.csv difiere del Espino base"; fallas=$((fallas + 1)); fi
  m=$(cat "$O/run_$n/mon_mixto.txt" 2>/dev/null)
  v1=$(echo "$m" | sed -n 's/.*vueltas_h1=\([0-9]*\).*/\1/p'); er=$(echo "$m" | sed -n 's/.*errores=\([0-9]*\).*/\1/p')
  if [ "${er:-1}" = 0 ] && [ "${v1:-0}" -gt "$MIN_VUELTAS" ]; then echo "   PASS hilos de estrategia iguales al modelo: $m"
  else echo "   FAIL hilos de estrategia: ${m:-sin resumen}"; fallas=$((fallas + 1)); fi
  if grep -q "max_sin_respuesta=1 ciclos_con_BOOT=0 " "$O/run_$n/mon_vigilante.txt" 2>/dev/null; then echo "   PASS vigilante: $(cat "$O/run_$n/mon_vigilante.txt")"
  else echo "   FAIL vigilante: $(cat "$O/run_$n/mon_vigilante.txt" 2>/dev/null)"; fallas=$((fallas + 1)); fi
  grep -h "^mon_mixto:" "$s" | head -3 | sed 's/^/   /'
done
echo
echo "Tiempo de las simulaciones: $((fin - inicio)) s."
if [ $fallas = 0 ]; then echo "RESULTADO: PASS"; else echo "RESULTADO: FAIL, $fallas problemas"; fi
} | tee "$M/mixto.txt"

grep -q "^RESULTADO: PASS" "$M/mixto.txt"
