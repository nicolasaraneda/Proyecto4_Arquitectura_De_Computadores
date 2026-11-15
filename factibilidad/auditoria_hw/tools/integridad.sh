#!/usr/bin/env bash
# integridad.sh: nada versionado cambió fuera de factibilidad/ y el testbench oficial está intacto.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Solo lee: git status, git diff, git ls-files y git show. No cambia nada del
# repositorio (lo que compila queda en build/ de esta carpeta).
#   1. Ningún archivo versionado fuera de factibilidad/ tiene cambios locales
#      (git diff contra HEAD), ni tampoco los de las piezas de hardware de las
#      que dependen las dos auditadas.
#   2. Todo lo que aparece en git status queda dentro de factibilidad/.
#   3. tb/tb_proyecto_4.sv es byte a byte el del commit que lo entregó.
#   4. rtl/, tb/, ref/, tools/, sw/ y el Makefile de la raíz son los de main.
#   5. Las copias de fuentes que usan las piezas siguen iguales al original.
#   6. La referencia en C del fondo da lo mismo compilada con los fuentes de
#      HEAD y con los del disco (otro estudio está cambiando
#      factibilidad/retorno/nucleo mientras se corre esta auditoría).
#
# Uso: factibilidad/auditoria_hw/tools/integridad.sh   (o make integridad)
# Resultado en mediciones/integridad.txt.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

