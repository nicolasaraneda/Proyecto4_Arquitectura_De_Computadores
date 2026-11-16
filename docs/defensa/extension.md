# Extensión de la ISA: `emad` y `devk` en custom-0

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Documento de estudio para la defensa. Resume y ordena `docs/extension_isa.md`, que es la especificación y la fuente completa. Cifras de `docs/mediciones/xd/`, `docs/mediciones/p7/` y `docs/puertas.md`.

## 1. El problema: lo que más cuesta en `trade.s`

Espino no tiene desplazamientos (el shifter completo no cabe: 1491 celdas de 1280, `docs/mediciones/base.txt`). La regla de reversión guarda la media por 32 (`S`) y en cada tick hace dos cosas con ella:

1. **La desviación**, `dev = 32 p - S`. Sin shifter, `32 p` son cinco sumas: 6 instrucciones (`sw/trade.s:100` a `:106`).
2. **El paso de la media**, `S = S + (dev >>> 5)`. Sin desplazamiento a la derecha, `trade.s` multiplica por 8, guarda en memoria y lee el segundo byte: 8 instrucciones con un store y un load (`sw/trade.s:121` a `:128`).

Las dos son "un desplazamiento por una constante seguido de una suma o una resta". Un desplazamiento por una constante en hardware no es lógica: **son cables**. Lo único que falta es que el operando A del sumador de la ALU pueda venir desplazado. Eso es toda la extensión.

En términos de la ley de hierro, la extensión ataca el **IC**: el estimador pasa de 14 instrucciones a 2. El CPI por hilo del barrel sigue en 4 y el reloj no cambia.

## 2. La especificación

Opcode custom-0 (`0001011`), el que RISC-V reserva para extensiones propias. Formato R.

| Instrucción | `funct3` | `funct7` | Resultado |
|-------------|----------|----------|-----------|
| `emad rd, rs1, rs2, 5` | 100 | 0000101 | `rd = rs2 + (rs1 >>> 5)` |
| `devk rd, rs1, rs2, 5` | 101 | 0000101 | `rd = (rs1 << 5) - rs2` |
| `mulstep rd, rs1, rs2` | 010 | 0000000 | `rd = (rs1 << 1) + (rs1[31] ? rs2 : 0)` |

Fuente: `rtl/espino_core/espino_xd.v:12` a `:15` y `docs/extension_isa.md`, sección 2. **Toda otra palabra de custom-0 es una instrucción ilegal sin efecto**: no escribe, no accede al bus y no salta. Eso incluye `emad` y `devk` con k distinto de 5.

Con estas dos, el estimador completo de un tick son dos instrucciones:

```
devk x9, x8, x4, 5        # dev = 32 p - S        (sw/fondo.s:202)
...                       # decidir con dev
emad x4, x9, x4, 5        # S = S + (dev >>> 5)   (sw/fondo.s:209)
```

Con `rs2 = x0`, `devk` es un desplazamiento de 5 a la izquierda (multiplicar por 32) y `emad` un desplazamiento aritmético de 5 a la derecha.

**R1 y R2 llevan solo `emad` y `devk`.** `mulstep` está construida y verificada, pero `sw/fondo.s` no la usa: era para la contabilidad de la cuenta, que el fondo no lleva porque sus órdenes son idempotentes. Por la regla de Nicolás ("no quiero piezas sin uso en el chip que compite", decisión T58) queda para la edición de exhibición y el ASIC.

## 3. Cómo está construida

Dos módulos chicos en `rtl/espino_core/espino_xd.v` y cuatro puntos de contacto en el core barrel. El decodificador, la ALU y la LSU del Espino **no se tocaron** (decisión T59).

