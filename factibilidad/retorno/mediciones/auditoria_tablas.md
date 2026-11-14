# Tablas de la auditoría del arnés de retorno

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Generado por `auditoria/informe.py` con el evaluador independiente (`auditoria/indep.c`). Los puntos esperados son exactos (no hay sorteo de campos) y su error es el error estándar entre series. `kalman` y `guardia` son externos: su patrimonio por serie viene del arnés.

## 1. Campos de rivales más fuertes, rondas de 2000 ticks

Conjunto evidencia (10 000 series), G = 10. Primera columna: puntos esperados de la regla base. Las demás: diferencia de puntos esperados contra la base, H3a y H3b, con su error.

Semilla 2:

| Campo (G = 10) | `base`: H3a, H3b | `max_media` | `kalman` | `activo` | `guardia` | `prudente` |
|---|---|---|---|---|---|---|
| ingenuo | 1,671, 1,542 | +0,019 ± 0,002, +0,028 ± 0,003 | +0,020 ± 0,002, +0,033 ± 0,003 | +0,007 ± 0,003, +0,019 ± 0,004 | -0,014 ± 0,002, -0,019 ± 0,004 | -0,050 ± 0,002, -0,069 ± 0,004 |
| mixto | 1,453, 1,425 | +0,042 ± 0,003, +0,039 ± 0,004 | +0,034 ± 0,003, +0,042 ± 0,004 | +0,006 ± 0,005, +0,035 ± 0,005 | -0,023 ± 0,004, -0,026 ± 0,005 | -0,107 ± 0,004, -0,071 ± 0,004 |
| fuerte (60 % reversión ajustada) | 1,349, 1,158 | +0,066 ± 0,005, +0,084 ± 0,006 | +0,053 ± 0,005, +0,085 ± 0,006 | +0,023 ± 0,006, +0,098 ± 0,008 | -0,023 ± 0,006, -0,040 ± 0,007 | -0,141 ± 0,005, -0,124 ± 0,006 |
| racional (nadie entrega algo que pierde en la práctica) | 1,100, 1,157 | +0,100 ± 0,006, +0,082 ± 0,006 | +0,100 ± 0,006, +0,092 ± 0,006 | +0,099 ± 0,009, +0,074 ± 0,008 | -0,006 ± 0,007, -0,029 ± 0,007 | -0,188 ± 0,007, -0,205 ± 0,007 |
| mixto con 2 rivales fijos: base y max_media | 1,416, 1,327 | +0,057 ± 0,004, +0,057 ± 0,005 | +0,041 ± 0,004, +0,060 ± 0,005 | +0,001 ± 0,006, +0,057 ± 0,006 | -0,025 ± 0,005, -0,039 ± 0,006 | -0,134 ± 0,005, -0,096 ± 0,005 |
| mixto con 3 fijos: base, max_media y suma móvil | 1,371, 1,274 | +0,057 ± 0,004, +0,064 ± 0,005 | +0,046 ± 0,004, +0,066 ± 0,005 | +0,018 ± 0,006, +0,069 ± 0,007 | -0,022 ± 0,005, -0,035 ± 0,006 | -0,127 ± 0,005, -0,101 ± 0,005 |
| todos con reversión ajustada | 0,872, 0,922 | +0,200 ± 0,013, +0,123 ± 0,009 | +0,186 ± 0,012, +0,123 ± 0,009 | +0,192 ± 0,013, +0,150 ± 0,010 | +0,030 ± 0,012, -0,057 ± 0,009 | -0,144 ± 0,009, -0,171 ± 0,008 |

Semilla 0:

