# Bitácora: registrador de la maestra (tarea A, 16 y 17/11)

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Encargo: un bitstream que, conectado a la maestra, envíe por la UART cada precio recibido, y una herramienta que lo guarde como CSV; verificar que no pierde precios a 0,1 ms; agregarlo al checklist del 26/11; no guardar ninguna serie dentro del diseño. Rama `registrador`.

- `rtl/registrador/registrador.v`: núcleo que escucha SCLK, MOSI, CS_n y MISO con el mismo muestreo del esclavo del SoC, cola de 4 registros, UART 8N1 a 1 Mbaud (25 ciclos por bit), registro de 5 bytes con secuencia, precio, MISO, marca de error y período. Tope `registrador_top` con MISO en 0 (mantener), cuenta en los 7 segmentos, SW3 borra.
- `tb/registrador/tb_registrador.sv`: maestra con los tiempos del testbench oficial y receptor UART; 6 casos (0,1 ms, 1 ms con SCLK de 100 kHz, 10 ms, una transacción de 7 bits, 60 us y el control de 30 us).
- `tools/registrador.py`: lee el puerto con `termios` a 1 Mbaud, arma los registros, cuenta los perdidos y escribe `_serie.csv` (formato de `tb/practica.csv`) y `_detalle.csv`; `--prueba` sin placa.
- **Error propio encontrado por un control negativo** (16/11 en la noche): la condición de cola llena comparaba la resta de punteros de 3 bits con un entero, en 32 bits; al dar la vuelta los punteros la cola sobrescribía. Solo ocurre con precios cada menos de 50 us. Corregido, con una comprobación nueva en el testbench (cada registro que llega tiene el precio de su transacción) y la versión antigua como control negativo `cola_llena_en_32_bits`.
- La primera corrida completa murió con las caídas de WSL; se repitió el 17/11 por la cola de trabajos pesados: `PASS: registrador listo` (`docs/mediciones/registrador.txt`). 478 celdas, 0 BRAM, 10 de 10 semillas (mínima 118,40 MHz), 7 de 7 controles negativos, 28 comprobaciones por los pines del bitstream ruteado.
- Checklist del 26/11: sección 4b. El bitstream va en `bitstreams/registrador.bin`.
- Falta: probarlo en la placa con el conversor USB a 1 Mbaud (solo se probó con un pseudoterminal).
