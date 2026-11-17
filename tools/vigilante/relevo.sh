#!/usr/bin/env bash
# relevo.sh: relevo de punta a punta en RTL, del fondo con el supervisor
# colgado a la imagen de respaldo, comparado byte por byte con la referencia.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Usa tb/vigilante/tb_relevo.sv con Verilator. En el mismo testbench están la
# imagen 0 (R2: barrel, emad, devk, tabla y vigilante, con sw/fondo.s o una
# variante cuelgue_sup:N de tools/fondo/variante.py) y la imagen 1 (Espino
# base con sw/trade.hex). Los dos son el módulo pochoco_soc con definiciones
# distintas: para la imagen 0 se arma en build/ una copia llamada
# pochoco_soc_r2 con las definiciones de R2 puestas adentro.
#
# La reconfiguración se modela: desde que BOOT sube y durante T_RECONF el pin
# MISO vale 1 y ningún SoC tiene reloj; después la imagen 1 parte de cero.
# T_RECONF = 53 ms es el valor estimado con la hoja de datos en la
# factibilidad (factibilidad/e_warmboot/README.md), no una medición.
#
# El resultado esperado de cada corrida lo calcula tools/vigilante/relevo_ref.py
# a partir de los parámetros, sin mirar la simulación.
#
#   1. Corrida sana de 20 000 ticks: BOOT no sube nunca.
#   2. Relevos con T_RECONF = 53 ms: falla en el tick 100 a 0,1 ms, 1 ms y
#      10 ms, falla temprana (tick 3) y el caso de 0,1 ms repetido con la
#      maestra corrida 10 ns, para que ningún cambio suyo coincida con un
#      flanco del reloj.
#   3. Relevos con T_RECONF corto (2 ms): falla en el tick 100 y programa que
#      no escribe nunca (falla en el tick 1).
#   4. Barrido del fin de la reconfiguración a lo largo de una transacción,
#      cada 500 ns: la maestra lee unos y después ceros.
#   5. Barrido del fin del reset de la imagen 1 alrededor del primer flanco de
#      SCLK de una transacción, cada 20 ns: comprueba la regla que dice cuál es
#      el primer precio que recibe la imagen 1.
#   6. Controles negativos: la comparación tiene que rechazar una referencia
#      con otro VigN, con la falla en otro tick, y una simulación con un byte
#      cambiado.
#
# Uso, desde cualquier carpeta del repositorio:
#   tools/vigilante/relevo.sh      (make vig-relevo)
# Resultado en docs/mediciones/vigilante/relevo.txt. Termina con error si
# alguna línea da FAIL. JOBS fija cuántas simulaciones corren a la vez.
set -uo pipefail
export HW=r2
source "$(dirname "${BASH_SOURCE[0]}")/../fondo/comun.sh"

D=build/vigilante/relevo
MV=docs/mediciones/vigilante
INF=$MV/relevo.txt
TV=tools/vigilante
SERIE=tb/practica.csv
VIG_N=$(sed -n 's/.*parameter  *VigN  *= *\([0-9]*\).*/\1/p' rtl/pochoco_soc.v)
rm -rf "$D"
mkdir -p "$D" "$MV"
t_ini=$(date +%s)

# --- Copia del SoC para la imagen 0 ----------------------------------------------
# Solo difiere de rtl/pochoco_soc.v en el nombre del módulo y en que las
# definiciones de R2 quedan puestas dentro del archivo.
N_DEFS=$(echo $R2_DEFS | wc -w)
{ for d in $R2_DEFS; do echo "\`define ${d#-D}"; done
  sed -e 's/^module pochoco_soc #(/module pochoco_soc_r2 #(/' rtl/pochoco_soc.v
  echo; for d in $R2_DEFS; do echo "\`undef ${d#-D}"; done; } > "$D/pochoco_soc_r2.v"
COPIA_OK=0
if grep -q '^module pochoco_soc_r2 #(' "$D/pochoco_soc_r2.v" && \
   [ "$(sed -e '$a\\' rtl/pochoco_soc.v | diff - "$D/pochoco_soc_r2.v" | grep -c '^[<>]')" = $((2 * N_DEFS + 3)) ]; then COPIA_OK=1; fi

# --- Programas ---------------------------------------------------------------------
PROG_OK=1
ensamblar_fondo sw/fondo.s "$D/sano.hex" || PROG_OK=0
for n in 1 3 100; do
  $PYTHON tools/fondo/variante.py cuelgue_sup:$n -o "$D/cuelgue_$n.s" && \
    $PYTHON tools/pochoasm.py "$D/cuelgue_$n.s" -o "$D/cuelgue_$n.hex" > /dev/null || PROG_OK=0