| Campo (G = 10) | `base`: H3a, H3b | `max_media` | `kalman` | `activo` | `guardia` | `prudente` |
|---|---|---|---|---|---|---|
| ingenuo | 1,677, 1,554 | +0,018 ± 0,002, +0,024 ± 0,003 | +0,020 ± 0,002, +0,029 ± 0,003 | +0,005 ± 0,003, +0,013 ± 0,004 | -0,014 ± 0,002, -0,023 ± 0,004 | -0,055 ± 0,002, -0,075 ± 0,004 |
| mixto | 1,464, 1,438 | +0,039 ± 0,003, +0,035 ± 0,004 | +0,035 ± 0,003, +0,041 ± 0,004 | +0,001 ± 0,005, +0,028 ± 0,005 | -0,026 ± 0,004, -0,031 ± 0,005 | -0,114 ± 0,004, -0,078 ± 0,004 |
| fuerte (60 % reversión ajustada) | 1,362, 1,167 | +0,061 ± 0,005, +0,077 ± 0,006 | +0,053 ± 0,005, +0,089 ± 0,006 | +0,017 ± 0,006, +0,088 ± 0,008 | -0,028 ± 0,006, -0,048 ± 0,007 | -0,150 ± 0,005, -0,131 ± 0,006 |
| racional (nadie entrega algo que pierde en la práctica) | 1,115, 1,170 | +0,094 ± 0,006, +0,076 ± 0,006 | +0,098 ± 0,006, +0,090 ± 0,006 | +0,088 ± 0,009, +0,062 ± 0,008 | -0,013 ± 0,007, -0,037 ± 0,007 | -0,202 ± 0,007, -0,216 ± 0,007 |
| mixto con 2 rivales fijos: base y max_media | 1,427, 1,337 | +0,054 ± 0,004, +0,055 ± 0,005 | +0,042 ± 0,004, +0,063 ± 0,005 | -0,005 ± 0,006, +0,049 ± 0,006 | -0,028 ± 0,005, -0,043 ± 0,006 | -0,142 ± 0,004, -0,103 ± 0,005 |
| mixto con 3 fijos: base, max_media y suma móvil | 1,382, 1,285 | +0,054 ± 0,004, +0,059 ± 0,005 | +0,047 ± 0,004, +0,068 ± 0,005 | +0,012 ± 0,006, +0,061 ± 0,007 | -0,025 ± 0,005, -0,042 ± 0,006 | -0,135 ± 0,005, -0,108 ± 0,005 |
| todos con reversión ajustada | 0,880, 0,928 | +0,182 ± 0,013, +0,114 ± 0,009 | +0,190 ± 0,012, +0,130 ± 0,009 | +0,181 ± 0,013, +0,138 ± 0,010 | +0,015 ± 0,012, -0,067 ± 0,010 | -0,149 ± 0,009, -0,178 ± 0,008 |

Contra `max_media`, semilla 2:

| Campo (G = 10) | `kalman` contra `max_media`: H3a, H3b | `activo` contra `max_media`: H3a, H3b | `guardia` contra `max_media`: H3a, H3b |
|---|---|---|---|
| ingenuo | +0,000 ± 0,001, +0,004 ± 0,002 | -0,012 ± 0,002, -0,009 ± 0,004 | -0,034 ± 0,002, -0,047 ± 0,002 |
| mixto | -0,008 ± 0,002, +0,003 ± 0,002 | -0,036 ± 0,004, -0,004 ± 0,004 | -0,065 ± 0,003, -0,064 ± 0,003 |
| fuerte (60 % reversión ajustada) | -0,013 ± 0,002, +0,002 ± 0,004 | -0,043 ± 0,005, +0,014 ± 0,006 | -0,088 ± 0,003, -0,124 ± 0,004 |
| racional (nadie entrega algo que pierde en la práctica) | +0,001 ± 0,003, +0,010 ± 0,003 | -0,001 ± 0,007, -0,007 ± 0,007 | -0,106 ± 0,004, -0,111 ± 0,004 |
| mixto con 2 rivales fijos: base y max_media | -0,016 ± 0,002, +0,003 ± 0,003 | -0,056 ± 0,004, -0,000 ± 0,005 | -0,083 ± 0,003, -0,096 ± 0,003 |
| mixto con 3 fijos: base, max_media y suma móvil | -0,011 ± 0,002, +0,002 ± 0,003 | -0,039 ± 0,005, +0,006 ± 0,005 | -0,079 ± 0,003, -0,099 ± 0,004 |
| todos con reversión ajustada | -0,014 ± 0,007, +0,000 ± 0,006 | -0,008 ± 0,010, +0,027 ± 0,009 | -0,169 ± 0,007, -0,179 ± 0,006 |

