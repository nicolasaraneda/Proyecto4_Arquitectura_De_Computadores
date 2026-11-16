# comun.sh: rutas, listas de fuentes y configuraciones que comparten los
# scripts del diseño integrado.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Se incluye con "source". Deja el directorio de trabajo en la raíz del
# repositorio y define:
#   I            carpeta de este estudio, relativa a la raíz
#   B            productos intermedios (I/build, ignorada por git)
#   M            mediciones (I/mediciones, versionada)
#   A, D, E      carpetas de los estudios del barrel, de la extensión de la
#                ISA y del respaldo por reconfiguración. Solo se leen.
#   INT_SRC      fuentes del SoC integrado sobre el barrel
#   SEG_SRC      fuentes del SoC "conservador": segmentado con la extensión
#                (copia del core de d_isa) y el vigilante (copia del SoC y del
#                esclavo SPI de e_warmboot). Ningún archivo es de esta carpeta.
#   BASE_SRC     fuentes del SoC original (rtl/), sin modificar
#   CELLS_SIM    modelos de simulación de las primitivas del iCE40
# y las funciones int_src, ensamblar, con_tabla, programas, defs_de, armar_rtl
# y versiones.
#
# De los otros estudios se usan en su lugar, sin copiar ni modificar:
#   a_barrel     rtl/espino_barrel_regfile.v, tb/tb_verif.sv, tools/tabla.py,
#                tools/prog_hilos.py y tools/resumen_verif.py
#   d_isa        rtl/xd_*.v, core/espino_core/*.v, ref/xd.py, tools/gen_prog.py,
#                tools/xd_word.py y sw/trade_*.s
#   e_warmboot   rtl/vigilante.v, soc/pochoco_spi_slave.v, soc/pochoco_soc.v,
#                tb/mon_vigilante.sv y sw/cuelgue.s
# Las copias modificadas de esta carpeta son rtl/espino_barrel_core.v,
# rtl/pochoco_soc.v y rtl/espino_decoder_xd.v.

RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
cd "$RAIZ"
export PATH=${OSS_CAD_SUITE:+$OSS_CAD_SUITE/bin:}$PATH
export PYTHONDONTWRITEBYTECODE=1     # no dejar __pycache__ en las carpetas ajenas

I=factibilidad/i_integrado
A=factibilidad/a_barrel
D=factibilidad/d_isa
E=factibilidad/e_warmboot
B=$I/build
M=$I/mediciones
PYTHON=${PYTHON:-python3}
CELLS_SIM=$(yosys-config --datdir)/ice40/cells_sim.v

