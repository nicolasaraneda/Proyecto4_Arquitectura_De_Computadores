#!/usr/bin/env bash
# variante_cotas_r1.sh: puerta de simulación de R1 y R2 con la variante "comprar 20 al
# inicio, banda 70" de la regla de cotas, y sus bitstreams desde los moldes.
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# Igual que tools/variante_cotas.sh para R0: arma una copia de trabajo del commit actual
# en build/variante_r1_p20b70/ y pone ahí la variante como si fuera la oficial:
#   sw/fondo.s       <- sw/variantes/fondo_p20b70.s (la compra inicial es código)
#   sw/trade.s       <- sw/variantes/trade_p20b70.s (la imagen de R0 dentro de R2)
#   ref/fondo.py     banda 70 en la tabla (171 y 185) y la compra inicial en el modelo
#   ref/trader.py    Oficial = Cotas("parte", k=20, banda=70)
#   sw/fondo_tabla.hex regenerada desde ref/fondo.py
# y corre, para HW=r1 y HW=r2, las pruebas de la puerta salvo el timing (el hardware no
# cambia: los bitstreams salen de los moldes): referencia, tabla, oficial, equivalencia,
# series, fases, degradación, controles y estrés; después los bitstreams sobre los moldes
# (tools/fondo/molde_cotas.sh) y su simulación por los pines.
# Bitstreams en bitstreams/variantes/, registro en docs/mediciones/variantes/r1_r2_p20b70.txt.
#
# Uso: tools/variante_cotas_r1.sh   (unas 2 horas)
set -uo pipefail
RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$RAIZ"
W=build/variante_r1_p20b70
SALIDA=docs/mediciones/variantes/r1_r2_p20b70.txt
mkdir -p docs/mediciones/variantes bitstreams/variantes
rm -rf "$W"; git worktree prune
git worktree add -q --detach "$W" HEAD
cp sw/variantes/fondo_p20b70.s "$W/sw/fondo.s"
cp sw/variantes/trade_p20b70.s "$W/sw/trade.s"
cd "$W"
python3 - <<'PY'
def rep(p, pares):
    s = open(p, encoding="utf-8").read()
    for o, n in pares:
        assert o in s, (p, o[:60])
        s = s.replace(o, n)
    open(p, "w", encoding="utf-8").write(s)
rep("ref/trader.py", [('super().__init__("espera", banda=60)', 'super().__init__("parte", k=20, banda=70)')])
rep("ref/test_fondo.py", [("(19214, 4, 1, 1)", "(24671, 19, 1, 1)")])     # la variante en la serie Meta
rep("ref/fondo.py", [
    ('("BANDA_COMPRA", 161),', '("BANDA_COMPRA", 171),'),
    ('("BANDA_VENTA", 195),', '("BANDA_VENTA", 185),'),
    ('''        if comprar or vender:
            self.byte = market.VENDER_63 if vender else market.COMPRAR_63''',
     '''        if comprar or vender:
            self.byte = market.VENDER_63 if vender else market.COMPRAR_63
        escrito = self.byte
        if t == 1 and not (bajo or alto):      # variante: comprar 20 con el primer precio
            escrito = 0x40 | 20'''),
    ('''            self.traza.append((t, p, self.byte, bajo, alto, self.vio_lo, self.vio_hi, self.leds, self.seg))
        return self.byte''',
     '''            self.traza.append((t, p, escrito, bajo, alto, self.vio_lo, self.vio_hi, self.leds, self.seg))
        return escrito'''),
])
PY
python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex > /dev/null
python3 ref/fondo.py --tabla-hex sw/fondo_tabla.hex > /dev/null
f=0
paso() { echo "== $*"; if "$@" > build/paso.log 2>&1; then echo "PASS: $*"; else echo "FAIL: $*"; f=$((f+1)); fi;
         grep -E '^(PASS|FAIL)|Peor caso|Patrimonio|Testbenchs' build/paso.log | grep -v '^PASS: ' | cut -c1-200 | head -40; }
{
echo "Puerta de simulacion de R1 y R2 con la variante comprar 20 al inicio, banda 70 de la regla de cotas"
echo "Generado por tools/variante_cotas_r1.sh sobre $(git -C "$RAIZ" rev-parse --short HEAD)."
echo
paso python3 ref/test_fondo.py
paso python3 ref/test_cotas.py
for hw in r1 r2; do
  echo; echo "######## $hw"
  for t in check-tabla fondo-oficial fondo-equiv-ronda1 fondo-series fondo-fases fondo-degradacion fondo-controles fondo-estres; do
    paso make $t HW=$hw
  done
done
echo; echo "######## bitstreams sobre los moldes"
paso make fondo-molde-cotas
for b in r0_cotas r1_cotas r2_cotas r2_cotas_multi; do
  [ -f build/fondo/molde_cotas/$b.bin ] && cp build/fondo/molde_cotas/$b.bin "$RAIZ/bitstreams/variantes/${b/cotas/p20b70}.bin" \
    && echo "bitstreams/variantes/${b/cotas/p20b70}.bin: sha256 $(sha256sum build/fondo/molde_cotas/$b.bin | cut -d' ' -f1)"
done
echo
if [ "$f" -eq 0 ]; then echo "PASS: la variante p20b70 paso la puerta de R1 y R2"; else echo "FAIL: $f pasos fallaron"; fi
} 2>&1 | tee "$RAIZ/$SALIDA"
cd "$RAIZ" && git worktree remove --force "$W"
grep -q '^PASS: la variante' "$SALIDA"
