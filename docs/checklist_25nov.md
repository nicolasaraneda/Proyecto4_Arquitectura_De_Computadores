# Checklist del miércoles 25/11 (por confirmar): R2 y R3 con la maestra real

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Una página, en orden. No agrega pasos: resume `docs/c1_dia_de_prueba.md` (R3) y `docs/checklist_26nov.md` (conexión, medidor y R2), que tienen el detalle y las tablas de lectura. Etiqueta del congelamiento: `v-maestra-25nov`. La regla de decisión es de Nicolás (21/11) y está al final.

## 0. Qué llevar

- [ ] Go Board, cable USB, 4 cables hembra-hembra para el PMOD (`CS_n` 1, `MOSI` 2, `MISO` 3, `SCLK` 4) y uno de tierra (5 u 11). Verificar los números del PMOD con el ayudante. **La tierra se conecta primero.**
- [ ] Mac con el repo en la rama `c1`, en el commit de la etiqueta `v-maestra-25nov` (`git checkout v-maestra-25nov`), e `iceprog` funcionando.
- [ ] Hashes verificados: `cd bitstreams && sha256sum -c SHA256SUMS && cd ..` con todas las líneas en `OK` (en Mac, si falta `sha256sum`: `shasum -a 256 -c SHA256SUMS`). Se usan `medidor_spi.bin`, `r2_banda40_multi.bin` y `r3_c1_multi.bin`; si sobra tiempo, `r3_c1_apagada_multi.bin` y `r3_c1_falla_multi.bin`.
- [ ] Plantilla impresa (`docs/c1_dia_de_prueba.md`, sección 8) y las preguntas para el ayudante (`docs/checklist_26nov.md`, sección 6).

## 1. Paso 0: el medidor, antes que R2 y R3

1. `iceprog bitstreams/medidor_spi.bin`. Con "VERIFY OK": LED apagados y `FF`. Si falla, repetir con `-b`.
2. Pedir una ronda, mejor la de 0,1 ms. Sin apretar SW3, leer con SW1 las medidas 0 y 1 (byte bajo; con SW4, el alto). Decide la **medida 1** (SCLK más lento, en ciclos de 40 ns; kHz = 25 000 / medida).

| Medida 1 | SCLK | Qué se hace |
|----------|------|-------------|
| 100 (`0x0064`) o menos | 250 kHz o más | R3 sigue |
| 101 a 166 | entre 150 y 250 kHz | R3 sigue. Anotar el SCLK, la medida 6 y la medida 6 menos 916 |
| 167 (`0x00A7`) o más | menos de 150 kHz | **Compite la banda 40.** R3 no se prueba como candidato |

Si LED4 se enciende (otro número de flancos, flancos con `CS_n` en alto, o modo 2 o 3), anotarlo y aplicar `docs/checklist_26nov.md`, sección 3.

## 2. R2 con la banda 40 (la vara de comparación)

1. `iceprog -b bitstreams/r2_banda40_multi.bin`.
2. Por cada ronda: desconectar el USB, esperar un par de segundos, conectar, esperar dos segundos. Tiene que verse `00` y los LED apagados. Recién ahí pedir la partida.
3. Anotar el patrimonio de la pantalla de cada ronda. No debe pasar a R0: si la telemetría desaparece a mitad de ronda, el vigilante disparó; anotar cuándo.

## 3. R3 con C1 (solo si el medidor lo permitió)

1. `iceprog -b bitstreams/r3_c1_multi.bin`. Anotar el hash que imprime `sha256sum`.
2. Misma rutina de reinicio por ronda. Antes de partir: `00` y **LED1 apagado**. Con la primera partida, `10` en los 7 segmentos y `27` con SW1 apretado.
3. Al terminar cada ronda leer la placa (`docs/c1_dia_de_prueba.md`, secciones 3 y 4): a 10 ms, en los últimos 30 s, SW1, SW1 + SW2 (modo), SW3 y SW3 + SW1 (caja), SW4 (acciones), y al final queda congelado el byte bajo. A 1 ms y 0,1 ms, un byte por partida: o el byte bajo sin tocar nada, o el segundo con SW1 apretado toda la ronda.
4. Si sobra tiempo: `r3_c1_apagada_multi.bin` (tiene que dar el patrimonio de R2) y `r3_c1_falla_multi.bin` (relevo a R0, unos 361 ticks sin decisión nueva a 0,1 ms).

## 4. Verificación con Meta a 10 ms (si la maestra la permite)

Con `data/practica_meta.csv` a 10 ms: compra de 22 en la fase A en el **tick 8234 al precio 222** (byte `0x56`, caja 5 111; SW4 `16`, SW3 `F7`), venta en el 10966 (precio 250), 6 órdenes, **patrimonio 22 682** (caja 22 682, acciones 0, modo `02`; byte bajo `9A`, SW1 `58`). La orden 1 cae a los 82 s de la ronda. Si la primera compra no ocurre en ese tick y precio, anotar tick, precio, acciones y caja.

## 5. Qué anotar en cada ronda

Período y ticks; patrimonio de la pantalla de la maestra; byte bajo, segundo byte, caja y acciones de la placa; modo; LED1; patrimonio de R2 en la misma ronda; si calza; hash grabado; SCLK medido y margen. Si la serie es conocida, valores esperados de R3 (banda 40 entre paréntesis): Meta 22 682 (21 392), Tesla 21 224 (20 795), AMD 27 199 (26 470). Para una serie registrada: `python3 ref/c1/c1.py SERIE.csv --placa`.

## 6. Regla de decisión (Nicolás, 21/11)

- **R3 compite** solo si el medidor lo permitió, la caja y el patrimonio de la placa calzan con la pantalla de la maestra en las rondas leídas, el LED1 no se encendió sin causa (más de 20 000 ticks desde el reset o un precio bajo 100), y no se perdieron precios ni decisiones.
- **Compite la banda 40** (R2 o R0 según `docs/arbol_decision.md`) si R3 falla en cualquiera de esos puntos, o si el SCLK medido es bajo (medida 1 de 167 o más). Se anota la diferencia, la ronda, el modo y los bytes leídos, y esa noche se compara con la serie registrada.
