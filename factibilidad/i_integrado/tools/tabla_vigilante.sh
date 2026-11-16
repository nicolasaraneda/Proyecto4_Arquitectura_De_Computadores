#!/usr/bin/env bash
# tabla_vigilante.sh: pruebas de la memoria para la tabla de política y del
# vigilante sobre el barrel.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Memoria de la tabla:
#   - tb/tb_tabla_mod.sv: tabla_mmio y tabla_ram solos, 200 000 accesos al
#     azar contra un modelo, con tres semillas, y el contenido inicial
#     cargado de un archivo.
#   - tb/tb_tabla.sv: sw/tabla_prueba.s en el SoC, con los cuatro hilos
#     inicializando, leyendo y ajustando cada uno su cuarto de la tabla. En
#     las dos formas, sola y dentro de la configuración I1 (con la extensión
#     y el vigilante).
# Vigilante:
#   - tb/tb_vig_barrel.sv: sw/cuelgue_supervisor.s, con el hilo supervisor
#     colgado y los otros tres escribiendo en la memoria. Con N = 4 y N = 1,
#     a los períodos de las rondas 3 y 2, solo y dentro de I1.
#   El módulo vigilante tiene su testbench y su prueba formal en
#   factibilidad/e_warmboot. Que no dispare con el programa sano lo comprueba
#   tools/oficial.sh con el testbench oficial.
#
# Uso: factibilidad/i_integrado/tools/tabla_vigilante.sh   (o make tabla-vigilante)
# Resultado en mediciones/tabla_vigilante.txt. Menos de un minuto.
set -uo pipefail
source "$(dirname "$0")/comun.sh"
source "$I/tools/pruebas_comun.sh"

O=$B/tabla_vig
mkdir -p "$O"
programas_prueba
MEDIA="$(defs_de media_mul)"

{
echo "Memoria para la tabla de política y vigilante sobre el barrel"
echo "Generado por factibilidad/i_integrado/tools/tabla_vigilante.sh (make tabla-vigilante). No editar a mano."
echo
versiones
echo
echo "1. Módulos tabla_mmio (256 x 16) y tabla_ram (512 x 32) solos, accesos al azar contra un modelo"
for s in 1 2 3; do
  echo -n "   semilla $s: "
  SEMILLA_TABLA=$s CICLOS_TABLA=200000 correr_tabla_mod "$O/mod_s$s"
done
echo
echo "2. sw/tabla_prueba.s en el SoC: los cuatro hilos usan cada uno su cuarto de la tabla"
echo -n "   forma 1 (BRAM de 256 x 16 por MMIO), SoC con -DI_TABLA=1:                 "; correr_tabla "$O/solo" 1
echo -n "   forma 2 (otras 512 palabras de datos), SoC con -DI_TABLA=2:               "; correr_tabla "$O/solo" 2
echo -n "   forma 1 dentro de I1 (emad, devk, mulstep y vigilante):                   "; DEFS_PRUEBA="$MEDIA -DI_VIGILANTE" correr_tabla "$O/i1" 1
echo -n "   forma 2 dentro de I1 (emad, devk, mulstep y vigilante):                   "; DEFS_PRUEBA="$MEDIA -DI_VIGILANTE" correr_tabla "$O/i1" 2
echo
echo "3. sw/cuelgue_supervisor.s: el hilo supervisor se cuelga después de 20 precios y los otros tres siguen"
echo -n "   N = 4, período 0,1 ms, SoC con -DI_VIGILANTE:        "; correr_vig "$O/solo" 4
echo -n "   N = 1, período 0,1 ms:                               "; correr_vig "$O/solo" 1
echo -n "   N = 4, período 1 ms:                                 "; PERIODO_VIG=1000000 correr_vig "$O/p1ms" 4
echo -n "   N = 4, período 0,1 ms, dentro de I1 con la tabla 1:  "; DEFS_PRUEBA="$MEDIA -DI_TABLA=1" correr_vig "$O/i1a" 4
echo -n "   N = 4, período 0,1 ms, dentro de I1 con la tabla 2:  "; DEFS_PRUEBA="$MEDIA -DI_TABLA=2" correr_vig "$O/i1b" 4
echo
} > "$O/cuerpo.txt"
{
cat "$O/cuerpo.txt"
if grep -q "FAIL" "$O/cuerpo.txt"; then echo "RESULTADO: FAIL"; else echo "RESULTADO: PASS, $(grep -c PASS "$O/cuerpo.txt") pruebas"; fi
} | tee "$M/tabla_vigilante.txt"

grep -q "^RESULTADO: PASS" "$M/tabla_vigilante.txt"
