#!/usr/bin/env bash
# mutaciones.sh: errores nuevos puestos a propósito, contra las pruebas de las piezas.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Las dos piezas traen sus propios controles negativos. Aquí se ponen errores
# que sus autores no eligieron, para ver si sus testbenches prueban lo que
# dicen. Todo se hace sobre copias: ningún fuente se modifica.
#
#   A. Integración de la extensión de la ISA en el barrel (6 mutaciones en
#      copias de i_integrado/rtl/espino_barrel_core.v y de d_isa/rtl/xd_opa.v).
#      Prueba de la pieza: tb/tb_xd_barrel.sv con programas de
#      tools/gen_prog_hilos.py contra el modelo, en tres configuraciones:
#        XD-I1     emad, devk y mulstep con vigilante y tabla (I1)
#        XD-ancha  lo anterior más carriles en la ALU y divstep (la que usa
#                  tools/mutaciones.sh de la pieza)
#        XD-k      todas las instrucciones con todos los k
#   B. Vigilante (6 mutaciones en copias de i_integrado/rtl/pochoco_soc.v y de
#      e_warmboot/rtl/vigilante.v). Pruebas: tb/tb_vig_barrel.sv de la pieza
#      con N = 4 y N = 1 (VIG4 y VIG1), y la prueba formal del módulo de
#      e_warmboot (FORMAL, prove con N = 4). VIG4-antes es el mismo testbench
#      como estaba antes de que la auditoría lo corrigiera: sirve para dejar
#      medido qué dejaba pasar. No cuenta como detección.
#   C. Protocolo entre hilos del fondo (6 mutaciones de sw/fondo.s, de
#      tools/prog_carreras.py). Pruebas:
#        EQUIV     la de la pieza: tb/tb_fondo.sv, 20 000 ticks de la práctica
#                  a 0,1 ms, decisiones byte a byte y estado interno contra la
#                  referencia en C (lo que hacen make equiv y make estado)
#        ATRASO    la variante atraso_800 de la pieza sobre el programa mutado
#                  (el gestor 3 publica 800 ciclos más tarde)
#        ATRASO2   la variante atraso_800_g2, que la auditoría agregó a
#                  make variantes de la pieza: lo mismo con el gestor 2. Antes
#                  la pieza solo atrasaba al gestor 3
#        MON       los monitores de tb/tb_carreras.sv con el programa mutado y
#                  el timing nominal, sin retardos
#        CARRERAS  la prueba de la auditoría: retardos y fase al azar,
#                  monitores y modelo sobre los precios vistos
#
# Una mutación está detectada si alguna prueba falla. El RTL y el programa sin
# mutar tienen que pasar todas.
#
# Uso: factibilidad/auditoria_hw/tools/mutaciones.sh   (o make mutaciones)
# Resultado en mediciones/mutaciones.txt. Unos 5 minutos con 5 procesos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"
arnes || exit 1

O=$B/mutaciones
mkdir -p "$O/sw" "$O/series"
NPROG=${NPROG:-12}
DEFS_ANCHA="-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU -DXD_SIMDALU=12 -DXD_DIVSTEP -DI_VIGILANTE -DI_TABLA=1"
DEFS_K="-DXD_EMA=5 -DXD_EMAALU -DXD_EMAD=5 -DXD_DEVK=5 -DXD_SRAK=5 -DXD_SIMD=31 -DXD_MULSTEPALU -DXD_DIVSTEP -DXD_MULC=16"

$PYTHON tools/pochoasm.py $I/sw/cuelgue_supervisor.s -o "$O/sw/cuelgue_supervisor.hex" -D K=20 > /dev/null || exit 1
[ -s "$O/series/volatil.csv" ] || $PYTHON ref/series.py volatil --n 20000 --semilla 1 -o "$O/series/volatil.csv" > /dev/null