| Paso | Qué hace | Dónde |
|------|----------|-------|
| 1. Etapa R, `espino_xd_dec` | Compara opcode, `funct3` y los 7 bits de `funct7`. Dice si la palabra es `emad`, `devk` o `mulstep` | `rtl/espino_core/espino_xd.v:35`; revisión de k = 5 en `:56` |
| 2. Etapa R, el core | Si es una de las tres, cambia cuatro señales de lo que se registra hacia X: selección 3 del operando A, `rs2` como operando B, suma (resta en `devk`) y escritura de `rd` | `rtl/espino_core/espino_barrel_core.v:198`, `:200` y `:206` |
| 3. Etapa X, `espino_xd_opa` | Entrega el operando A desplazado: `rs1 >>> 5`, `rs1 << 5` o `rs1 << 1`, eligiendo con el `funct3` de la instrucción que está en X | `rtl/espino_core/espino_xd.v:75`; los cables en `:92`, `:98` y `:100` |
| 4. Etapa X, el core | El multiplexor del operando A tiene una entrada más; el resultado sale del sumador de la ALU como un `add` | `rtl/espino_core/espino_barrel_core.v:266` |

No hay sumador nuevo, ni estado, ni cambios en el control del pipeline.

**El error más fácil de cometer en un barrel.** Mientras una instrucción está en X, la palabra que sale de la memoria es de **otro hilo**. `espino_xd_opa` tiene que mirar el `funct3` registrado (`instr_x`), no el que sale de la memoria. Es la mutación `MUTA_XD_HILO`.

## 4. Por qué estas y no otras

| Alternativa | Por qué no | Fuente |
|-------------|------------|--------|
| Shifter completo | No cabe: 1491 celdas en el base | `docs/mediciones/base.txt` |
| `ema` de una instrucción, `rd = rs2 + ((rs1 - rs2) >>> k)` | Encadena resta, desplazamiento y suma: necesita un segundo sumador. 60 a 167 celdas contra 37 de `emad` en la factibilidad. Y el programa necesita la desviación de todas formas para decidir | `docs/extension_isa.md`, sección 4 |
| k variable (0 a 31) | Hace falta un desplazador delante del sumador: unas 160 celdas más y la frecuencia mínima baja de 51,6 a 39,2 MHz (medido en la factibilidad). Con k fijo son cables | idem |
| Multiplicador combinacional de 16 por 8 | No cabe: 1338 celdas en el segmentado (factibilidad) | `docs/extension_isa.md`, sección 12 |

**Por qué k fijo en 5.** El alfa de `max_media` y de las tres bandas del fondo es 1/32, y el estudio del algoritmo encontró que alfa 1/32 es el mejor compromiso (`docs/algoritmo.md`, sección 5.2). Un k fijo son cables; un k variable es un desplazador. Si después del 25/11 el algoritmo necesitara otro alfa, hay que volver a las sumas: el ensamblador rechaza otro k y el core lo trata como ilegal, así que no se puede ejecutar otro k en silencio.

## 5. Costo y efecto

| | Celdas | Fmax mín. | Fuente |
|-|--------|-----------|--------|
| Barrel sin extensión (control) | 938 | 52,11 | `docs/mediciones/xd/timing.txt` |
| `emad` y `devk` (lo de R1) | 990 (+52) | 48,92 | idem |
| Las tres | 1034 (+96) | 48,33 | idem |

El costo es el multiplexor del operando A: una entrada más de 32 bits por instrucción.

| Efecto | Sin extensión | Con `emad` y `devk` | Fuente |
|--------|---------------|---------------------|--------|
| Instrucciones del estimador | 14 | 2 | `docs/extension_isa.md`, sección 12 |
| Respuesta de `max_media` en el barrel, peor caso del testbench | 83 ciclos | 63 ciclos | `docs/puertas.md` (barrel con extensión) |
| Kernel de `max_media`: IC y MOPS | 24 instr., 2,08 MOPS | 12 instr., 4,17 MOPS | `docs/mediciones/p7/variantes.txt` |
| Instrucciones de un gestor del fondo por tick | 35 (factibilidad) | 25 | `docs/fondo.md`, sección 4 |
| Patrimonio | | Igual, bit a bit | `make xd-oficial` |

`emad` y `devk` valen 2 operaciones útiles cada una, como el MAC de la clase (decisión T100).

## 6. Verificación

Tres métodos independientes, cada uno con controles negativos. La especificación está escrita **tres veces por separado**: en el modelo `ref/xd.py`, en el testbench de la campaña y en las propiedades formales.