done
$PYTHON tools/pochoasm.py sw/trade.s -o "$D/trade.hex" > /dev/null || PROG_OK=0
TRADE_OK=0; cmp -s "$D/trade.hex" sw/trade.hex && TRADE_OK=1

# --- Testbench -----------------------------------------------------------------------
SIM_OK=0
if [ $COPIA_OK = 1 ]; then
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_relevo -O3 \
    -DNO_ICE40_DEFAULT_ASSIGNMENTS --Mdir "$D/obj" -o sim \
    "$CELLS_SIM" "$D/pochoco_soc_r2.v" $BASE_SRC tb/vigilante/tb_relevo.sv > "$D/verilator.log" 2>&1 && SIM_OK=1
fi

# correr NOMBRE FALLA NTICKS PERIODO_NS INICIO_NS T_RECONF_NS [--breve]
# Simula y compara con la referencia. Deja el resultado en D/NOMBRE.txt.
correr() {
  local nom=$1 falla=$2 nt=$3 per=$4 ini=$5 trc=$6 prog=$D/sano.hex
  [ "$falla" != 0 ] && prog=$D/cuelgue_$falla.hex
  if ! "$D/obj/sim" +PROGRAMA="$prog" +TABLA="$TABLA_HEX" +RESPALDO=sw/trade.hex +SERIE="$SERIE" +NTICKS="$nt" \
       +PERIODO_NS="$per" +INICIO_NS="$ini" +T_RECONF_NS="$trc" +SALIDA="$D/$nom.csv" > "$D/$nom.log" 2>&1; then
    echo "FAIL $nom: la simulacion termino con error (ver $D/$nom.log)" > "$D/$nom.txt"; return 0
  fi
  $PYTHON $TV/relevo_ref.py --resumen "$D/$nom.log" --sim "$D/$nom.csv" --serie "$SERIE" --falla "$falla" \
    --vig-n "$VIG_N" --nombre "$nom" ${7:-} > "$D/$nom.txt" 2>&1
  [ -s "$D/$nom.txt" ] || echo "FAIL $nom: la referencia no entrego resultado" > "$D/$nom.txt"
  grep -q "^PASS\|^FAIL" "$D/$nom.txt" || sed -i "1s/^/FAIL $nom: /" "$D/$nom.txt"
}
export -f correr; export D TV SERIE VIG_N PYTHON TABLA_HEX

# Barridos, con la falla en el tick 3 a 0,1 ms. El precio colgado es el de la
# transacción 4 y BOOT sube 9580 ns después del comienzo de la transacción 8
# (la quinta sin respuesta).
#   corte: la fase 2 empieza entre 940 ns y 10 440 ns después del comienzo de
#          la transacción 28, que dura 9500 ns.
#   reset: el reset de la imagen 1 termina entre 460 ns antes y 340 ns después
#          del primer flanco de SCLK de la transacción 30 (163 800 ns desde
#          que empieza la fase 2, y ese flanco llega 1500 ns después del
#          comienzo de la transacción).
CORTE=$(seq 1991340 500 2000840)
# Tiempo de reconfiguración medido en la placa por el eco de la UART el 16/11
# (docs/mediciones/placa_16nov.md): 35,50 ms, una medición.
T_MEDIDO=${T_MEDIDO:-35500000}
RESET=$(seq 2027660 20 2028460)
if [ $SIM_OK = 1 ] && [ $PROG_OK = 1 ]; then
  {
    echo "sana        0   20000 100000   4000 53000000"
    echo "f100_r3     100 800   100000   4000 53000000"
    echo "f100_r2     100 250   1000000  4000 53000000"
    echo "f100_r1     100 160   10000000 4000 53000000"
    echo "f3_r3       3   700   100000   4000 53000000"
    echo "f100_r3_10  100 800   100000   4010 53000000"
    echo "med_r3      100 800   100000   4000 $T_MEDIDO"
    echo "med_r2      100 250   1000000  4000 $T_MEDIDO"
    echo "med_r1      100 160   10000000 4000 $T_MEDIDO"
    echo "f100_corto  100 300   100000   4000 2000000"
    echo "f1_corto    1   200   100000   4000 2000000"
    for t in $CORTE; do echo "corte_$t 3 60 100000 4000 $t --breve"; echo "corte10_$t 3 60 100000 4010 $t --breve"; done
    for t in $RESET; do echo "reset_$t 3 60 100000 4000 $t --breve"; echo "reset10_$t 3 60 100000 4010 $t --breve"; done
  } > "$D/lista.txt"
  xargs -P "${JOBS:-6}" -L1 bash -c 'correr "$@"' _ < "$D/lista.txt"
