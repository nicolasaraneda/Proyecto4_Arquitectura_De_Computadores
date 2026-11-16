#!/bin/sh
# bytes.sh: flujo de bytes de DECISION de una configuración del fondo para una serie dada.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Es la referencia para comparar byte a byte el programa en assembly del barrel.
#
#   sh bytes.sh build/arnes fondo_rec ../../../tb/practica.csv mediciones/bytes_fondo_rec_practica.txt
#
# Deja en build/:
#   decisiones_NOMBRE.csv   tick, precio, byte que la maestra lee en ese tick, caja, acciones, patrimonio
#                           (mismo formato que el decisiones.csv del testbench)
#   bytes_NOMBRE.hex        un byte por línea, en hexadecimal: el que la maestra lee en cada tick
#   traza_NOMBRE.csv        estado interno por tick: cuenta real, posición y desempeño de cada gestor, pesos, F y decisión
# y en el archivo de salida (cuarto argumento) el resumen versionable: comando, resultado, huella y primeros bytes.
B=$1; N=$2; S=$3; SALIDA=$4
mkdir -p build
FONDO_TRAZA=build/traza_$N.csv HILOS=1 $B correr --estrategia $N --serie $S -o build/decisiones_$N.csv > build/bytes_$N.resumen || exit 1
tail -n +2 build/decisiones_$N.csv | cut -d, -f3 > build/bytes_$N.hex
{
  echo "Flujo de bytes de DECISION: configuracion $N, serie $S"
  echo "Comando: sh bytes.sh $B $N $S $SALIDA"
  cat build/bytes_$N.resumen
  echo "Bytes (uno por tick, el que la maestra lee en ese tick): $(wc -l < build/bytes_$N.hex)"
  echo "Huella md5 de build/bytes_$N.hex: $(md5sum < build/bytes_$N.hex | cut -d' ' -f1)"
  echo "Huella md5 de build/decisiones_$N.csv: $(md5sum < build/decisiones_$N.csv | cut -d' ' -f1)"
  echo "Huella md5 de build/traza_$N.csv: $(md5sum < build/traza_$N.csv | cut -d' ' -f1)"
  echo "Veces que aparece cada byte:"
  sort build/bytes_$N.hex | uniq -c | sort -rn | head -12 | awk '{printf "  %s: %d\n", $2, $1}'
  echo "Bytes distintos: $(sort -u build/bytes_$N.hex | wc -l)"
  echo "Primeros 80 bytes:"
  head -80 build/bytes_$N.hex | tr '\n' ' ' | fold -w 60
  echo
  echo "Primeras 12 filas de la traza (tick, precio, caja, acciones, pos0..2, desempeno0..2, pesos0..2, F, decision):"
  head -13 build/traza_$N.csv
  echo "Filas 110 a 130 de la traza:"
  sed -n '111,131p' build/traza_$N.csv
} > $SALIDA
tail -n +2 $SALIDA | head -8
