# Variantes de contingencia de la regla de cotas

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Bitstreams de la variante "comprar 20 al inicio, banda 70" (`docs/cotas.md`, opción R-b), para usar solo si el ayudante confirma que **cada ronda se normaliza por separado** y Nicolás la elige. El hardware de cada uno es el mismo del peldaño oficial: solo cambia el programa (y en R1 y R2 la tabla), puestos con `icebram` sobre los moldes. Cambiar de regla es elegir el archivo: no hay que sintetizar ni reconstruir nada.

| Archivo | Peldaño | Regla | Puerta | sha256 |
|---------|---------|-------|--------|--------|
| `r0_p20b70.bin` | R0 | `sw/variantes/trade_p20b70.s`: compra 20 con el primer precio, compra en 100 y vende en 255, y después de ver los dos, compra con p ≤ 170 y vende con p ≥ 185 | Completa (`docs/mediciones/variantes/r0_p20b70.txt`, `tools/variante_cotas.sh`): oficial 4/4 (78 ciclos), equivalencia, 3810 series, fases, estrés, exhaustiva y el `.asc` por los pines | ver `SHA256SUMS` |

R1 y R2 se agregan cuando estén los programas nuevos de esos peldaños.

Comprobar antes de grabar: `cd bitstreams/variantes && sha256sum -c SHA256SUMS`.