fi

# barrido PREFIJO TITULO: una línea PASS o FAIL con el resumen de un barrido
barrido() {
  local n pass bytes primeros
  n=$(ls "$D"/$1_*.txt 2>/dev/null | wc -l)
  pass=$(cat "$D"/$1_*.txt 2>/dev/null | grep -c '^PASS')
  bytes=$(cat "$D"/$1_*.txt | sed -n 's/.*cortados \([^,]*\),.*/\1/p' | tr ' ' '\n' | grep -v ninguno | sort -u | paste -sd' ')
  primeros=$(cat "$D"/$1_*.txt | sed -n 's/.*primer precio del respaldo en \([0-9]*\),.*/\1/p' | sort -n | uniq -c | awk '{printf "%s%s (%s corridas)", (NR > 1 ? ", " : ""), $2, $1}')
  if [ "$n" -gt 0 ] && [ "$pass" = "$n" ] && [ -n "$3" ]; then
    echo "PASS $2: $n corridas, todas iguales al esperado byte por byte"
  else
    echo "FAIL $2: $pass de $n corridas iguales al esperado${3:-, o el barrido no paso por la frontera que debia cruzar}"
    cat "$D"/$1_*.txt 2>/dev/null | grep -A3 '^FAIL' | head -12
  fi
  echo "  bytes leidos en la transaccion cortada: ${bytes:-ninguno}"
  echo "  primera transaccion que recibe la imagen 1: ${primeros:-ninguna}"
}

