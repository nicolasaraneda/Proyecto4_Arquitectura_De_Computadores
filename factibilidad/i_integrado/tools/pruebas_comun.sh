# pruebas_comun.sh: compilar y correr las pruebas cortas del diseño integrado
# con el RTL de esta carpeta o con una copia mutada. Lo comparten
# tools/tabla.sh, tools/vigilante.sh y tools/mutaciones.sh.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se incluye con "source" después de tools/comun.sh. Cada función deja sus
# productos en la carpeta que se le pasa, imprime la línea PASS o FAIL de su
# testbench y devuelve 0 si pasó. El último argumento, opcional, es la carpeta
# con los cuatro archivos propios del SoC (por defecto rtl/ de este estudio).

# programas_prueba: ensambla en B/sw los programas de estas pruebas
programas_prueba() {
  ensamblar $I/sw/tabla_prueba.s "$B/sw/tabla_prueba_1.hex" -D TAB_BASE=0x80020000 -D Q=64  -D QBYTES=256
  ensamblar $I/sw/tabla_prueba.s "$B/sw/tabla_prueba_2.hex" -D TAB_BASE=0x800      -D Q=128 -D QBYTES=512
  ensamblar $I/sw/cuelgue_supervisor.s "$B/sw/cuelgue_supervisor.hex" -D K=20
  # Contenido inicial de prueba para tabla_mmio: 3 i + 1
  $PYTHON -c "print(''.join(f'{3 * i + 1:04x}\n' for i in range(256)), end='')" > "$B/sw/tabla_init.hex"
}

# correr_tabla DIR FORMA [RTL]: sw/tabla_prueba.s en el SoC con la memoria de
# la tabla en la forma 1 o 2
correr_tabla() {
  local d=$1 forma=$2 r=${3:-$I/rtl} extra=""
  mkdir -p "$d"
  [ "$forma" = 2 ] && extra="-DTB_TABLA_FORMA_2"
  iverilog -g2012 -s tb_tabla -DI_TABLA="$forma" $extra ${DEFS_PRUEBA:-} -o "$d/tabla$forma.vvp" "$CELLS_SIM" $(int_src "$r") $I/tb/tb_tabla.sv > "$d/tabla$forma.iverilog.log" 2>&1 \
    || { echo "FAIL tb_tabla forma $forma: no compila"; return 1; }
  vvp -n "$d/tabla$forma.vvp" "+hex=$B/sw/tabla_prueba_$forma.hex" > "$d/tabla$forma.log" 2>&1
  grep -E "^(PASS|FAIL) tb_tabla" "$d/tabla$forma.log" || echo "FAIL tb_tabla forma $forma: sin resultado"
  grep -q "^PASS tb_tabla" "$d/tabla$forma.log"
}

# correr_tabla_mod DIR [RTL]: los dos módulos solos, con accesos al azar
correr_tabla_mod() {
  local d=$1 r=${2:-$I/rtl}
  mkdir -p "$d"
  iverilog -g2012 -s tb_tabla_mod "-DTABLA_INIT=\"$B/sw/tabla_init.hex\"" -o "$d/tabla_mod.vvp" "$r/tabla_mmio.v" "$r/tabla_ram.v" $I/tb/tb_tabla_mod.sv > "$d/tabla_mod.iverilog.log" 2>&1 \
    || { echo "FAIL tb_tabla_mod: no compila"; return 1; }
  vvp -n "$d/tabla_mod.vvp" ${CICLOS_TABLA:+"+ciclos=$CICLOS_TABLA"} ${SEMILLA_TABLA:+"+semilla=$SEMILLA_TABLA"} > "$d/tabla_mod.log" 2>&1
  grep -E "^(PASS|FAIL) tb_tabla_mod" "$d/tabla_mod.log" || echo "FAIL tb_tabla_mod: sin resultado"
  grep -q "^PASS tb_tabla_mod" "$d/tabla_mod.log"
}

# correr_vig DIR N [RTL]: sw/cuelgue_supervisor.s con el vigilante (N = 1 o 4)
correr_vig() {
  local d=$1 n=$2 r=${3:-$I/rtl}
  mkdir -p "$d"
  iverilog -g2012 -s tb_vig_barrel -DI_VIGILANTE -DVIG_N="$n" ${DEFS_PRUEBA:-} -o "$d/vig$n.vvp" "$CELLS_SIM" $(int_src "$r") $I/tb/tb_vig_barrel.sv > "$d/vig$n.iverilog.log" 2>&1 \
    || { echo "FAIL tb_vig_barrel N=$n: no compila"; return 1; }
  vvp -n "$d/vig$n.vvp" "+hex=$B/sw/cuelgue_supervisor.hex" +k=20 ${PERIODO_VIG:+"+periodo=$PERIODO_VIG"} > "$d/vig$n.log" 2>&1
  grep -E "^(PASS|FAIL) tb_vig_barrel" "$d/vig$n.log" || echo "FAIL tb_vig_barrel N=$n: sin resultado"
  grep -q "^PASS tb_vig_barrel" "$d/vig$n.log"
}

# correr_xd DIR "definiciones" NPROG [RTL]: NPROG programas de custom-0 con
# los cuatro hilos a la vez, contra el modelo de d_isa
correr_xd() {
  local d=$1 defs=$2 nprog=$3 r=${4:-$I/rtl} s n res arg t ok=0
  mkdir -p "$d"
  iverilog -g2012 -s tb_xd_barrel $defs -o "$d/xd.vvp" "$CELLS_SIM" $(int_src "$r") $I/tb/tb_xd_barrel.sv > "$d/xd.iverilog.log" 2>&1 \
    || { echo "FAIL tb_xd_barrel: no compila"; return 1; }
  for s in $(seq 1 "$nprog"); do
    n=$d/xd_s$s
    res=$($PYTHON $I/tools/gen_prog_hilos.py "--defs=$defs" --semilla "$s" --hex "$n.hex" --esperado "$n")
    arg=""
    for t in 0 1 2 3; do arg="$arg +n$t=$(echo "$res" | tr ' ' '\n' | sed -n "s/^h$t=\([0-9]*\):.*/\1/p")"; done
    vvp -n "$d/xd.vvp" "+hex=$n.hex" "+esp=$n" $arg > "$n.log" 2>&1
    grep -q "^PASS tb_xd_barrel" "$n.log" && ok=$((ok + 1))
  done
  if [ "$ok" = "$nprog" ]; then echo "PASS tb_xd_barrel: $ok de $nprog programas iguales al modelo"; return 0; fi
  echo "FAIL tb_xd_barrel: $ok de $nprog programas iguales al modelo ($(grep -h -m1 -E 'diferencia|escribe de mas|vale X' "$d"/xd_s*.log | head -1 | sed 's/^ *//'))"
  return 1
}