| Prueba | Resultado | Comando |
|--------|-----------|---------|
| Formal A: cada instrucción contra su especificación, sobre el core, para cualquier programa y cualquier operando (X1 a X5, inducción) | Probadas en los 7 subconjuntos | `make xd-formal` |
| Formal B: el resto del core no cambió (equivalencia con el core de P1 con los pases `equiv_*` de Yosys) | 1890 puntos equivalentes | `make xd-formal` |
| Formal C: la prueba A sirve | 9 de 9 mutaciones con contraejemplo | `make xd-formal` |
| Simulación: cada hilo contra el Espino base más la especificación | 7 966 640 instrucciones, 93,15 % distintas, 1 030 081 de la extensión, cero diferencias | `make xd-verif` |
| Módulos solos | 49 152 comprobaciones del decodificador y 1 200 000 resultados iguales al modelo | `make xd-tb` |
| Configuración exacta de R1 (solo `emad` y `devk`) | 6 de 6 mutaciones que aplican; las 3 de `mulstep` probadas sin efecto sobre el netlist (decisión T74) | `make fondo-criterio5` |

Lo que encontró la prueba formal es un buen ejemplo para la defensa: la primera versión de la propiedad de `emad` fallaba y a la vez la mutación que vuelve lógico el desplazamiento pasaba. El error estaba en la propiedad: en Verilog `rs2 + (rs1s >>> 5)` en una sola expresión se evalúa sin signo, porque un operando sin signo vuelve sin signo toda la expresión. Sin el control negativo, "arreglar" el RTL para que pasara la propiedad habría metido el error (`docs/extension_isa.md`, sección 7.1).

## 7. Reglas del enunciado

El enunciado permite "una instrucción nueva en el espacio custom-0" como alternativa de hardware y exige que el hardware agregado acelere partes del algoritmo sin reemplazar al procesador. `emad` y `devk` son aritmética sin estado: no reciben un precio ni entregan una decisión, y no guardan nada entre ticks. El programa sigue leyendo `PRICE` con `lw`, comparando con `slt` y escribiendo `DECISION` con `sw`.

## 8. Preguntas típicas

1. **¿Por qué custom-0?** Es uno de los opcodes que RISC-V reserva para extensiones propias; ninguna estándar lo va a ocupar (`rtl/espino_core/espino_xd.v:44`).
2. **¿Por qué no agregaron el shifter?** El completo no cabe (1491 celdas). Un desplazamiento por una constante son cables, y las dos instrucciones cuestan 52 celdas.
3. **¿Por qué k fijo en 5?** Con un k son cables; con k variable hace falta un desplazador de unas 160 celdas que baja la frecuencia. El alfa del algoritmo es 1/32 en las cuatro reglas.
4. **¿Qué pasa si el programa usa k = 4?** El ensamblador lo rechaza (decisión T61). Si la palabra llega igual a la memoria, el core la trata como ilegal: lo prueba la propiedad X4 y la mutación `MUTA_XD_K` (`rtl/espino_core/espino_xd.v:56`).
5. **¿Cómo saben que no rompieron RV32E?** Formal B: con palabras de custom-0 reemplazadas por nop, el core es equivalente al de P1 en 1890 puntos. Y la campaña compara cada instrucción contra el Espino base.
6. **¿Contra qué se compara una instrucción que el Espino base no tiene?** Contra la fórmula, escrita tres veces por separado: modelo, testbench y propiedades formales (decisión T60).
7. **¿Cuánto acelera?** El estimador pasa de 14 instrucciones a 2; la respuesta de `max_media` en el barrel baja de 83 a 63 ciclos; un gestor del fondo pasa de 35 a 25 instrucciones.
8. **¿Cambia el resultado de la competencia?** No. Las decisiones son las mismas bit a bit. Lo que aporta es co-diseño medido y ciclos libres.
9. **¿Por qué no está `mulstep` en R1?** Porque `sw/fondo.s` no la usa, y una instrucción sin uso es riesgo sin función (T58).
10. **¿Por qué no hay Espino base con la extensión?** Porque llevarla al base toca `espino_core.v`, que es el RTL de R0 y ya pasó la puerta. Está predicha con Amdahl: 31 ciclos de respuesta, 1,32 veces R0 (decisión T101, `docs/codiseno.md`, sección 1).