# fuentes_mut CARPETA: lista de fuentes del SoC integrado con las copias de CARPETA
fuentes_mut() {
  src_i "$1" "$1/vigilante.v" "$(echo $XD | sed "s|$D/rtl/xd_opa.v|$1/xd_opa.v|")"
}

# xd CARPETA_RTL DIR ETIQUETA "definiciones": programas de custom-0 en los cuatro hilos contra el modelo
xd() {
  local r=$1 d=$2/$3 defs=$4 s n res arg t ok=0
  mkdir -p "$d"
  iverilog -g2012 -s tb_xd_barrel $defs -o "$d/xd.vvp" "$CELLS_SIM" $(fuentes_mut "$r") $I/tb/tb_xd_barrel.sv > "$d/iverilog.log" 2>&1 \
    || { echo "$3 FAIL no compila"; return; }
  for s in $(seq 1 "$NPROG"); do
    n=$d/p$s
    res=$($PYTHON $I/tools/gen_prog_hilos.py "--defs=$defs" --semilla $((500 + s)) --hex "$n.hex" --esperado "$n")
    arg=""
    for t in 0 1 2 3; do arg="$arg +n$t=$(echo "$res" | tr ' ' '\n' | sed -n "s/^h$t=\([0-9]*\):.*/\1/p")"; done
    vvp -n "$d/xd.vvp" "+hex=$n.hex" "+esp=$n" $arg > "$n.log" 2>&1
    grep -q "^PASS tb_xd_barrel" "$n.log" && ok=$((ok + 1))
  done
  if [ "$ok" = "$NPROG" ]; then echo "$3 PASS $ok de $NPROG programas iguales al modelo"
  else echo "$3 FAIL $ok de $NPROG programas iguales al modelo ($(grep -h -m1 -E 'diferencia|escribe de mas|vale X' "$d"/p*.log | head -1 | sed 's/^ *//' | cut -c1-90))"; fi
}

# vig CARPETA_RTL DIR N: tb_vig_barrel de la pieza
vig() {
  local r=$1 d=$2/vig$3
  mkdir -p "$d"
  iverilog -g2012 -s tb_vig_barrel -DVIG_N="$3" $DEFS_I1A -o "$d/vig.vvp" "$CELLS_SIM" $(fuentes_mut "$r") $I/tb/tb_vig_barrel.sv > "$d/iverilog.log" 2>&1 \
    || { echo "VIG$3 FAIL no compila"; return; }
  vvp -n "$d/vig.vvp" "+hex=$O/sw/cuelgue_supervisor.hex" +k=20 > "$d/vig.log" 2>&1
  if grep -q "^PASS tb_vig_barrel" "$d/vig.log"; then echo "VIG$3 PASS $(grep '^PASS' "$d/vig.log" | cut -c1-110)"
  else echo "VIG$3 FAIL $(grep -m1 'FALLA' "$d/vig.log" | sed 's/^ *FALLA: //' | cut -c1-110)"; fi
}

# vig_antes CARPETA_RTL DIR: lo mismo con el testbench como estaba antes de la
# auditoría, que miraba BOOT y el destino en los cables que salen del
# vigilante (dut.g_vig.boot y dut.g_vig.sel) y no en las entradas de la
# primitiva. Se reconstruye deshaciendo esas dos líneas en una copia.
vig_antes() {
  local r=$1 d=$2/vig_antes
  mkdir -p "$d"
  sed -e 's|dut\.g_vig\.u_warmboot\.BOOT|dut.g_vig.boot|' \
      -e 's|{dut\.g_vig\.u_warmboot\.S1, dut\.g_vig\.u_warmboot\.S0}|dut.g_vig.sel|' $I/tb/tb_vig_barrel.sv > "$d/tb_vig_barrel.sv"
  [ "$(diff $I/tb/tb_vig_barrel.sv "$d/tb_vig_barrel.sv" | grep -c '^>')" = 2 ] || { echo "VIG4-antes FAIL no se pudo reconstruir el testbench anterior"; return; }
  iverilog -g2012 -s tb_vig_barrel -DVIG_N=4 $DEFS_I1A -o "$d/vig.vvp" "$CELLS_SIM" $(fuentes_mut "$r") "$d/tb_vig_barrel.sv" > "$d/iverilog.log" 2>&1 \
    || { echo "VIG4-antes FAIL no compila"; return; }
  vvp -n "$d/vig.vvp" "+hex=$O/sw/cuelgue_supervisor.hex" +k=20 > "$d/vig.log" 2>&1
  if grep -q "^PASS tb_vig_barrel" "$d/vig.log"; then echo "VIG4-antes PASS el testbench de antes de la auditoría pasa"
  else echo "VIG4-antes FAIL $(grep -m1 'FALLA' "$d/vig.log" | sed 's/^ *FALLA: //' | cut -c1-110)"; fi
}