Contra `max_media`, semilla 0:

| Campo (G = 10) | `kalman` contra `max_media`: H3a, H3b | `activo` contra `max_media`: H3a, H3b | `guardia` contra `max_media`: H3a, H3b |
|---|---|---|---|
| ingenuo | +0,002 ± 0,001, +0,005 ± 0,002 | -0,014 ± 0,002, -0,011 ± 0,004 | -0,032 ± 0,002, -0,047 ± 0,002 |
| mixto | -0,004 ± 0,002, +0,006 ± 0,002 | -0,038 ± 0,004, -0,007 ± 0,004 | -0,065 ± 0,003, -0,067 ± 0,003 |
| fuerte (60 % reversión ajustada) | -0,008 ± 0,002, +0,011 ± 0,004 | -0,044 ± 0,005, +0,011 ± 0,006 | -0,088 ± 0,003, -0,126 ± 0,004 |
| racional (nadie entrega algo que pierde en la práctica) | +0,004 ± 0,003, +0,014 ± 0,003 | -0,006 ± 0,007, -0,014 ± 0,007 | -0,106 ± 0,004, -0,114 ± 0,004 |
| mixto con 2 rivales fijos: base y max_media | -0,012 ± 0,002, +0,008 ± 0,003 | -0,059 ± 0,005, -0,006 ± 0,005 | -0,082 ± 0,003, -0,098 ± 0,004 |
| mixto con 3 fijos: base, max_media y suma móvil | -0,007 ± 0,002, +0,009 ± 0,003 | -0,041 ± 0,005, +0,002 ± 0,005 | -0,079 ± 0,003, -0,101 ± 0,004 |
| todos con reversión ajustada | +0,008 ± 0,007, +0,016 ± 0,006 | -0,001 ± 0,010, +0,023 ± 0,009 | -0,167 ± 0,007, -0,181 ± 0,006 |

## 2. Campos más fuertes, rondas de 20 000 ticks (series interiores)

Semilla 2:

| Campo (G = 10) | `base`: H3a, H3b | `max_media` | `kalman` | `activo` | `guardia` | `prudente` |
|---|---|---|---|---|---|---|
| ingenuo | 1,815, 1,844 | +0,071 ± 0,002, +0,047 ± 0,002 | +0,071 ± 0,002, +0,051 ± 0,002 | +0,074 ± 0,004, +0,058 ± 0,003 | -0,022 ± 0,003, -0,009 ± 0,003 | -0,193 ± 0,003, -0,111 ± 0,003 |
| mixto | 1,737, 1,746 | +0,122 ± 0,004, +0,075 ± 0,003 | +0,106 ± 0,004, +0,085 ± 0,003 | +0,077 ± 0,005, +0,092 ± 0,004 | -0,050 ± 0,005, -0,016 ± 0,004 | -0,302 ± 0,005, -0,121 ± 0,004 |
| fuerte (60 % reversión ajustada) | 1,549, 1,256 | +0,198 ± 0,006, +0,223 ± 0,008 | +0,179 ± 0,006, +0,257 ± 0,008 | +0,153 ± 0,008, +0,275 ± 0,010 | -0,045 ± 0,007, -0,049 ± 0,009 | -0,366 ± 0,006, -0,286 ± 0,007 |
| racional (nadie entrega algo que pierde en la práctica) | 1,286, 1,322 | +0,229 ± 0,007, +0,205 ± 0,007 | +0,235 ± 0,007, +0,224 ± 0,007 | +0,271 ± 0,011, +0,247 ± 0,010 | -0,038 ± 0,009, -0,045 ± 0,009 | -0,437 ± 0,008, -0,423 ± 0,008 |
| mixto con 2 rivales fijos: base y max_media | 1,638, 1,557 | +0,198 ± 0,006, +0,141 ± 0,005 | +0,167 ± 0,006, +0,164 ± 0,005 | +0,109 ± 0,007, +0,164 ± 0,006 | -0,048 ± 0,007, -0,034 ± 0,006 | -0,364 ± 0,006, -0,192 ± 0,005 |
| mixto con 3 fijos: base, max_media y suma móvil | 1,554, 1,465 | +0,190 ± 0,006, +0,160 ± 0,006 | +0,173 ± 0,005, +0,184 ± 0,006 | +0,151 ± 0,008, +0,197 ± 0,007 | -0,041 ± 0,007, -0,035 ± 0,007 | -0,345 ± 0,006, -0,215 ± 0,005 |
| todos con reversión ajustada | 0,684, 0,808 | +0,561 ± 0,019, +0,357 ± 0,012 | +0,556 ± 0,017, +0,414 ± 0,013 | +0,568 ± 0,020, +0,441 ± 0,016 | +0,047 ± 0,018, -0,080 ± 0,014 | -0,340 ± 0,013, -0,434 ± 0,011 |

