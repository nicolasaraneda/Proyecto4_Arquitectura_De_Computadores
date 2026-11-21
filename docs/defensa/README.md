# Kit de defensa

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Material para preparar la defensa presencial del 1/12. Según el enunciado (sección 5), las preguntas pueden ser sobre cualquier parte del informe, del algoritmo, del assembly y del RTL, y todos los integrantes deben poder responder.

Estos documentos **resumen y ordenan** los documentos de estudio de `docs/`, que siguen siendo la fuente completa: cada uno dice al comienzo de cuáles sale. Cada cifra trae su fuente en `docs/mediciones/` o en un documento del repositorio, y cada referencia `archivo:línea` está comprobada en la rama de entrega. Si una cifra de aquí no calza con su fuente, manda la fuente.

## Qué hay

| Archivo | Qué es |
|---------|--------|
| `resumen.md` | Una página: qué compite y por qué, la escalera R0, R1 y R2, qué está probado y qué falta, qué leer primero |
| `cifras.md` | Las cifras que hay que saber de memoria, cada una con su fuente |
| `plan_estudio.md` | Quién domina qué, qué deben poder explicar los tres, calendario de repasos hasta el 1/12 y el ensayo con preguntas al azar |
| `preguntas.md` | Banco de 183 preguntas con respuesta corta y `archivo:línea`, agrupadas por pieza, con las incómodas marcadas **[I]** |
| `espino_base.md` | El core del curso: las dos fases de cada instrucción, CPI de 2 más load y salto tomado, banco de registros síncrono, el SoC, cómo se mide, el tick de R0 |
| `segmentado.md` | El pipeline de 3 etapas: lectura en el flanco de bajada, adelantamiento, riesgos, contra lo que estimó la clase |
| `barrel.md` | Cuatro hilos por cuatro etapas: por qué no hay riesgos, dónde viven los contextos, qué cuesta en latencia |
| `extension.md` | `emad` y `devk` en custom-0: especificación, construcción, por qué k fijo en 5, verificación |
| `fondo.md` | `sw/fondo.s`: supervisor y gestores, protocolo de memoria compartida, degradación, qué aportan los gestores |
| `c1.md` | R3, `sw/c1.s`: C1 en los cuatro hilos. Qué hace cada hilo, la máquina de modos, de dónde salen las tablas y por qué no son precios guardados, degradación, y lo medido en el examen y en las puertas |
| `tabla_vigilante.md` | Tabla en BRAM, `icebram` con moldes, vigilante con `SB_WARMBOOT`, relevo e imagen múltiple |
| `algoritmo.md` | De la serie al modelo, reversión a la media, `max_media`, protocolo de evaluación, por qué no otras ideas, suerte y sobreajuste |
| `verificacion.md` | El flujo completo: referencia en Python, gemelo digital, equivalencia, formal, mutaciones, puertas, matriz de estrés, simulación del bitstream, placa y maestra |
| `diagramas.md` | Seis dibujos para la pizarra: el SoC, las fases del Espino base, el segmentado, el barrel, un tick por los cuatro hilos del fondo y el relevo de R2 |
| `guiones.md` | Guion de 1 minuto y de 5 minutos (un bloque por integrante, en el orden de la pauta) |
| `pruebas_practica.md` | Tres pruebas de 15 preguntas del banco con su pauta (`python3 tools/defensa/pruebas.py`) |
| `guia_nicolas.md`, `guia_vicente.md`, `guia_santiago.md` | Una guía por integrante según el plan de estudio: qué leer, qué dibujar, cifras, preguntas y fechas |

## En qué orden leerlo

1. `resumen.md` y `cifras.md`.
2. `plan_estudio.md`, para saber qué pieza es de cada uno.
3. Los documentos de estudio en este orden, que va de lo básico a lo que compite: `espino_base.md`, `algoritmo.md`, `segmentado.md`, `barrel.md`, `extension.md`, `fondo.md`, `tabla_vigilante.md`, `verificacion.md`.
4. `preguntas.md`: primero las **[B]** y las **[I]** de todo el banco, después las **[A]** de la propia pieza.
5. La guía propia (`guia_*.md`), `diagramas.md` y `guiones.md`, y las pruebas de práctica en los repasos.

Fuera de esta carpeta, para el día: `docs/arbol_decision.md` (qué se graba el 1/12), `docs/checklist_26nov.md` y `docs/checklist_1dic.md`.