# formal_vig CARPETA_RTL DIR: la prueba por inducción de e_warmboot sobre la copia del módulo (N = 4)
formal_vig() {
  local d=$2/formal
  rm -rf "$d"; mkdir -p "$d"
  cp "$1/vigilante.v" "$d/vigilante.v"
  printf '[options]\nmode prove\ndepth 24\n[engines]\nsmtbmc yices\n[script]\nread_verilog -formal vigilante.v\nchparam -set N 4 vigilante\nprep -top vigilante\n[files]\nvigilante.v\n' > "$d/v.sby"
  ( cd "$d" && sby -f v.sby > sby.log 2>&1 )
  if grep -q "DONE (PASS" "$d/sby.log"; then echo "FORMAL PASS prueba por inducción del módulo, N = 4"
  else echo "FORMAL FAIL $(grep -m1 -E 'Assert failed|BMC failed|DONE \(' "$d/sby.log" | sed 's/^.*engine_0: *//; s/^SBY[^]]*] *//' | cut -c1-110)"; fi
}

# rtl NOMBRE: una mutación de RTL (o "referencia") con las pruebas de su área
rtl() {
  local m=$1 d=$O/$1 area
  rm -rf "$d"; mkdir -p "$d"
  $PYTHON $U/tools/mutar_aud.py "$m" "$d/rtl" > "$d/mutar.log" 2>&1 || { echo "NO_APLICA $(cat "$d/mutar.log")" > "$d/resultado.txt"; return 0; }
  area=$($PYTHON $U/tools/mutar_aud.py --tabla | grep "^$m|" | cut -d'|' -f2)
  {
    if [ "$area" != vigilante ]; then
      xd "$d/rtl" "$d" XD-I1 "$DEFS_I1A"
      xd "$d/rtl" "$d" XD-ancha "$DEFS_ANCHA"
      xd "$d/rtl" "$d" XD-k "$DEFS_K"
    fi
    if [ "$area" != isa ]; then
      vig "$d/rtl" "$d" 4
      vig "$d/rtl" "$d" 1
      formal_vig "$d/rtl" "$d"
      vig_antes "$d/rtl" "$d"
    fi
  } > "$d/resultado.txt"
}

