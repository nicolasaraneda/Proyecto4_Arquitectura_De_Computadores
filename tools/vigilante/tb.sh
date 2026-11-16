#!/usr/bin/env bash
# tb.sh: corre el testbench unitario del vigilante (tb/vigilante/tb_vigilante.v)
# para varios valores de N.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# El testbench tiene casos dirigidos (programa sano, N precios sin respuesta,
# el precio N + 1, la espera a que CS_n suba, la escritura simultánea con el
# precio, BOOT que no baja, maestra detenida) y una parte aleatoria contra un
# modelo de referencia. Se corre con N = 1, 2, 4, 7 y 15. El SoC de competencia
# usa N = 4 (parámetro VigN de rtl/pochoco_soc.v).
#
# Uso, desde cualquier carpeta del repositorio:
#   tools/vigilante/tb.sh          (make vig-tb)
# Resultado en docs/mediciones/vigilante/tb.txt. Termina con error si alguna
# comprobación da FAIL.
set -uo pipefail
export HW=r2
source "$(dirname "${BASH_SOURCE[0]}")/../fondo/comun.sh"

BV=build/vigilante/tb
MV=docs/mediciones/vigilante
INF=$MV/tb.txt
VALORES="1 2 4 7 15"
mkdir -p "$BV" "$MV"

{
  echo "Testbench unitario del vigilante (tb/vigilante/tb_vigilante.v)"
  echo "Generado por tools/vigilante/tb.sh (make vig-tb). No editar a mano."
  echo
  versiones
  echo "Modulo: rtl/vigilante.v (sha256 $(sha256sum rtl/vigilante.v | cut -c1-16)...)"
  echo "Valores de N: $VALORES. El SoC de competencia usa N = $(sed -n 's/.*parameter  *VigN  *= *\([0-9]*\).*/\1/p' rtl/pochoco_soc.v)."
  echo
  for n in $VALORES; do
    if iverilog -g2012 -DN_VIG=$n -s tb_vigilante -o "$BV/tb_n$n.vvp" rtl/vigilante.v tb/vigilante/tb_vigilante.v > "$BV/tb_n$n.iverilog.log" 2>&1; then
      vvp -n "$BV/tb_n$n.vvp" 2>&1 | grep -v "finish called" > "$BV/tb_n$n.log"
    else
      echo "FAIL N=$n el testbench no compila (ver $BV/tb_n$n.iverilog.log)" > "$BV/tb_n$n.log"
    fi
    cat "$BV/tb_n$n.log"
    # Una corrida que se corta antes del resumen también es una falla
    grep -q "^RESUMEN N=$n " "$BV/tb_n$n.log" || echo "FAIL N=$n la simulacion no llego al resumen"
    echo
  done
} > "$INF" 2>&1

{
  echo "Total: $(grep -c '^PASS' "$INF") comprobaciones con PASS y $(grep -c '^FAIL' "$INF") con FAIL, en $(echo $VALORES | wc -w) valores de N."
} >> "$INF"
cat "$INF"
cierre "$INF"