Semilla 0:

| Campo (G = 10) | `base`: H3a, H3b | `max_media` | `kalman` | `activo` | `guardia` | `prudente` |
|---|---|---|---|---|---|---|
| ingenuo | 1,810, 1,841 | +0,071 ± 0,002, +0,047 ± 0,002 | +0,072 ± 0,002, +0,052 ± 0,002 | +0,074 ± 0,004, +0,059 ± 0,003 | -0,022 ± 0,003, -0,010 ± 0,003 | -0,191 ± 0,004, -0,106 ± 0,003 |
| mixto | 1,732, 1,742 | +0,124 ± 0,004, +0,079 ± 0,003 | +0,110 ± 0,004, +0,091 ± 0,003 | +0,078 ± 0,005, +0,096 ± 0,004 | -0,046 ± 0,005, -0,015 ± 0,004 | -0,295 ± 0,005, -0,111 ± 0,003 |
| fuerte (60 % reversión ajustada) | 1,536, 1,242 | +0,205 ± 0,006, +0,239 ± 0,008 | +0,188 ± 0,006, +0,275 ± 0,008 | +0,159 ± 0,008, +0,290 ± 0,010 | -0,034 ± 0,007, -0,032 ± 0,009 | -0,349 ± 0,006, -0,253 ± 0,007 |
| racional (nadie entrega algo que pierde en la práctica) | 1,270, 1,309 | +0,231 ± 0,007, +0,204 ± 0,006 | +0,243 ± 0,007, +0,230 ± 0,007 | +0,273 ± 0,011, +0,253 ± 0,010 | -0,026 ± 0,009, -0,035 ± 0,008 | -0,415 ± 0,008, -0,400 ± 0,008 |
| mixto con 2 rivales fijos: base y max_media | 1,631, 1,549 | +0,207 ± 0,006, +0,152 ± 0,005 | +0,177 ± 0,005, +0,175 ± 0,005 | +0,113 ± 0,007, +0,173 ± 0,006 | -0,038 ± 0,007, -0,027 ± 0,006 | -0,350 ± 0,006, -0,173 ± 0,005 |
| mixto con 3 fijos: base, max_media y suma móvil | 1,540, 1,455 | +0,198 ± 0,006, +0,171 ± 0,005 | +0,183 ± 0,005, +0,197 ± 0,006 | +0,157 ± 0,008, +0,207 ± 0,007 | -0,029 ± 0,007, -0,025 ± 0,006 | -0,328 ± 0,006, -0,192 ± 0,005 |
| todos con reversión ajustada | 0,657, 0,786 | +0,593 ± 0,018, +0,384 ± 0,012 | +0,586 ± 0,016, +0,444 ± 0,013 | +0,597 ± 0,020, +0,465 ± 0,016 | +0,088 ± 0,017, -0,049 ± 0,014 | -0,280 ± 0,013, -0,379 ± 0,011 |

## 3. Criterio de corte recalculado

En cuántas combinaciones de campo y G pasa cada candidata, con las cifras de la auditoría: la media de los puntos mejora en más de dos errores y el percentil 5 de la competencia de tres rondas no baja en más de dos errores, en H3a y en H3b. El error del percentil 5 es el de la auditoría (10 lotes de series), más chico que el del estudio.