# --- Protocolo del fondo -------------------------------------------------------
# prog DIR FUENTE.s: ensambla y deja los símbolos
prog() {
  $PYTHON tools/pochoasm.py "$2" -o "$1/fondo.hex" > /dev/null && $PYTHON $F/tools/simbolos.py "$2" --vh "$1/simbolos.vh"
}
# sim_pieza DIR: compila tb/tb_fondo.sv de la pieza con el programa de DIR
sim_pieza() {
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_fondo -O3 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS "-DPROGRAMA=\"$1/fondo.hex\"" "-I$1" --Mdir "$1/obj" -o sim \
    "$CELLS_SIM" $SRC_BARREL_PROTO $F/tb/tb_fondo.sv > "$1/verilator.log" 2>&1
}
sim_aud() {
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_carreras -O3 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS "-DPROGRAMA=\"$1/fondo.hex\"" "-I$1" --Mdir "$1/obj" -o sim \
    "$CELLS_SIM" $SRC_BARREL_PROTO $U/tb/tb_carreras.sv > "$1/verilator.log" 2>&1
}
# prueba_pieza DIR ETIQUETA: 20 000 ticks de la práctica a 0,1 ms con tb_fondo, contra la referencia
prueba_pieza() {
  local d=$1 k
  k=$(perdidos 100000)
  "$d/obj/sim" +serie=tb/practica.csv +nticks=20000 +periodo=100000 +inicio=4000 "+ticks_csv=$d/t.csv" "+dec_csv=$d/dec.csv" > "$d/run.log" 2>&1
  FONDO_TRAZA=$d/traza.csv HILOS=1 "$ARNES" correr --estrategia fondo_min --serie tb/practica.csv --nticks 20000 --perdidos "$k" -o "$d/ref.csv" > "$d/ref.log" 2>&1
  local c44 dec est
  c44=$(grep -o "Chequeos aprobados: [0-9]/4" "$d/run.log" | grep -o "[0-9]/4")
  if cmp -s "$d/dec.csv" "$d/ref.csv"; then dec="decisiones idénticas"; else dec="decisiones distintas desde la fila $(cmp "$d/dec.csv" "$d/ref.csv" | grep -o 'line [0-9]*' | grep -o '[0-9]*')"; fi
  if $PYTHON $F/tools/comparar_estado.py "$d/t.csv" "$d/traza.csv" > "$d/estado.log" 2>&1; then est="estado idéntico"; else est="estado distinto"; fi
  if [ "$c44" = 4/4 ] && [ "$dec" = "decisiones idénticas" ] && [ "$est" = "estado idéntico" ]; then echo "$2 PASS $c44, $dec, $est"
  else echo "$2 FAIL ${c44:-sin resultado}, $dec, $est"; fi
}
# prueba_aud DIR ETIQUETA SERIE JITTER SW_CADA: tb_carreras, monitores y modelo sobre los precios vistos
prueba_aud() {
  local d=$1 n mon mod
  "$d/obj/sim" "+serie=$3" +nticks=20000 +periodo=100000 "+jitter=$4" "+sw_cada=$5" +semilla=21 \
    "+vistos_csv=$d/v.csv" "+estado_csv=$d/e.csv" > "$d/run.log" 2>&1
  n=$(($(wc -l < "$d/e.csv") - 1))
  if [ "$n" -gt 0 ]; then
    FONDO_TRAZA=$d/traza.csv HILOS=1 "$ARNES" correr --estrategia fondo_min --serie "$d/v.csv" --nticks "$n" --perdidos 0 -o "$d/ref.csv" > "$d/ref.log" 2>&1
    mod=$($PYTHON $U/tools/comparar_vistos.py "$d/e.csv" "$d/traza.csv" | cut -c1-70)
  else mod="FAIL modelo: el supervisor no completa ningún tick"; fi
  mon=$(grep -E "^(PASS|FAIL) monitores" "$d/run.log")
  if [[ "$mon" == PASS* ]] && [[ "$mod" == PASS* ]]; then echo "$2 PASS monitores sin violaciones y estado igual al modelo (esperas del supervisor a EST_1, EST_2 y EST_3: $(grep '^Cargas de EST_k' "$d/run.log" | sed 's/.*: *//'))"
  else echo "$2 FAIL violaciones M1..M7: $(grep '^Violaciones M1' "$d/run.log" | sed 's/.*: *//'), M9: $(grep '^Violaciones M9' "$d/run.log" | sed 's/.*: *//'); modelo: ${mod#* modelo: }"; fi
}