XD_SRC=$(echo $D/rtl/xd_*.v)
# int_src [CARPETA]: fuentes del SoC integrado. Los cuatro archivos propios
# (SoC, core y las dos memorias de la tabla) salen de CARPETA, que por defecto
# es rtl/ de este estudio. tools/mutaciones.sh la usa con copias mutadas.
int_src() {
  local r=${1:-$I/rtl}
  echo "rtl/pochoco_ram.v rtl/pochoco_periph.v $E/soc/pochoco_spi_slave.v \
rtl/espino_core/espino_alu.v rtl/espino_core/espino_load_store_unit.v \
$I/rtl/espino_decoder_xd.v $r/pochoco_soc.v $r/espino_barrel_core.v $A/rtl/espino_barrel_regfile.v \
$E/rtl/vigilante.v $r/tabla_mmio.v $r/tabla_ram.v $XD_SRC"
}
INT_SRC=$(int_src)
SEG_SRC="rtl/pochoco_ram.v rtl/pochoco_periph.v $E/soc/pochoco_spi_slave.v $E/soc/pochoco_soc.v \
$(echo $D/core/espino_core/*.v) $E/rtl/vigilante.v $XD_SRC"
BASE_SRC=$(echo rtl/*.v rtl/espino_core/*.v)

mkdir -p "$B/sw" "$M"

# La copia del decodificador debe ser la de d_isa salvo por el nombre del módulo
if ! diff -q <(sed -n '/^module espino_decoder #(/,$p' $D/core/espino_core/espino_decoder.v | sed '1s/espino_decoder/espino_decoder_xd/') \
             <(sed -n '/^module espino_decoder_xd #(/,$p' $I/rtl/espino_decoder_xd.v) > /dev/null; then
  echo "AVISO: $I/rtl/espino_decoder_xd.v ya no coincide con el decodificador de $D" >&2
fi
# Los archivos de rtl/ que d_isa y e_warmboot copiaron no deben haber cambiado
for f in pochoco_ram.v pochoco_periph.v espino_core/espino_alu.v espino_core/espino_load_store_unit.v \
         espino_core/espino_core.v espino_core/espino_if_stage.v espino_core/espino_register_file.v espino_core/espino_controller.v; do
  cmp -s "rtl/$f" "$D/core/$f" || echo "AVISO: rtl/$f cambió desde que $D hizo su copia" >&2
done

# ensamblar FUENTE.s SALIDA.hex [opciones]: ensambla con tools/pochoasm.py
ensamblar() {
  local s=$1 h=$2; shift 2
  $PYTHON tools/pochoasm.py "$@" "$s" -o "$h" > /dev/null
}

# con_tabla HILO PROGRAMA.s SALIDA.hex: antepone la tabla de arranque del barrel
con_tabla() {
  $PYTHON $A/tools/tabla.py "$1" "$2" > "${3%.hex}.s"
  ensamblar "${3%.hex}.s" "$3"
}

# programas: ensambla en B/sw los programas que usan las mediciones
#   trade_h0.hex        sw/trade.s sin modificar, con la tabla, en el hilo 0
#   trade_media_h0.hex  la regla base con devk y emad (d_isa/sw/trade_media.s)
#   trade_emad_h0.hex   la regla base con emad (d_isa/sw/trade_emad.s)
#   trade_media.hex, trade_emad.hex   las mismas sin tabla, para el segmentado
programas() {
  local p
  con_tabla 0 sw/trade.s "$B/sw/trade_h0.hex"
  for p in trade_media trade_emad; do
    $PYTHON $D/tools/xd_word.py --pre $D/sw/$p.s -o "$B/sw/$p.s"
    ensamblar "$B/sw/$p.s" "$B/sw/$p.hex"
    con_tabla 0 "$B/sw/$p.s" "$B/sw/${p}_h0.hex"
  done
}

# Subconjuntos de la extensión (definiciones XD_*), con los nombres de
# factibilidad/d_isa/tools/variantes.txt
defs_de() {
  case $1 in
    ref)           echo "" ;;
    emad_k5)       echo "-DXD_EMAD=0" ;;
    media_k5)      echo "-DXD_EMAD=0 -DXD_DEVK=0" ;;
    media_mul)     echo "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU" ;;
    alu_todo)      echo "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU -DXD_SIMDALU=12" ;;
    media_bandas)  echo "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU -DXD_SIMD=28" ;;
    media_muldiv)  echo "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU -DXD_DIVSTEP" ;;
    alu_todo_div)  echo "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU -DXD_SIMDALU=12 -DXD_DIVSTEP" ;;
    bandas_div)    echo "-DXD_EMAD=0 -DXD_DEVK=0 -DXD_MULSTEPALU -DXD_SIMD=28 -DXD_DIVSTEP" ;;
    *) echo "defs_de: subconjunto desconocido $1" >&2; return 1 ;;
  esac
}

# armar_rtl DESTINO barrel|segmentado [directa]: arma una carpeta con la forma
# que espera tools/medir_variante.sh (*.v y espino_core/*.v), con enlaces a los
# fuentes de INT_SRC o SEG_SRC. Con "directa", pochoco_ram.v es una copia con
# el atributo (* no_rw_check *) en sus arreglos (la memoria sin la emulación
# de lectura durante escritura, igual que en a_barrel/tools/medir_recursos.sh).
armar_rtl() {
  local d=$1 cual=$2 ram=${3:-original} f src
  rm -rf "${d:?}"; mkdir -p "$d/espino_core"
  if [ "$cual" = barrel ]; then src=$INT_SRC; else src=$SEG_SRC; fi
  for f in $src; do
    [ "$(basename "$f")" = pochoco_ram.v ] && [ "$ram" = directa ] && continue
    case "$(basename "$f")" in
      espino_*) ln -s "$RAIZ/$f" "$d/espino_core/" ;;
      *)        ln -s "$RAIZ/$f" "$d/" ;;
    esac
  done
  if [ "$ram" = directa ]; then
    sed -E 's|^( *)reg \[31:0\] (mem(_f)?) \[0:NumWords-1\];|\1(* no_rw_check *) reg [31:0] \2 [0:NumWords-1];|' \
      rtl/pochoco_ram.v > "$d/pochoco_ram.v"
    [ "$(diff rtl/pochoco_ram.v "$d/pochoco_ram.v" | grep -c '^>')" = 2 ] || { echo "FAIL: la copia de pochoco_ram.v no quedo como se esperaba" >&2; return 1; }
  fi
}

versiones() {
  echo "Herramientas:"
  echo "  $(yosys -V)"
  echo "  $(nextpnr-ice40 --version 2>&1 | head -1)"
  echo "  $(iverilog -V 2>/dev/null | head -1)"
  echo "Commit de partida: $(git rev-parse --short HEAD) (rama $(git rev-parse --abbrev-ref HEAD))"
}