| Candidata | Semilla 0: 2000, 20 000 interiores (de 9) | Semilla 2: 2000, 20 000 interiores (de 9) | Campos más fuertes, 2000 ticks, semillas 0 y 2 (de 4) |
|---|---|---|---|
| `max_media` contra `base` | 9, 9 | 9, 9 | 4 y 4 |
| `kalman` contra `base` | 9, 9 | 9, 9 | 4 y 4 |
| `activo` contra `base` | 0, 9 | 1, 9 | 0 y 0 |
| `guardia` contra `base` | 0, 0 | 0, 0 | 0 y 0 |
| `prudente` contra `base` | 0, 0 | 0, 0 | 0 y 0 |
| `kalman` contra `max_media` | 3, 0 | 0, 0 | 0 y 0 |
| `activo` contra `max_media` | 0, 1 | 0, 0 | 0 y 0 |
| `guardia` contra `max_media` | 0, 0 | 0, 0 | 0 y 0 |

## 4. Rondas de 20 000 ticks: tres vistas

Diferencia contra la regla base en el conjunto evidencia, campo mixto, G = 10. Interiores: solo las series que nunca salen de 21 a 249 (selecciona por la trayectoria completa). Todas: sin filtrar (incluye las series pegadas al precio 1). Parada: todas las series, cada una hasta el primer precio fuera de 21 a 249 (mínimo 200 ticks); no mira el futuro y deja rondas de largo medio 15276 ticks.

| Candidato contra `base` | Interiores (la del estudio): H1, H3a, H3b | Todas: H1, H3a, H3b | Parada (sin selección): H1, H3a, H3b |
|---|---|---|---|
| `max_media`, semilla 0 | +3278 ± 124, +0,124 ± 0,004, +0,079 ± 0,003 | +9388 ± 273, +0,149 ± 0,003, +0,084 ± 0,002 | +1899 ± 74, +0,075 ± 0,003, +0,050 ± 0,003 |
| `activo`, semilla 0 | +5407 ± 236, +0,078 ± 0,005, +0,096 ± 0,004 | +26444 ± 741, +0,145 ± 0,004, +0,124 ± 0,003 | +2519 ± 136, -0,018 ± 0,005, +0,024 ± 0,004 |
| `prudente`, semilla 0 | -5393 ± 154, -0,295 ± 0,005, -0,111 ± 0,003 | -14738 ± 372, -0,332 ± 0,004, -0,109 ± 0,002 | -3346 ± 95, -0,213 ± 0,004, -0,078 ± 0,003 |
| `max_media`, semilla 2 | +3001 ± 118, +0,122 ± 0,004, +0,075 ± 0,003 | +9162 ± 265, +0,146 ± 0,003, +0,082 ± 0,002 | +1757 ± 71, +0,074 ± 0,003, +0,050 ± 0,003 |
| `activo`, semilla 2 | +5275 ± 246, +0,077 ± 0,005, +0,092 ± 0,004 | +25478 ± 729, +0,138 ± 0,004, +0,120 ± 0,003 | +2621 ± 141, -0,005 ± 0,005, +0,033 ± 0,004 |
| `prudente`, semilla 2 | -5520 ± 157, -0,302 ± 0,005, -0,121 ± 0,004 | -14531 ± 386, -0,330 ± 0,004, -0,112 ± 0,003 | -3404 ± 96, -0,212 ± 0,004, -0,083 ± 0,003 |

## 5. Cuánto selecciona el filtro de interiores

Los primeros 2000 ticks de las series de 20 000 ticks de la evidencia, separadas según si la serie completa queda dentro de 21 a 249. Si el filtro no seleccionara, las dos filas de cada semilla serían iguales.