# protocolo NOMBRE: una mutación de sw/fondo.s (o "referencia")
protocolo() {
  local m=$1 d=$O/p_$1 opt=""
  rm -rf "$d"; mkdir -p "$d/equiv" "$d/atraso" "$d/atraso2" "$d/mon" "$d/carreras"
  [ "$m" != referencia ] && opt="--mutacion $m"
  {
    $PYTHON $U/tools/prog_carreras.py $F/sw/fondo.s -o "$d/equiv/fondo.s" $opt || { echo "EQUIV NO_APLICA"; return 0; }
    cp "$d/equiv/fondo.s" "$d/mon/fondo.s"
    $PYTHON $F/tools/variante.py "$d/equiv/fondo.s" retardo_antes:100:3 -o "$d/atraso/fondo.s"
    $PYTHON $F/tools/variante.py "$d/equiv/fondo.s" retardo_antes:100:2 -o "$d/atraso2/fondo.s"
    $PYTHON $U/tools/prog_carreras.py $F/sw/fondo.s -o "$d/carreras/fondo.s" $opt --retardos 4
    for v in equiv atraso atraso2 mon carreras; do prog "$d/$v" "$d/$v/fondo.s" || echo "$v FAIL no ensambla"; done
    sim_pieza "$d/equiv"; sim_pieza "$d/atraso"; sim_pieza "$d/atraso2"; sim_aud "$d/mon"; sim_aud "$d/carreras"
    prueba_pieza "$d/equiv" EQUIV
    prueba_pieza "$d/atraso" ATRASO
    prueba_pieza "$d/atraso2" ATRASO2
    prueba_aud "$d/mon" MON tb/practica.csv 0 0
    prueba_aud "$d/carreras" CARRERAS "$O/series/volatil.csv" 4000 37
  } > "$d/resultado.txt" 2> "$d/errores.txt"
}

if [ "${1:-}" = --rtl ]; then rtl "$2"; exit 0; fi
if [ "${1:-}" = --protocolo ]; then protocolo "$2"; exit 0; fi

M_RTL=$($PYTHON $U/tools/mutar_aud.py --tabla | cut -d'|' -f1)
M_PROT=$($PYTHON $U/tools/prog_carreras.py --lista | cut -d'|' -f1)
T0=$(date +%s)
if [ "${SOLO_INFORME:-0}" != 1 ]; then
  {
    for m in referencia $M_RTL; do echo "--rtl $m"; done
    for m in referencia $M_PROT; do echo "--protocolo $m"; done
  } | xargs -P "$JOBS" -L 1 "$RAIZ/$U/tools/mutaciones.sh"
fi
T1=$(date +%s)

