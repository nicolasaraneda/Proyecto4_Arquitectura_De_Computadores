#!/bin/sh
# pruebas.sh: comprobaciones de las piezas propias del estudio de cierre (fondoc.c y final.c).
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
#   1. Causalidad de todas las configuraciones nuevas (comando causal del arnés).
#   2. `fondoc` con em=0 decide igual que `fondo` (la copia no cambió nada más).
#   3. `filtro` sobre max_media y `fondoc` con todo el peso en max_media, los dos
#      con m = 8, deciden igual que `ejec:m=8` del estudio de ejecución.
#   4. El espejo del supervisor coincide con la cuenta real también cuando el
#      supervisor suprime compras (contador 3 en cero).
#   5. Control negativo: con em=8 el fondo sí cambia.
#
# Las identidades se comprueban serie por serie (patrimonio, órdenes y pérdida
# máxima de cada serie, comando detalle) en lotes de la semilla 0 de los dos
# largos, y byte a byte en la serie de práctica completa (comando correr).
#
# Uso: sh pruebas.sh build/arnes ../../../tb/practica.csv
B=$1; S=$2; T=build/prueba; mkdir -p $T; falla=0
LOTES="remuestreo_s0_n2000 modelo_s0_n2000 dos_componentes_s0_n2000 tendencia_s0_n2000 saltos_s0_n2000 nivel_bajo_s0_n2000 borde_bajo_s0_n2000 borde_alto_s0_n2000 cambio_volatilidad_s0_n20000 paseo_s0_n20000"

echo "== 1. Causalidad =="
for v in "filtro" espera_e rec_e min_e completo completo_s completo_esp completo_ap completo_ancla completo_min; do
  $B causal --estrategia "$v" | tail -1 | sed "s/^/  $v: /" || falla=1
  $B causal --estrategia "$v" | grep -q "^PASS" || falla=1
done

igual() {  # nombre A, nombre B: mismas tres primeras columnas de detalle en todos los lotes y mismos bytes en la práctica
  series=0; malas=0
  for lote in $LOTES; do
    $B detalle --estrategia "$1" --lote ../build/series/$lote.bin | cut -d' ' -f1-3 > $T/a.txt
    $B detalle --estrategia "$2" --lote ../build/series/$lote.bin | cut -d' ' -f1-3 > $T/b.txt
    n=$(wc -l < $T/a.txt); d=$(paste -d'|' $T/a.txt $T/b.txt | awk -F'|' '$1 != $2' | wc -l)
    series=$((series + n)); malas=$((malas + d))
  done
  $B correr --estrategia "$1" --serie $S -o $T/a.csv > /dev/null
  $B correr --estrategia "$2" --serie $S -o $T/b.csv > /dev/null
  if cmp -s $T/a.csv $T/b.csv; then bytes="practica identica byte a byte"; else bytes="practica DISTINTA"; fi
  echo "$series $malas $bytes"
}
identidad() {
  r=$(igual "$1" "$2")
  case "$r" in *" 0 practica identica"*) echo "  ok    $1 = $2: $r" ;; *) echo "  FALLA $1 contra $2: $r"; falla=1 ;; esac
}
distinta() {
  r=$(igual "$1" "$2")
  case "$r" in *" 0 practica identica"*) echo "  FALLA $1 deberia diferir de $2: $r"; falla=1 ;; *) echo "  ok    $1 difiere de $2: $r" ;; esac
}

echo "== 2. fondoc con em=0 es fondo (series, series distintas, serie de practica) =="
identidad "fondoc:c=3,w0=8,w1=4,w2=4,b=4" fondo_rec
identidad "fondoc:c=1,w0=12,w1=2,w2=2,b=2" fondo_ancla
identidad "fondoc:c=5,w0=6,w1=5,w2=5,m=2,v=9,mg=5,d=4,pp=1,vt=8" fondo_min
identidad completo_s "fondo:c=3,x=cand:aprendiz,w0=6,w1=3,w2=3,w3=4,b=4"
identidad "fondoc:c=1,m=2,w0=12,w1=2,w2=2,v=9,mg=6,d=4,b=1" "fondo:c=1,m=2,w0=12,w1=2,w2=2,v=9,mg=6,d=4,b=1"

echo "== 3. La ejecucion A puesta por fuera y en el supervisor es ejec:m=8 =="
identidad "filtro:x=cand:max_media,m=8" "ejec:m=8"
identidad "fondoc:c=3,w0=16,em=8" "ejec:m=8"
identidad "fondoc:c=5,w0=16,vt=8,em=8" "ejec:m=8"
identidad "filtro:x=cand:max_media,m=0" max_media

echo "== 4. Espejo del supervisor con compras suprimidas (contador 3 = ticks con diferencia) =="
for v in rec_e completo completo_ap completo_ancla completo_min; do
  for lote in $LOTES; do $B detalle --estrategia "$v" --lote ../build/series/$lote.bin; done | awk -v n="$v" '{s += $6; p += $7; k++} END {
    printf "  %s %-16s series %d, ticks con objetivo parcial %d, ticks con el espejo distinto %d\n", (s == 0 ? "ok   " : "FALLA"), n, k, p, s; exit (s != 0)}' || falla=1
done

echo "== 5. Control negativo =="
distinta rec_e fondo_rec
distinta completo completo_s

if [ $falla = 0 ]; then echo "PASS: todas las comprobaciones"; else echo "FAIL: hay comprobaciones que no pasan"; fi
exit $falla
