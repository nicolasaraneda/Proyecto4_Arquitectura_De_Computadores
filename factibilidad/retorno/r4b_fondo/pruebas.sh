#!/bin/sh
# pruebas.sh: comprobaciones del módulo fondo.c antes de usarlo en el estudio.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
#   1. Causalidad: el fondo no mira el futuro (comando causal del arnés).
#   2. Identidad: con todo el peso en un gestor y df=0, el fondo escribe los
#      mismos bytes que ese gestor solo, en los 20 000 ticks de práctica.
#   3. Desfase: con df=1 escribe los bytes del gestor atrasados un tick.
#   4. Espejo: la cuenta que lleva el supervisor coincide con la real en
#      todos los ticks de un lote de series (contador 3 en cero).
#
# Uso: sh pruebas.sh build/arnes ../../../tb/practica.csv
B=$1; S=$2; T=build/prueba; mkdir -p $T; falla=0
echo "== 1. Causalidad =="
for v in "fondo:c=1" "fondo:c=1,w0=12,w1=2,w2=2,b=1" "fondo:c=2,m=1,v=9,mg=6" "fondo:c=3,m=2,w0=12,w1=2,w2=2,v=8,mg=7,d=4" \
         "fondo:c=1,m=1,v=0,mg=5,pp=1,df=1" "fondo:c=4,w0=8,w1=4,w2=4,vt=8,df=1" "fondo:c=1,x=cand:activo,w0=8,w1=2,w2=2,w3=4"; do
  $B causal --estrategia "$v" | tail -2 || falla=1
done
echo "== 2. Identidad: todo el peso en un gestor =="
ident() {  # conjunto, pesos, gestor
  $B correr --estrategia "fondo:c=$1,$2" --serie $S -o $T/f.csv > /dev/null
  $B correr --estrategia "$3" --serie $S -o $T/g.csv > /dev/null
  if cmp -s $T/f.csv $T/g.csv; then echo "  ok    fondo:c=$1,$2 = $3 (20000 filas identicas)"; else echo "  FALLA fondo:c=$1,$2 contra $3"; falla=1; fi
}
ident 1 "w0=16" max_media; ident 1 "w0=0,w1=16" prudente; ident 1 "w0=0,w2=16" "byh:q=63,rep=1"
ident 2 "w0=0,w1=16" guardia; ident 3 "w0=0,w1=16" kalman; ident 3 "w0=0,w2=16" activo; ident 4 "w0=0,w1=16" base
ident 1 "x=cand:kalman,w0=0,w3=16" kalman
ident 1 "m=1,v=0,mg=0,w0=16,pp=1" max_media >/dev/null   # (el líder puede cambiar: no es identidad, solo se corre)
echo "== 3. Desfase de un tick =="
$B correr --estrategia "fondo:c=1,w0=16,df=1" --serie $S -o $T/f.csv > /dev/null
$B correr --estrategia max_media --serie $S -o $T/g.csv > /dev/null
python3 - $T/f.csv $T/g.csv <<'PY' || falla=1
import sys
f = [l.split(',')[2] for l in open(sys.argv[1]).read().split('\n')[1:] if l]
g = [l.split(',')[2] for l in open(sys.argv[2]).read().split('\n')[1:] if l]
malas = sum(1 for t in range(2, len(f)) if f[t] != g[t - 1])
print("  %s  fondo con df=1: byte leido en t igual al de max_media en t-1, %d filas, %d distintas (t=1 lee %s)" %
      ("ok   " if malas == 0 else "FALLA", len(f) - 2, malas, f[1]))
sys.exit(1 if malas else 0)
PY
echo "== 4. Espejo de la cuenta real (contador 3 = ticks con diferencia) =="
for lote in remuestreo_s0_n2000 modelo_s0_n2000 saltos_s0_n2000 borde_bajo_s0_n2000 borde_alto_s0_n2000; do
  for v in "fondo:c=1,w0=12,w1=2,w2=2,b=1" "fondo:c=2,m=2,w0=10,w1=4,w2=2,v=8,mg=7,d=4,b=0,df=1" "fondo:c=3,w0=8,w1=4,w2=4,b=2"; do
    $B detalle --estrategia "$v" --lote ../build/series/$lote.bin | awk -v n="$lote $v" '{s += $6; p += $7; k++} END {
      printf "  %s %-28s series %d, ticks con objetivo parcial %d, ticks con el espejo distinto %d\n", (s == 0 ? "ok   " : "FALLA"), n, k, p, s; exit (s != 0)}' || falla=1
  done
done
if [ $falla = 0 ]; then echo "PASS: todas las comprobaciones"; else echo "FAIL: hay comprobaciones que no pasan"; fi
exit $falla