{
echo "Auditoría: errores nuevos puestos a propósito, contra las pruebas de las piezas"
echo "Generado por factibilidad/auditoria_hw/tools/mutaciones.sh (make mutaciones). No editar a mano."
echo
versiones
echo "  $(sby --version 2>&1 | head -1)"
echo "Pruebas: XD-I1, XD-ancha y XD-k = tb_xd_barrel de i_integrado, $NPROG programas por configuración; VIG4 y VIG1 = tb_vig_barrel de"
echo "  i_integrado; FORMAL = prueba por inducción del vigilante de e_warmboot; EQUIV, ATRASO y ATRASO2 = tb_fondo de b_fondo_hilos"
echo "  contra la referencia en C (20 000 ticks, decisiones y estado), sin retardo, con el gestor 3 atrasado 800 ciclos y con el"
echo "  gestor 2 atrasado 800 ciclos; MON y CARRERAS = tb_carreras de esta carpeta."
echo "Demora: $((T1 - T0)) s con $JOBS procesos."
echo
fallas=0
echo "Sin mutación: todas las pruebas deben pasar"
for r in "$O/referencia/resultado.txt" "$O/p_referencia/resultado.txt"; do
  while read -r p estado resto; do
    echo "   $estado $p: $resto"
    [ "$estado" = PASS ] || fallas=$((fallas + 1))
  done < "$r"
done
echo
total=0; detectadas=0; por_pieza=0; resumen=""; solo_aud=""; ninguna=""; antes_no=""; solo_atraso2=""
tabla=$($PYTHON $U/tools/mutar_aud.py --tabla; $PYTHON $U/tools/prog_carreras.py --lista | sed 's/|/|protocolo|fondo.s|/')
for m in $M_RTL $M_PROT; do
  total=$((total + 1))
  area=$(echo "$tabla" | grep "^$m|" | cut -d'|' -f2)
  r=$O/$m/resultado.txt; [ "$area" = protocolo ] && r=$O/p_$m/resultado.txt
  quien=$(grep " FAIL " "$r" | grep -v '^VIG4-antes' | cut -d' ' -f1 | tr '\n' ' ' | sed 's/ $//')
  pasan=$(grep " PASS " "$r" | grep -v '^VIG4-antes' | cut -d' ' -f1 | tr '\n' ' ' | sed 's/ $//')
  grep -q "^VIG4-antes PASS" "$r" && [ -z "$(grep -E '^VIG[41] PASS' "$r")" ] && antes_no="$antes_no$m "
  # Pruebas de las piezas: todas menos MON y CARRERAS, que son de esta carpeta
  pieza=$(grep " FAIL " "$r" | cut -d' ' -f1 | grep -vE '^(MON|CARRERAS|VIG4-antes)$' | tr '\n' ' ' | sed 's/ $//')
  if [ -n "$pieza" ]; then por_pieza=$((por_pieza + 1)); fi
  [ "$pieza" = ATRASO2 ] && solo_atraso2="$solo_atraso2$m "
  if [ -n "$quien" ]; then
    detectadas=$((detectadas + 1))
    [ -z "$pieza" ] && solo_aud="$solo_aud$m "
    echo "DETECTADA $m [$area]: la detectan $quien${pasan:+; no la detectan $pasan}"
  else ninguna="$ninguna$m "; echo "NO DETECTADA $m [$area]: pasan $pasan"; fi
  echo "      $(echo "$tabla" | grep "^$m|" | cut -d'|' -f4) ($(echo "$tabla" | grep "^$m|" | cut -d'|' -f3))"
  sed -E 's/^([A-Za-z0-9-]+) (PASS|FAIL) /      \1 \2: /' "$r" | cut -c1-220
  resumen="$resumen$(printf '   %-22s %-10s %-26s %-18s %s' "$m" "$area" "${pieza:--}" "$(grep " FAIL " "$r" | cut -d' ' -f1 | grep -E '^(MON|CARRERAS)$' | tr '\n' ' ' | sed 's/ $//; s/^$/-/')" "${pasan:--}")"$'\n'
done
echo
echo "Resumen: mutación, área, pruebas de las piezas que la detectan, pruebas de la auditoría que la detectan y pruebas que pasan igual"
printf '%s' "$resumen"
echo
echo "Mutaciones: $total. Detectadas por alguna prueba de las piezas: $por_pieza. Detectadas solo por las pruebas de esta carpeta: ${solo_aud:-ninguna}."
echo "No detectadas por ninguna prueba: ${ninguna:-ninguna}. Problemas con el RTL o el programa sin mutar: $fallas."
echo "VIG4-antes es tb/tb_vig_barrel.sv de i_integrado como estaba antes de la auditoría (miraba los cables del vigilante y no las"
echo "entradas de la primitiva). No entra en las cuentas. Mutaciones que VIG4 y VIG1 detectan ahora y ese testbench dejaba pasar: ${antes_no:-ninguna}."
echo "ATRASO2 es la variante atraso_800_g2, que la auditoría agregó a make variantes de b_fondo_hilos (antes solo se atrasaba al"
echo "gestor 3). Mutaciones que, de las pruebas de las piezas, solo detecta ATRASO2: ${solo_atraso2:-ninguna}."
if [ $fallas = 0 ]; then echo "RESULTADO: referencia PASS, $por_pieza de $total mutaciones detectadas por las pruebas de las piezas y $detectadas de $total contando las de la auditoría"
else echo "RESULTADO: FAIL, el RTL o el programa sin mutar no pasa alguna prueba"; fi
} | tee "$M/mutaciones.txt"

grep -q "^RESULTADO: referencia PASS" "$M/mutaciones.txt"