TB=tb/tb_proyecto_4.sv
{
echo "Auditoría: integridad del repositorio"
echo "Generado por factibilidad/auditoria_hw/tools/integridad.sh (make integridad). No editar a mano."
echo
echo "Rama $(git rev-parse --abbrev-ref HEAD), commit $(git rev-parse --short HEAD). Fecha: $(date '+%d/%m/%Y %H:%M')."
echo
echo "1. Archivos versionados con cambios locales (git diff --stat HEAD)"
d=$(git diff --stat HEAD)
echo "${d:-   ninguno}" | sed 's/^/   /'
fuera=$(git diff --name-only HEAD | grep -vc '^factibilidad/')
propias=$(git diff --name-only HEAD | grep -cE '^factibilidad/(i_integrado|b_fondo_hilos|auditoria_hw|a_barrel|d_isa|e_warmboot)/')
otras=$(git diff --name-only HEAD | grep -E '^factibilidad/' | grep -vE '^factibilidad/(i_integrado|b_fondo_hilos|auditoria_hw|a_barrel|d_isa|e_warmboot)/' | tr '\n' ' ')
if [ "$fuera" = 0 ]; then echo "PASS ningún archivo versionado fuera de factibilidad/ tiene cambios locales"
else echo "FAIL $fuera archivos versionados fuera de factibilidad/ tienen cambios locales"; fi
if [ "$propias" = 0 ]; then echo "PASS ningún archivo versionado de a_barrel, d_isa ni e_warmboot (de los que dependen las dos piezas) tiene cambios locales"
else echo "FAIL $propias archivos versionados de las piezas de hardware tienen cambios locales"; fi
if [ -n "$otras" ]; then
  echo "AVISO cambios locales dentro de factibilidad/ que no son de estas piezas (otro estudio en curso): $otras"
  echo "      La referencia del fondo se compila con factibilidad/retorno/nucleo/*.c. factibilidad/retorno/r4b_fondo/fondo.c: $(git diff --quiet HEAD -- factibilidad/retorno/r4b_fondo/fondo.c && echo 'sin cambios' || echo 'CON CAMBIOS')."
  echo "      factibilidad/retorno/nucleo/nucleo.c: $(git diff --quiet HEAD -- factibilidad/retorno/nucleo/nucleo.c && echo 'sin cambios' || echo 'CON CAMBIOS')."
fi
echo
echo "2. Archivos sin versionar (git status --porcelain)"
s=$(git status --porcelain)
echo "${s:-   (nada)}" | sed 's/^/   /'
nfuera=$(echo "$s" | grep -v '^$' | awk '{print $2}' | grep -vc '^factibilidad/')
if [ "$nfuera" = 0 ]; then echo "PASS todo lo que aparece en git status está dentro de factibilidad/"
else echo "FAIL $nfuera entradas de git status fuera de factibilidad/"; fi
echo "   Carpetas de este tramo que todavía no están en un commit:"
for c in factibilidad/i_integrado factibilidad/b_fondo_hilos factibilidad/auditoria_hw; do
  echo "     $c: $(git ls-files "$c" | wc -l) archivos versionados, $(git status --porcelain --untracked-files=all "$c" | grep -c '^??') sin versionar"
done
echo
echo "3. Testbench oficial"
alta=$(git log --diff-filter=A --format=%h -- $TB | tail -1)
h_ahora=$(sha256sum $TB | cut -d' ' -f1)
h_head=$(git show HEAD:$TB | sha256sum | cut -d' ' -f1)
h_alta=$(git show "$alta:$TB" | sha256sum | cut -d' ' -f1)
echo "   sha256 en el disco:                 $h_ahora"
echo "   sha256 en HEAD:                     $h_head"
echo "   sha256 en el commit que lo entregó: $h_alta ($alta, $(git log -1 --format=%s "$alta"))"
echo "   commits que lo tocaron: $(git log --format=%h -- $TB | wc -l)"
if [ "$h_ahora" = "$h_head" ] && [ "$h_ahora" = "$h_alta" ]; then echo "PASS tb/tb_proyecto_4.sv es el archivo entregado, sin ningún cambio"
else echo "FAIL tb/tb_proyecto_4.sv cambió"; fi
echo
echo "4. Commits de la rama que tocan algo fuera de factibilidad/ (git log main..HEAD)"
r=$(git diff --stat main...HEAD -- . ':(exclude)factibilidad' 2>/dev/null)
if [ -z "$r" ]; then echo "   ninguno"
else
  echo "$r" | sed 's/^/   /'
  git log --format='   %h %ad %s' --date=format:%d/%m main..HEAD -- . ':(exclude)factibilidad'
  echo "   AVISO son commits anteriores a estas dos piezas, que todavía no están en ningún commit."
fi
echo "   Dentro de factibilidad/: $(git diff --stat main...HEAD -- factibilidad | tail -1 | sed 's/^ *//')"
echo "   rtl/, tb/, ref/, tools/, sw/ y Makefile respecto de main: $(git diff --stat main...HEAD -- rtl tb ref tools sw Makefile | tail -1 | sed 's/^ *//; s/^$/sin cambios/')$(git diff --quiet main...HEAD -- rtl tb ref tools sw Makefile && echo 'sin cambios')"
if git diff --quiet main...HEAD -- rtl tb ref tools sw Makefile && git diff --quiet HEAD -- rtl tb ref tools sw Makefile; then
  echo "PASS rtl/, tb/, ref/, tools/, sw/ y el Makefile de la raíz son los de main"
else echo "FAIL hay cambios en rtl/, tb/, ref/, tools/, sw/ o el Makefile de la raíz"; fi
echo
echo "5. Copias de fuentes del repositorio que usan las piezas: siguen iguales al original"
for par in "rtl/pochoco_ram.v $D/core/pochoco_ram.v" "rtl/pochoco_periph.v $D/core/pochoco_periph.v" \
           "rtl/espino_core/espino_alu.v $D/core/espino_core/espino_alu.v" \
           "rtl/espino_core/espino_load_store_unit.v $D/core/espino_core/espino_load_store_unit.v"; do
  set -- $par
  if cmp -s "$1" "$2"; then echo "   igual     $2"; else echo "   DISTINTO  $2 (respecto de $1)"; fi
done
echo "   $I/rtl/espino_decoder_xd.v contra $D/core/espino_core/espino_decoder.v: $(diff <(sed -n '/^module espino_decoder_xd #(/,$p' $I/rtl/espino_decoder_xd.v | sed '1s/espino_decoder_xd/espino_decoder/') <(sed -n '/^module espino_decoder #(/,$p' $D/core/espino_core/espino_decoder.v) | grep -c '^[<>]') líneas de código distintas además del nombre del módulo ($(diff <(sed 's/espino_decoder_xd/espino_decoder/' $I/rtl/espino_decoder_xd.v) $D/core/espino_core/espino_decoder.v | grep -c '^[<>]') líneas de comentario agregadas en el encabezado)"
echo "   $E/soc/pochoco_spi_slave.v contra rtl/pochoco_spi_slave.v: $(diff rtl/pochoco_spi_slave.v $E/soc/pochoco_spi_slave.v | grep -c '^>') líneas agregadas y $(diff rtl/pochoco_spi_slave.v $E/soc/pochoco_spi_slave.v | grep -c '^<') cambiada (el encabezado de la copia, las tres salidas para el vigilante y la coma del último puerto)"
echo
echo "6. La referencia en C del fondo no depende de los cambios locales de factibilidad/retorno/nucleo"
# Se compila dos veces: con los fuentes del disco y con los de HEAD (git show, sin tocar el árbol de trabajo)
R=factibilidad/retorno
N=$B/nucleo_head
rm -rf "$N"; mkdir -p "$N"
for f in nucleo.c torneo.c e_param.c e_rivales.c main.c nucleo.h torneo.h; do git show "HEAD:$R/nucleo/$f" > "$N/$f"; done
git show "HEAD:$R/r4b_fondo/fondo.c" > "$N/fondo.c"
ver=$(cat "$N/nucleo.h" "$N/nucleo.c" "$N/e_param.c" "$N/e_rivales.c" | md5sum | cut -c1-15)
if gcc -O2 -fopenmp -I"$N" -DRETORNO_DIR="\"$RAIZ/$R\"" -DNUCLEO_VERSION=0x${ver}ULL -o "$B/arnes_head" "$N/nucleo.c" "$N/torneo.c" "$N/e_param.c" "$N/e_rivales.c" "$N/main.c" "$N/fondo.c" -lm 2> "$B/arnes_head.log" \
   && make -s -C "$U" build/arnes > /dev/null 2>&1; then
  iguales=1
  for est in fondo_min fondo_min_ant; do
    for k in 0 2; do
      HILOS=1 "$B/arnes_head" correr --estrategia $est --serie tb/practica.csv --nticks 20000 --perdidos $k -o "$B/ref_head.csv" > /dev/null 2>&1
      HILOS=1 "$B/arnes"      correr --estrategia $est --serie tb/practica.csv --nticks 20000 --perdidos $k -o "$B/ref_disco.csv" > /dev/null 2>&1
      cmp -s "$B/ref_head.csv" "$B/ref_disco.csv" || iguales=0
    done
  done
  echo "   Fuentes de HEAD contra fuentes del disco, fondo_min y fondo_min_ant, 20 000 ticks de la práctica, con 0 y con 2 precios sin ver:"
  if [ $iguales = 1 ]; then echo "PASS las dos compilaciones entregan el mismo decisiones.csv (sha256 del último: $(sha256sum "$B/ref_disco.csv" | cut -c1-16)...)"
  else echo "FAIL la referencia cambia con los cambios locales de factibilidad/retorno/nucleo"; fi
else
  echo "AVISO no se pudo compilar la referencia con los fuentes de HEAD o con los del disco (ver $B/arnes_head.log)"
fi
} | tee "$M/integridad.txt"

! grep -q "^FAIL" "$M/integridad.txt"
