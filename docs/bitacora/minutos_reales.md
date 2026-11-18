# Bitácora: minutos reales, clase del 18/11 y registrador portable

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Rama `minutos-reales`, desde `main` (`4da78ca`). Pedido de Nicolás del 18/11 en la noche, en orden: bajar los minutos de Alpaca, armar la población real y comprobar la serie de práctica, repetir el paso 5 con minutos reales, registrar la clase, `iceprog -b`, registrador portable. Regla de los peldaños: no se cambia.

## Avance

1. **Descargador.** `tools/datos/alpaca.py` lee la clave de `~/.alpaca.env` si no está en el entorno (nunca la imprime ni la escribe), guarda también las barras crudas (con las de fuera de la sesión regular) y acepta `--salida` y `$P4_DATOS`. Datos en `$P4_DATOS/minuto` (en esta máquina, una carpeta fuera de todo repositorio). 5 empresas, 753 días cada una, de 293 596 a 293 670 minutos de sesión.
2. **Serie de práctica.** META desde el 2022-02-23 a las 15:20 hasta el 2022-05-09 a las 10:39: 20 000 de 20 000 iguales. La estimación anterior (15:10, con diarios) estaba 10 minutos corrida; las aperturas en los ticks 40 + 390 k ya lo indicaban.
3. **Captura de Tesla.** TSLA del 2022-01-10 10:20 al 2022-03-24 12:09: 20 000 de 20 000. `Cotas("espera", banda=60)` da 18 779 (la maestra mostró 18 779). AMD con el mismo inicio da 21 895 (la maestra mostró 21 895).
4. **Rival de Tesla.** `UnaVez(100, 220)` (comprar 63 repetido desde el primer 100, vender 63 repetido al ver 220 o más, no volver a entrar) da 21 467, la cifra de la maestra. Dos lecturas alternativas dan 21 500 y 17 550. En `ref/cotas/planb.py` y `evaluar.c` (tipo `unavez`), validado contra Python en 81 ventanas.
5. **Evaluador de todas las ventanas.** `ref/cotas/ventanas.c` incluye `evaluar.c` (con su `main` apagado por `EVALUAR_SIN_MAIN`), calcula mínimo y máximo de cada ventana con colas monótonas y corre las estrategias con OpenMP. `python3 ref/cotas/reales.py validar`: 55 ventanas de META, 4 estrategias, 0 diferencias contra Python. Unos 2,5 minutos por empresa con 97 estrategias y 24 núcleos.
6. **`iceprog -b`.** Documentos y checklists corregidos; tres `RESUMEN.txt` del banco de contingencia (`e16_s3`, `e16_s4`, `e7_s4`) tenían `iceprog` sin `-b` para `r2_multi.bin`. La placa del 16/11 no quedó mal grabada (`docs/mediciones/clase_18nov.md`, sección 3).
7. **Registrador.** `tools/registrador.py` con pyserial (Linux, Mac, Windows) o `termios` (Linux); `--convertir` y `--listar`. En WSL no hay pyserial: el camino de pyserial se probó con un módulo `serial` de imitación sobre un pseudoterminal (que pone el puerto en modo crudo, como pyserial) y con un `termios` sin `B921600` ni `B1000000`, como el de Mac: `--prueba` PASS por los dos caminos, y con `--puerto-con termios` en ese `termios` el programa pide pyserial en vez de caerse. `--convertir` con la captura de Tesla da un CSV idéntico a `ronda_10ms_clase.csv`.

8. **Paso 5.** `reales-paso5` en la cola: de 19:37:50 a 19:48:07 (código 0), 97 estrategias en las 1 368 253 ventanas. Después se agregó el cara a cara y se rehicieron las tablas desde la caché en 59 s (los resultados en C no cambian: la clave de la caché es la serie, las estrategias y el código en C). Resultado y conclusión en `docs/cotas.md`, secciones 7.2 y 7.3: la banda 60 sigue en la meseta; el mejor valor con minutos reales es 40 (+205 en la población, +258 y +314 en las validaciones, mismo p5 y peor). La regla no se cambió.

## Cerrado

Todo lo pedido. La decisión sobre la banda queda para Nicolás (`docs/estado.md`, tramo 17).