{
  cabecera "Relevo de punta a punta: del fondo colgado a la imagen de respaldo (tb/vigilante/tb_relevo.sv)" "tools/vigilante/relevo.sh" "make vig-relevo"
  echo "Imagen 0: copia de rtl/pochoco_soc.v llamada pochoco_soc_r2, con las definiciones de R2 y VigN = $VIG_N."
  echo "Imagen 1: pochoco_soc sin definiciones (Espino base) con sw/trade.hex (sha256 $(sha256sum sw/trade.hex | cut -c1-16)...)."
  echo "Serie: $SERIE. Referencia: tools/vigilante/relevo_ref.py, con ref/fondo.py y ref/trader.py."
  echo "Modelo de la reconfiguracion: desde BOOT y durante T_RECONF el pin MISO vale 1 (pull-up) y"
  echo "ningun SoC tiene reloj. T_RECONF = 53 ms es el valor tipico de la hoja de datos; $T_MEDIDO ns es el"
  echo "medido en la placa el 16/11 por el eco de la UART (docs/mediciones/placa_16nov.md, una medicion)."
  echo "Las transacciones se cuentan desde 0. La maestra usa los tiempos del testbench oficial."
  echo
  echo "=== 0. Preparacion ==="
  if [ $COPIA_OK = 1 ]; then echo "PASS copia: pochoco_soc_r2 difiere de rtl/pochoco_soc.v solo en el nombre del modulo y en las $N_DEFS definiciones"
  else echo "FAIL copia: la copia del SoC cambio mas de lo esperado"; fi
  if [ $PROG_OK = 1 ]; then echo "PASS programas: sw/fondo.s y las variantes cuelgue_sup:1, 3 y 100 ensamblan"
  else echo "FAIL programas: algun programa no ensambla"; fi
  if [ $TRADE_OK = 1 ]; then echo "PASS respaldo: sw/trade.hex es igual a sw/trade.s recien ensamblado"
  else echo "FAIL respaldo: sw/trade.hex no corresponde a sw/trade.s"; fi
  if [ $SIM_OK = 1 ]; then echo "PASS testbench: Verilator compila los dos SoC en el mismo testbench"
  else echo "FAIL testbench: Verilator no compila (ver $D/verilator.log)"; fi
  echo
  if [ $SIM_OK = 1 ] && [ $PROG_OK = 1 ]; then
    titulo() { echo "--- $1 ---"; cat "$D/$2.txt" 2>/dev/null || echo "FAIL $2: no hay resultado"; echo; }
    echo "=== 1. Corrida sana ==="
    titulo "fondo sin fallas, 20 000 ticks a 0,1 ms" sana
    echo "=== 2. Relevos con T_RECONF = 53 ms ==="
    titulo "falla en el tick 100, T = 0,1 ms (ronda 3), 800 ticks" f100_r3
    titulo "falla en el tick 100, T = 1 ms (ronda 2), 250 ticks" f100_r2
    titulo "falla en el tick 100, T = 10 ms (ronda 1), 160 ticks" f100_r1
    titulo "falla temprana, tick 3, T = 0,1 ms, 700 ticks" f3_r3
    titulo "falla en el tick 100, T = 0,1 ms, maestra corrida 10 ns (INICIO_NS = 4010)" f100_r3_10
    echo "=== 2b. Relevos con T_RECONF = $T_MEDIDO ns, medido en la placa el 16/11 ==="
    titulo "falla en el tick 100, T = 0,1 ms (ronda 3), 800 ticks" med_r3
    titulo "falla en el tick 100, T = 1 ms (ronda 2), 250 ticks" med_r2
    titulo "falla en el tick 100, T = 10 ms (ronda 1), 160 ticks" med_r1
    echo "=== 3. Relevos con T_RECONF = 2 ms ==="
    titulo "falla en el tick 100, T = 0,1 ms, 300 ticks" f100_corto
    titulo "el programa no escribe nunca (falla en el tick 1), T = 0,1 ms, 200 ticks" f1_corto
    echo "=== 4. Barrido del fin de la reconfiguracion dentro de una transaccion ==="
    echo "Falla en el tick 3 a 0,1 ms, T_RECONF de $(echo $CORTE | cut -d' ' -f1) a $(echo $CORTE | awk '{print $NF}') ns cada 500 ns."
    for p in corte corte10; do
      [ $p = corte ] && tit="corte, INICIO_NS = 4000" || tit="corte, INICIO_NS = 4010"
      # el barrido tiene que haber pasado por bytes cortados
      b=$(cat "$D"/${p}_*.txt 2>/dev/null | grep -c 'cortados [0-9a-f]')
      barrido $p "$tit" "$([ "$b" -ge 7 ] && echo si)"
    done
    echo
    echo "=== 5. Barrido del fin del reset de la imagen 1 ==="
    echo "Falla en el tick 3 a 0,1 ms, T_RECONF de $(echo $RESET | cut -d' ' -f1) a $(echo $RESET | awk '{print $NF}') ns cada 20 ns."
    for p in reset reset10; do
      [ $p = reset ] && tit="reset, INICIO_NS = 4000" || tit="reset, INICIO_NS = 4010"
      # el barrido tiene que haber cruzado la frontera: dos primeras transacciones distintas
      v=$(cat "$D"/${p}_*.txt 2>/dev/null | sed -n 's/.*primer precio del respaldo en \([0-9]*\),.*/\1/p' | sort -u | wc -l)
      barrido $p "$tit" "$([ "$v" = 2 ] && echo si)"
    done
    echo
  fi
  if [ -s "$D/f100_r3.csv" ]; then
    echo "=== 6. Controles negativos de la comparacion ==="
    echo "La corrida f100_r3 contra una referencia equivocada a proposito. PASS significa que la comparacion la rechazo."
    # negativo NOMBRE TEXTO CSV argumentos de relevo_ref.py
    negativo() {
      local nom=$1 txt=$2 sim=$3; shift 3
      if $PYTHON $TV/relevo_ref.py --resumen "$D/f100_r3.log" --sim "$sim" --serie "$SERIE" --nombre "$nom" --breve "$@" > "$D/$nom.txt" 2>&1; then
        echo "FAIL $nom ($txt): la comparacion no lo detecto"
      else
        echo "PASS $nom ($txt): $(grep -c '^  FAIL' "$D/$nom.txt") comprobaciones rechazadas"
      fi
    }
    negativo neg_vign "referencia con VigN = $((VIG_N + 1))" "$D/f100_r3.csv" --falla 100 --vig-n $((VIG_N + 1))
    negativo neg_falla "referencia con la falla en el tick 101" "$D/f100_r3.csv" --falla 101 --vig-n "$VIG_N"
    # un solo byte cambiado en la simulación: un 0xFF de la reconfiguración pasa a ser comprar 63
    awk -F, -v OFS=, 'NR > 1 && $3 == "ff" && !hecho { $3 = "7f"; hecho = 1 } { print }' "$D/f100_r3.csv" > "$D/neg_byte.csv"
    negativo neg_byte "un 0xFF de la simulacion cambiado por 0x7F" "$D/neg_byte.csv" --falla 100 --vig-n "$VIG_N"
    echo
  fi
  echo "Tiempo total: $(( $(date +%s) - t_ini )) s."
} > "$INF" 2>&1
echo "Total: $(grep -c '^PASS' "$INF") lineas con PASS y $(grep -c '^FAIL' "$INF") con FAIL." >> "$INF"
cat "$INF"
cierre "$INF"
