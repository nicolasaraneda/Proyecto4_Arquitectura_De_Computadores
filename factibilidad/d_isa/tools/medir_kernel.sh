#!/usr/bin/env bash
# medir_kernel.sh: kernel de cuatro bandas, escalar contra carriles, medido en el core.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Ensambla sw/bandas_vacio.s, sw/bandas_escalar.s y sw/bandas_carriles.s, los
# corre en la copia del SoC (core/ con -DXD_SIMD=28) con tb/tb_xd_kernel.sv, en
# el Espino base y en el segmentado, y compara los 256 resultados de cada uno
# con el modelo tools/kernel_bandas.py. Informa instrucciones y ciclos por
# vuelta, el costo del kernel solo (restando el lazo vacío) y el speedup.
#
# Uso, desde factibilidad/d_isa:   tools/medir_kernel.sh > mediciones/kernel_bandas.txt
set -euo pipefail
cd "$(dirname "$0")/.."
B=build/kernel
mkdir -p "$B" build/sw
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v
SRC="$(echo core/*.v core/espino_core/*.v rtl/xd_*.v)"
DEFS="-DXD_SIMD=28"
N=256
FALLAS=0

echo "Kernel de cuatro bandas: instrucciones de RV32E contra carriles de 4 x 8 bits"
echo "Generado por factibilidad/d_isa/tools/medir_kernel.sh (make kernel). No editar a mano."
echo
python3 tools/kernel_bandas.py
echo "Programas sw/bandas_*.s en la copia del SoC (core/ con $DEFS), Icarus Verilog. $N vueltas del lazo."
echo "Ciclos e instrucciones entre la primera y la última escritura a MARCA (tb/tb_xd_kernel.sv)."
echo
printf "%-11s %-16s %-6s %8s %8s %10s %10s\n" core programa modelo instr ciclos "instr/vta" "ciclos/vta"

declare -A CIC INS
for core in base segmentado; do
  cdef=""; [ "$core" = segmentado ] && cdef="-DESPINO_SEGMENTADO"
  for prog in bandas_vacio bandas_escalar bandas_carriles; do
    python3 tools/xd_word.py --pre "sw/$prog.s" -o "build/sw/$prog.s" > /dev/null
    python3 ../../tools/pochoasm.py "build/sw/$prog.s" -o "build/sw/$prog.hex" > /dev/null
    iverilog -g2012 -s tb_xd_kernel $cdef $DEFS "-DPROGRAMA=\"build/sw/$prog.hex\"" \
      "-DRESULTADOS=\"$B/${core}_$prog.res\"" -o "$B/${core}_$prog.vvp" "$CELLS_SIM" $SRC tb/tb_xd_kernel.sv
    vvp -n "$B/${core}_$prog.vvp" > "$B/${core}_$prog.log" 2>&1 || true
    linea=$(grep "^MEDIDO" "$B/${core}_$prog.log" || echo "MEDIDO ciclos=0 instrucciones=0")
    c=$(echo "$linea" | sed -E 's/.*ciclos=([0-9]+).*/\1/'); i=$(echo "$linea" | sed -E 's/.*instrucciones=([0-9]+).*/\1/')
    vacio=""; [ "$prog" = bandas_vacio ] && vacio="--vacio"
    if python3 tools/kernel_bandas.py --comparar "$B/${core}_$prog.res" $vacio > "$B/${core}_$prog.cmp" 2>&1; then m=igual; else m=FAIL; FALLAS=$((FALLAS + 1)); fi
    CIC[$core,$prog]=$c; INS[$core,$prog]=$i
    printf "%-11s %-16s %-6s %8s %8s %10s %10s\n" "$core" "$prog" "$m" "$i" "$c" \
      "$(awk -v x="$i" -v n=$N 'BEGIN {printf "%.2f", x / n}')" "$(awk -v x="$c" -v n=$N 'BEGIN {printf "%.2f", x / n}')"
  done
done

echo
echo "Kernel solo (restando el lazo vacío, que hace una instrucción, mv, en su lugar):"
printf "%-11s %-10s %12s %12s %14s\n" core versión "instr/vta" "ciclos/vta" "MOPS (1)"
for core in base segmentado; do
  for prog in bandas_escalar bandas_carriles; do
    awk -v core="$core" -v prog="${prog#bandas_}" -v i="${INS[$core,$prog]}" -v c="${CIC[$core,$prog]}" \
        -v i0="${INS[$core,bandas_vacio]}" -v c0="${CIC[$core,bandas_vacio]}" -v n=$N \
        -v ciclos_mv="$([ "$core" = base ] && echo 2 || echo 1)" 'BEGIN {
      ki = (i - i0) / n + 1; kc = (c - c0) / n + ciclos_mv;
      printf "%-11s %-10s %12.2f %12.2f %14.2f\n", core, prog, ki, kc, 4 * 25 / kc }'
  done
done
echo
echo "Speedup medido del kernel (ciclos por vuelta del escalar sobre los de carriles):"
for core in base segmentado; do
  awk -v core="$core" -v ce="${CIC[$core,bandas_escalar]}" -v cc="${CIC[$core,bandas_carriles]}" \
      -v c0="${CIC[$core,bandas_vacio]}" -v n=$N -v mv="$([ "$core" = base ] && echo 2 || echo 1)" 'BEGIN {
    ke = (ce - c0) / n + mv; kc = (cc - c0) / n + mv;
    printf "  %-11s kernel solo %.2f / %.2f = %.2f      vuelta completa del lazo %.2f / %.2f = %.2f\n", core, ke, kc, ke / kc, ce / n, cc / n, ce / cc }'
done
echo "Predicho por conteo de instrucciones: 30 / 8 = 3.75 (todas son de un ciclo de ejecución, sin loads ni saltos)."
echo
echo "(1) Operaciones útiles por segundo, en millones: una operación es evaluar una banda (entrar, salir y"
echo "    actualizar la posición de una estrategia). El kernel hace 4 por vuelta: MOPS = 4 x 25 MHz / ciclos."
if [ "$FALLAS" != 0 ]; then echo "FAIL: $FALLAS corridas no coinciden con el modelo"; exit 1; fi
echo "PASS: las seis corridas entregan los resultados del modelo"
