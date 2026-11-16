#!/bin/sh
# causal.sh: el comando `causal` del arnés para todas las estrategias de los estudios 3 y 4.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Uso: sh causal.sh BINARIO
#
# Corre `causal` sin argumentos (todas las estrategias, alias y rivales
# registrados en el binario, que incluye los módulos de r3_ejecucion,
# r4b_fondo, r4c_aprendizaje y r4_final) y además, una por una, variantes que
# no tienen alias: las que aprenden rápido y las demás formas de repartir.
BIN=$1
mal=0
"$BIN" causal || mal=1
for s in "ejec:m=8" "ejec:m=8,m2=24,e2=32" "ejec:K=2" "ejec:F=12" "ejec:eo=16" "ejec:xc=1,xo=16" \
         "tabla:ka=6,h=16" "tabla:ka=8,h=4" "tabla:ka=8,h=126" "tabla:modo=1,bits=4,h=16" "tabla:banda=1,ka=8,h=16,lim=2" \
         "tabla:ter=1,ka=8,h=8" "tabla:filas=2,ka=8,h=16" "patron:tipo=3,H=12,sim=2,bits=2,h=16" \
         "fondo:c=1,m=1,v=0,mg=6" "fondo:c=3,m=1,v=9,mg=6" "fondo:c=5,m=1,v=6,mg=6,pp=1" \
         "fondo:c=3,w0=6,w1=5,w2=5,m=2,v=6,mg=8,d=6,ps=2" "fondo:c=3,w0=6,w1=5,w2=5,vt=11,vs=0" \
         "fondoc:c=5,x=cand:aprendiz_rapido,w0=4,w1=4,w2=4,w3=4,m=2,v=6,mg=7,d=4,pp=1,vt=8,em=8" \
         "fondoc:c=3,x=tabla:ka~6/h~16,w0=4,w1=4,w2=4,w3=4,m=1,v=6,mg=8,b=1,em=8" "filtro:x=tabla:ka~6/h~16,m=8"; do
  "$BIN" causal --estrategia "$s" | grep -v "^Prueba de causalidad" | grep -v "^PASS" || true
  "$BIN" causal --estrategia "$s" > /dev/null || mal=1
done
if [ $mal = 0 ]; then echo "PASS: comando causal sin fallas en todas las estrategias registradas y en las variantes sin alias"
else echo "FAIL: alguna estrategia no pasa el comando causal"; fi
