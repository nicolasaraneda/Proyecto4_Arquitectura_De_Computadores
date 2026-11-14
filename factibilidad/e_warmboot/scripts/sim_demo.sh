#!/usr/bin/env bash
# sim_demo.sh: simula las dos imágenes de la prueba de placa.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Dos niveles, con el mismo testbench (tb/tb_wb_demo.v):
#
#   rtl        rtl/wb_demo.v con esperas cortas. Las dos imágenes, los seis
#              escenarios.
#   bitstream  el .asc de cada imagen convertido a Verilog con icebox_vlog
#              (scripts/chip_vlog_wb.py), con las esperas reales: antirrebote
#              de 2^18 ciclos, ping-pong rápido de 2^20 y lento de 2^24. Es
#              lo mismo que queda en el .bin. Las dos imágenes, los seis
#              escenarios.
#
# La reconfiguración no se simula: se comprueba que BOOT, S1 y S0 salen
# cuando corresponde y con el destino correcto, y que la letra, los LED, MISO
# y la UART son los de cada imagen.
#
# Uso, desde la raíz del repositorio (después de construir_demo.sh):
#   factibilidad/e_warmboot/scripts/sim_demo.sh [rtl|bitstream|todo]
# Deja el resultado en mediciones/demo_sim_rtl.txt y demo_sim_bitstream.txt.
set -euo pipefail

QUE=${1:-todo}
E=factibilidad/e_warmboot
D=$E/build/demo
JOBS=${JOBS:-6}
mkdir -p "$D" "$E/mediciones"

resumen() {   # resumen ARCHIVOS_DE_LOG...
  local pass fail
  pass=$(cat "$@" | grep -c '^PASS' || true)
  fail=$(cat "$@" | grep -c '^FAIL' || true)
  local ok falla
  ok=$(cat "$@" | grep -c '^  ok' || true)
  falla=$(cat "$@" | grep -c '^  FALLA' || true)
  echo
  echo "RESUMEN: $pass corridas PASS, $fail FAIL; $ok comprobaciones correctas, $falla con falla"
  [ "$fail" = 0 ] && [ "$falla" = 0 ] && [ "$pass" = "$#" ]
}

if [ "$QUE" = rtl ] || [ "$QUE" = todo ]; then
  for n in 0 1; do
    iverilog -g2012 -DIMG=$n -s tb_wb_demo -o "$D/tb_rtl$n" $E/rtl/wb_demo.v $E/tb/tb_wb_demo.v
    for e in 0 1 2 3 4 5; do
      vvp -n "$D/tb_rtl$n" +escenario=$e > "$D/rtl_i${n}_e$e.log"
    done
  done
  {
    echo "Simulación RTL de las dos imágenes de la prueba de placa"
    echo "Comando: factibilidad/e_warmboot/scripts/sim_demo.sh rtl"
    echo "Esperas cortas: WLento = 16, WRapido = 14, WAntirreb = 8"
    echo
    cat "$D"/rtl_i?_e?.log | grep -v "finish called"
    resumen "$D"/rtl_i?_e?.log
  } | tee $E/mediciones/demo_sim_rtl.txt
fi

if [ "$QUE" = bitstream ] || [ "$QUE" = todo ]; then
  for n in 0 1; do
    python3 $E/scripts/chip_vlog_wb.py "$D/img$n.asc" goboard.pcf -o "$D/chip$n.v"
    iverilog -g2012 -DBITSTREAM -DIMG=$n -DWLENTO=24 -DWRAPIDO=20 -DWANTIRREB=18 \
      -s tb_wb_demo -o "$D/tb_bit$n" "$D/chip$n.v" $E/tb/tb_wb_demo.v
  done
  correr() { vvp -n "$D/tb_bit$1" +escenario=$2 > "$D/bit_i$1_e$2.log"; }
  export -f correr; export D
  for n in 0 1; do for e in 0 1 2 3 4 5; do echo "$n $e"; done; done |
    xargs -P "$JOBS" -L1 bash -c 'correr $0 $1'
  {
    echo "Simulación desde el .asc de las dos imágenes de la prueba de placa"
    echo "Comando: factibilidad/e_warmboot/scripts/sim_demo.sh bitstream"
    echo "icebox_vlog sobre build/demo/img0.asc e img1.asc. Esperas reales:"
    echo "WLento = 24 (16 777 216 ciclos, 0,671 s), WRapido = 20 (1 048 576 ciclos, 41,9 ms), WAntirreb = 18"
    echo
    cat "$D"/bit_i?_e?.log | grep -v "finish called"
    resumen "$D"/bit_i?_e?.log
  } | tee $E/mediciones/demo_sim_bitstream.txt
fi