| Semilla | Series | `base` en los primeros 2000 ticks: media ± ee, p5 | Comprar y mantener: media ± ee | `max_media` menos `base` |
|---|---|---|---|---|
| 0 | interiores (las que deja el filtro), 4021 | 10735 ± 21, 9127 | 10059 ± 32 | +102 ± 11 |
| 0 | excluidas por el filtro, 3979 | 11031 ± 50, 8541 | 9529 ± 44 | +103 ± 18 |
| 2 | interiores (las que deja el filtro), 4004 | 10758 ± 24, 9188 | 10049 ± 31 | +129 ± 11 |
| 2 | excluidas por el filtro, 3996 | 10915 ± 36, 8511 | 9544 ± 43 | +87 ± 20 |

## 6. Límites 1 y 255

| Conjunto, semilla 0 | Tocan 1 | Mínimo de 20 o menos | Tocan 255 | Ticks con precio de 20 o menos | Ticks con precio de 5 o menos | Series con más del 10 % de la ronda en la zona de los límites | Racha más larga pegada a un límite (media) |
|---|---|---|---|---|---|---|---|
| remuestreo, 2000 ticks | 0,1 % | 0,7 % | 0,0 % | 0,07 % | 0,01 % | 0,3 % | 0 ticks |
| plausibles, 2000 ticks | 0,5 % | 1,3 % | 0,6 % | 0,17 % | 0,03 % | 0,7 % | 0 ticks |
| estres, 2000 ticks | 7,6 % | 17,7 % | 3,6 % | 5,46 % | 0,99 % | 12,5 % | 9 ticks |
| evidencia, 2000 ticks | 0,3 % | 1,1 % | 0,4 % | 0,14 % | 0,02 % | 0,6 % | 0 ticks |
| remuestreo, 20000 ticks | 31,4 % | 41,1 % | 8,8 % | 7,19 % | 1,61 % | 26,1 % | 64 ticks |
| plausibles, 20000 ticks | 20,3 % | 26,8 % | 20,7 % | 3,99 % | 0,91 % | 17,5 % | 60 ticks |
| estres, 20000 ticks | 47,7 % | 56,5 % | 37,4 % | 11,13 % | 4,41 % | 39,0 % | 163 ticks |
| evidencia, 20000 ticks | 25,9 % | 34,0 % | 14,7 % | 5,59 % | 1,26 % | 21,8 % | 62 ticks |

## 7. Error del percentil 5 de la competencia de tres rondas

Diferencia del percentil 5 contra la regla base, 2000 ticks, campo mixto, G = 10. El estudio estima el error por remuestreo dentro de cada reparto en tríos y avisa que es conservador. La auditoría lo estima con 10 lotes disjuntos de series. El error del estudio es en promedio 2,8 veces el de la auditoría.

| Candidato contra `base` | H3a, estudio: semilla 0, semilla 2 | H3a, auditoría: semilla 0, semilla 2 | H3b, estudio: semilla 0, semilla 2 | H3b, auditoría: semilla 0, semilla 2 |
|---|---|---|---|---|
| `max_media` | +0,047 ± 0,015, +0,042 ± 0,016 | +0,037 ± 0,006, +0,049 ± 0,008 | +0,039 ± 0,022, +0,017 ± 0,021 | +0,029 ± 0,006, +0,033 ± 0,008 |
| `kalman` | +0,052 ± 0,015, +0,042 ± 0,016 | +0,043 ± 0,007, +0,052 ± 0,008 | +0,028 ± 0,026, +0,000 ± 0,025 | +0,013 ± 0,005, +0,017 ± 0,009 |
| `activo` | +0,005 ± 0,019, -0,002 ± 0,018 | -0,002 ± 0,009, +0,015 ± 0,008 | -0,022 ± 0,028, -0,033 ± 0,028 | -0,017 ± 0,008, +0,000 ± 0,008 |
| `guardia` | -0,025 ± 0,016, -0,031 ± 0,017 | -0,028 ± 0,006, -0,015 ± 0,009 | -0,072 ± 0,026, -0,067 ± 0,018 | -0,075 ± 0,005, -0,050 ± 0,012 |
| `prudente` | -0,108 ± 0,015, -0,108 ± 0,015 | -0,119 ± 0,010, -0,092 ± 0,007 | -0,106 ± 0,026, -0,100 ± 0,023 | -0,117 ± 0,008, -0,096 ± 0,007 |

