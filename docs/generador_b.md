# Tarea B: último intento con el generador, contra un campo de reversiones

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Documento de estudio de la tarea B del 16 y 17/11 (rama `generador`, bitácora `docs/bitacora/generador_b.md`, decisión T131). Cifras en `docs/mediciones/generador_b/`.

**Resultado en una línea.** Ninguna candidata mejora a `max_media` en todo. Una, `max_media` con la salida media unidad sobre la media (`entra 3, sale +0,5`), pasa el criterio de corte con la semilla reservada **si los rivales hacen todos reversión**, y pierde si el campo es el mixto. Queda condicionada a lo que se sepa el 26/11.

## 1. El encargo

Objetivo distinto al del frente A: no el patrimonio medio, sino la probabilidad de ganarle cabeza a cabeza a la mejor regla nuestra (`max_media`, porque `zscore` no le ganó con el criterio fijado, T129) y los puntos esperados contra un campo de rivales que también operan reversión con parámetros variados. Mismo protocolo contra el sobreajuste. Una candidata solo se acepta si además gana en la serie que se registre el 26/11.

## 2. Cómo se hizo

- **Campo `variados`** (`ref/torneo_b/torneo_b.c`): los 10 rivales de cada ronda salen de las 25 reversiones del arnés, con la misma probabilidad (entrada de 2 a 6 unidades, salida 0 o 1, media exponencial o suma móvil). `max_media` y la regla base son dos de ellos.
- **Exploración, semilla 0** (`ref/torneo_b/busqueda.py`): 78 candidatas (memoria de la media 16, 32 o 64; entrada de 2 a 5 unidades; salida de -1 a +0,5; y `zscore`), a 2000 y 20 000 ticks, en `variados` y en el mixto.
- **Finalistas fijados antes de la semilla 5** (regla escrita en la bitácora): las tres mejores a 20 000 ticks en `variados` que no pierden a 2000.
- **Semilla 5, una vez** (`ref/torneo_b/reservada.sh`): criterio de corte en los dos campos, protocolo y duelo.

## 3. Resultados con la semilla reservada

| Candidata | `variados`: criterio | mixto: criterio | Protocolo (bloques; remuestreos) | Gana una ronda, plausibles, 2000 / 20 000 |
|-----------|----------------------|-----------------|----------------------------------|--------------------------------------------|
| Entra 2,5, sale +0,5 | No pasa: a 2000 el percentil 5 de H3b baja (-0,067 +- 0,019) | No pasa: H3a -0,018 | -202 +- 201; -25 +- 26 | 59 % / 75 % |
| Entra 2,5, sale 0 | No pasa: igual | No pasa | -7 +- 131; -16 +- 20 | 54 % / 66 % |
| **Entra 3, sale +0,5** | **Pasa**: H3a +0,010 y +0,019, H3b +0,013 y +0,021 (2000 y 20 000), percentil 5 igual | No pasa: H3a -0,011 y -0,019 | -173 +- 137; -22 +- 16 | 58 % / 67 % |

Lo que se lee:

1. **El campo decide.** Contra rivales que hacen todos reversión, conviene salir un poco más tarde que ellos: se queda con el tramo final de la recuperación, que es justo donde los demás ya vendieron. Contra un campo mixto, donde muchos rivales no compiten por el mismo movimiento, esa ventaja no existe y se paga el riesgo de quedarse adentro.
2. **En la práctica no gana.** En los 10 bloques pierde 173 +- 137 y en los remuestreos 22 +- 16. Gana en las familias plausibles (+28 a +160). Es el mismo patrón de `zscore` al revés: lo que el modelo premia, la práctica no lo confirma.
3. **Cabeza a cabeza** gana entre el 51 % (remuestreos) y el 58 % (plausibles) de las rondas de 2000 ticks, y el 67 % de las de 20 000 en las plausibles.

## 4. El generador

El intento de identificar mejor el generador no dio un modelo nuevo. Lo que sí quedó establecido, en `docs/zscore.md` (sección 4.5): la práctica tiene algo a escalas de cientos de ticks que el modelo calibrado no reproduce. No son las razones de varianza (las del modelo calzan hasta 1000 ticks); la candidata más probable es la forma en que se suceden los tramos tranquilos y ruidosos. Con una sola serie de práctica no se puede separar si eso es del generador o de esta trayectoria. **Se cierra el tema**: no hay tiempo antes del congelamiento para un modelo nuevo con validación.

## 5. Qué hacer con la candidata

Queda como decisión de Nicolás (`docs/pendientes_nicolas.md`). Cambiarla es una constante del programa (el umbral de salida, de 1 a 17 en unidades de `dev`): en R0 un `icebram` del programa; en R1 y R2, la tabla. Se acepta solo si se cumplen las dos condiciones del encargo:

- que el 26/11 se sepa que los otros grupos operan reversión (preguntar o mirar lo que hacen en la maestra), y
- que gane en la serie que se registre el 26/11, si el ayudante confirma que esa serie no es la de la competencia.

## 6. Preguntas que nos pueden hacer

**¿Por qué no salen apenas el precio cruza la media?** Es lo que hace `max_media`. Contra rivales que hacen lo mismo, salir media unidad más arriba da más puntos; contra un campo variado, no. No sabemos qué campo habrá, y por eso no lo cambiamos.

**¿No es sobreajuste elegir la salida mirando el campo?** El campo es un supuesto sobre los otros grupos, no sobre la serie. La candidata se eligió con la semilla 0 y se confirmó una sola vez con la 5.
