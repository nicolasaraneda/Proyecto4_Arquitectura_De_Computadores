#!/usr/bin/env bash
# recursos.sh: celdas, BRAM y frecuencia máxima de I1, I2 e I3, medidos de nuevo.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Repite las cifras de la tabla principal de factibilidad/i_integrado sin usar
# sus scripts: las listas de fuentes y las definiciones están escritas en
# tools/comun.sh de esta carpeta. El flujo es el del repositorio
# (tools/medir_variante.sh: yosys synth_ice40 y nextpnr-ice40 --hx1k
# --package vq100 --freq 25 con goboard.pcf), con etiquetas
# fact2_auditoria_hw_*. Cuatro cosas que el estudio no hizo:
#   - 20 semillas en vez de 10. Las semillas 11 a 20 no se usaron para nada
#     antes, así que sirven de muestra nueva del "cierra en 10 de 10".
#   - Los números se leen directo de los logs de nextpnr con tools/leer_pnr.py,
#     no de la línea de resumen de medir_variante.sh.
#   - I1 con el programa del fondo (sw/fondo.s de b_fondo_hilos) en la memoria
#     en vez de la regla base. El contenido de las BRAM no debería cambiar ni
#     las celdas ni el timing, y aquí queda medido.
#   - Un segundo analizador de timing, icetime, sobre el .asc de cada semilla.
#     En el segmentado (I3) icetime no entiende las rutas de medio ciclo
#     (docs/espino_segmentado.md), así que ahí vale solo como referencia.
#   - El bitstream de la semilla 1 de esta medición (icepack del .asc) contra
#     el sha256 que informa la pieza en mediciones/bitstreams.txt. La pieza
#     dice que el sha256 se reproduce. Aquí se comprueba con una síntesis
#     hecha desde las listas de fuentes de esta carpeta.
#
# Uso: factibilidad/auditoria_hw/tools/recursos.sh   (o make recursos)
# Resultado en mediciones/recursos.txt. Unos 6 minutos con 5 procesos.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

SEMILLAS=${SEMILLAS:-20}
O=$B/recursos
mkdir -p "$O"
regla_base_h0 "$O/trade_h0.hex" || exit 1
$PYTHON tools/pochoasm.py $F/sw/fondo.s -o "$O/fondo.hex" > /dev/null || exit 1
enlazar "$O/rtl_i"   $SRC_I
enlazar "$O/rtl_seg" $SRC_SEG

# etiqueta | carpeta de fuentes | definiciones | programa | qué es | valores del README: celdas BRAM fmin fmed fmax
CONFIGS="i1a|$O/rtl_i|$DEFS_I1A|$O/trade_h0.hex|I1 fondo en un chip, tabla de 256 x 16|1071 13 46.76 48.62 50.48
i1b|$O/rtl_i|$DEFS_I1B|$O/trade_h0.hex|I1 con 16 BRAM|1098 16 44.94 48.07 51.83
i2|$O/rtl_i|$DEFS_I2|$O/trade_h0.hex|I2 barrel y vigilante|939 12 50.95 53.59 56.09
i3a|$O/rtl_seg|$DEFS_I3A|sw/trade.hex|I3 segmentado, emad y vigilante|1046 12 48.02 52.36 53.25
i3b|$O/rtl_seg|$DEFS_I3B|sw/trade.hex|I3 con emad, devk y mulstep|1142 12 46.59 48.05 49.14
i1a_fondo|$O/rtl_i|$DEFS_I1A|$O/fondo.hex|I1 con el programa del fondo en la memoria (fondo en un chip); se compara con las cifras de I1|1071 13 46.76 48.62 50.48"

T0=$(date +%s)
while IFS='|' read -r etq rtl defs hex desc readme; do
  RTL=$rtl HEX=$hex DEFS="$defs" JOBS=$JOBS tools/medir_variante.sh "fact2_auditoria_hw_$etq" "$SEMILLAS" > "$O/$etq.linea.txt" 2> "$O/$etq.err" < /dev/null
  # icetime sobre cada semilla que nextpnr terminó
  for s in $(seq 1 "$SEMILLAS"); do
    a=build/variantes/fact2_auditoria_hw_$etq/soc.s$s.asc
    [ -s "$a" ] && echo "$a"
  done | xargs -P "$JOBS" -I{} sh -c 'icetime -d hx1k -P vq100 -p goboard.pcf -t {} > {}.icetime.txt 2>&1'
  echo "medido $etq [$(( $(date +%s) - T0 )) s]" >&2
done <<< "$CONFIGS"
T1=$(date +%s)

{
echo "Auditoría: celdas, BRAM y frecuencia máxima de I1, I2 e I3, medidos de nuevo"
echo "Generado por factibilidad/auditoria_hw/tools/recursos.sh (make recursos). No editar a mano."
echo
versiones
echo "  icetime de Project IceStorm (OSS CAD Suite), segundo analizador de timing"
echo "Flujo: tools/medir_variante.sh, nextpnr-ice40 --hx1k --package vq100 --freq 25, goboard.pcf, semillas 1 a $SEMILLAS."
echo "Fuentes y definiciones: tools/comun.sh de esta carpeta. Demora: $((T1 - T0)) s con $JOBS procesos."
echo
$PYTHON $U/tools/leer_pnr.py "$SEMILLAS" <<< "$CONFIGS"
echo
echo "Bitstream de la semilla 1 de esta medición (icepack del .asc) contra el sha256 que informa la pieza"
echo "(factibilidad/i_integrado/mediciones/bitstreams.txt, hecho con los scripts de la pieza):"
malos=0
for e in i1a i1b i2 i3a i3b; do
  icepack "build/variantes/fact2_auditoria_hw_$e/soc.s1.asc" "$O/$e.s1.bin" 2> /dev/null
  a=$(sha256sum "$O/$e.s1.bin" 2> /dev/null | cut -d' ' -f1)
  b=$(grep -A2 "^$e:" $I/mediciones/bitstreams.txt | grep -o 'sha256 [0-9a-f]*' | cut -d' ' -f2)
  if [ -n "$a" ] && [ "$a" = "$b" ]; then echo "PASS $e: $(stat -c %s "$O/$e.s1.bin") bytes, sha256 $a, el mismo que informa la pieza"
  else echo "FAIL $e: sha256 ${a:-sin bitstream}, la pieza informa ${b:-nada}"; malos=$((malos + 1)); fi
done
if [ $malos = 0 ]; then echo "RESULTADO de los bitstreams: PASS, los cinco sha256 se reproducen"
else echo "RESULTADO de los bitstreams: FAIL ($malos distintos)"; fi
} | tee "$M/recursos.txt"

! grep -q "^FAIL" "$M/recursos.txt"
