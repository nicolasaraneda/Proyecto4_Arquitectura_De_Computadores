# Estudio de cierre: tablas de la lista `exploracion`, semilla 0 (exploración)

Generado por `tablas.py` a partir de las corridas de `correr.py`. Diferencias pareadas contra `max_media`, G = 10 rivales. Puntos de 0 a 2. "p5 de 3 rondas" es el percentil 5 del promedio de puntos de una competencia de tres rondas.

Vistas: 2000 ticks con todas las series; 20 000 ticks con las series interiores (precio siempre entre 21 y 249), que es la del criterio de corte; y 20 000 ticks con parada (todas las series, cada una hasta el primer precio fuera de 21 a 249), que no selecciona.

Series: 2000 ticks: 10000 de evidencia y 7000 de estrés; 20 000 ticks, interiores: 4021 de evidencia y 602 de estrés; 20 000 ticks, parada: 8000 de evidencia y 2800 de estrés.

| Nombre | Qué es |
|---|---|
| `base` | regla base (E = 128) |
| `kalman` | Kalman de dos estados |
| `ejec_a` | `ejec:m=8`, ejecución A |
| `ejec_b` | `ejec:m=8,m2=24,e2=32`, ejecución B |
| `espera` | regla fija `espera` (r4c) |
| `aprendiz` | tabla que aprende (r4c) |
| `aprendiz_patron` | `max_media` con predictor de patrones (r4c) |
| `espera_e` | `espera` con la ejecución A |
| `fondo_rec` | fondo recomendado (r4b) |
| `fondo_min` | fondo mínimo, voto (r4b) |
| `fondo_ancla` | fondo con ancla (r4b) |
| `rec_e` | `fondo_rec` con la ejecución A |
| `min_e` | `fondo_min` con la ejecución A |
| `completo` | FONDO COMPLETO |
| `completo_s` | completo sin la ejecución A |
| `completo_esp` | completo con `espera` de cuarto gestor |
| `completo_ap` | completo con pesos aprendidos |
| `completo_ancla` | completo con ancla en comprar y mantener |
| `completo_min` | fondo mínimo con `aprendiz` y ejecución A |

## 1. Criterio de corte contra `max_media`, por campo de rivales


Conjunto evidencia. Cada celda: diferencia de puntos esperados ± error. "dp5" es la diferencia del percentil 5 de tres rondas, H3a y H3b. Veredicto: 2000 / 20 000 / global con la regla del arnés, veredicto literal (solo signos) y si la fila de parada tiene el mismo signo que la de interiores. **Final** es PASA solo si el veredicto global pasa y la parada confirma.

### Campo ingenuo

Nivel de `max_media`: 2000 ticks: 1,695 (H3a) y 1,579 (H3b), p5 de 3 rondas 1,165 y 1,067; 20 000 ticks, interiores: 1,880 (H3a) y 1,887 (H3b), p5 de 3 rondas 1,571 y 1,611; 20 000 ticks, parada: 1,775 (H3a) y 1,785 (H3b), p5 de 3 rondas 1,357 y 1,400.

| Candidata | 2000: dH3a | 2000: dH3b | 2000: dp5 | 20 000 int.: dH3a | 20 000 int.: dH3b | 20 000 int.: dp5 | parada: dH3a | parada: dH3b | 2000 / 20 000 / global | Literal | Parada | Final |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `base` | -0,017 ± 0,002 | -0,025 ± 0,003 | -0,030 ± 0,015, -0,039 ± 0,024 | -0,070 ± 0,002 | -0,046 ± 0,002 | -0,153 ± 0,016, -0,078 ± 0,025 | -0,040 ± 0,002 | -0,029 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `kalman` | +0,002 ± 0,001 | +0,004 ± 0,002 | +0,002 ± 0,011, +0,000 ± 0,015 | +0,001 ± 0,001 | +0,006 ± 0,001 | +0,004 ± 0,011, +0,000 ± 0,028 | +0,001 ± 0,001 | +0,005 ± 0,001 | PASA / NO_PASA / NO_PASA | pasa | confirma | NO_PASA |
| `ejec_a` | +0,004 ± 0,000 | +0,010 ± 0,000 | +0,007 ± 0,004, +0,000 ± 0,014 | +0,005 ± 0,000 | +0,011 ± 0,000 | +0,012 ± 0,005, +0,044 ± 0,027 | +0,005 ± 0,000 | +0,010 ± 0,000 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `ejec_b` | +0,008 ± 0,000 | +0,015 ± 0,001 | +0,013 ± 0,006, +0,000 ± 0,023 | +0,008 ± 0,000 | +0,013 ± 0,001 | +0,018 ± 0,006, +0,056 ± 0,028 | +0,009 ± 0,000 | +0,013 ± 0,000 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `espera` | +0,008 ± 0,001 | +0,015 ± 0,002 | +0,012 ± 0,012, +0,000 ± 0,018 | -0,005 ± 0,001 | +0,005 ± 0,002 | -0,015 ± 0,012, -0,011 ± 0,028 | +0,009 ± 0,001 | +0,016 ± 0,001 | PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `aprendiz` | +0,000 ± 0,000 | +0,000 ± 0,000 | -0,001 ± 0,003, +0,000 ± 0,003 | -0,009 ± 0,001 | -0,004 ± 0,001 | -0,016 ± 0,011, -0,011 ± 0,025 | -0,003 ± 0,001 | -0,000 ± 0,001 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `aprendiz_patron` | -0,000 ± 0,000 | -0,000 ± 0,001 | -0,001 ± 0,005, +0,000 ± 0,011 | -0,002 ± 0,000 | -0,000 ± 0,001 | -0,005 ± 0,008, +0,000 ± 0,022 | +0,000 ± 0,000 | +0,002 ± 0,001 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `espera_e` | +0,011 ± 0,001 | +0,021 ± 0,002 | +0,019 ± 0,012, +0,000 ± 0,023 | -0,001 ± 0,001 | +0,009 ± 0,001 | -0,005 ± 0,012, +0,011 ± 0,029 | +0,014 ± 0,001 | +0,020 ± 0,001 | PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `fondo_rec` | +0,001 ± 0,001 | +0,003 ± 0,001 | +0,003 ± 0,008, +0,000 ± 0,013 | +0,009 ± 0,001 | +0,007 ± 0,001 | +0,026 ± 0,010, +0,022 ± 0,028 | +0,002 ± 0,001 | +0,002 ± 0,001 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `fondo_min` | +0,000 ± 0,000 | +0,000 ± 0,000 | +0,000 ± 0,003, +0,000 ± 0,004 | +0,000 ± 0,002 | +0,001 ± 0,001 | +0,001 ± 0,013, -0,011 ± 0,025 | -0,004 ± 0,001 | -0,001 ± 0,001 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `fondo_ancla` | -0,009 ± 0,001 | -0,007 ± 0,002 | +0,031 ± 0,009, +0,056 ± 0,023 | -0,063 ± 0,001 | -0,029 ± 0,001 | -0,124 ± 0,012, -0,011 ± 0,027 | -0,090 ± 0,001 | -0,052 ± 0,001 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `rec_e` | +0,004 ± 0,001 | +0,007 ± 0,001 | +0,009 ± 0,008, +0,000 ± 0,014 | +0,013 ± 0,001 | +0,011 ± 0,001 | +0,032 ± 0,010, +0,056 ± 0,028 | +0,006 ± 0,001 | +0,006 ± 0,001 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `min_e` | +0,005 ± 0,000 | +0,010 ± 0,000 | +0,007 ± 0,005, +0,000 ± 0,015 | +0,006 ± 0,001 | +0,008 ± 0,001 | +0,013 ± 0,013, +0,022 ± 0,031 | +0,002 ± 0,001 | +0,007 ± 0,001 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `completo` | +0,004 ± 0,000 | +0,008 ± 0,001 | +0,008 ± 0,008, +0,000 ± 0,013 | +0,010 ± 0,001 | +0,009 ± 0,001 | +0,027 ± 0,010, +0,022 ± 0,028 | +0,006 ± 0,001 | +0,006 ± 0,001 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `completo_s` | +0,001 ± 0,000 | +0,003 ± 0,001 | +0,003 ± 0,008, +0,000 ± 0,012 | +0,007 ± 0,001 | +0,005 ± 0,001 | +0,020 ± 0,010, +0,011 ± 0,027 | +0,003 ± 0,001 | +0,002 ± 0,001 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `completo_esp` | +0,002 ± 0,001 | +0,003 ± 0,001 | +0,005 ± 0,008, +0,000 ± 0,016 | +0,008 ± 0,001 | +0,006 ± 0,001 | +0,024 ± 0,010, +0,011 ± 0,027 | +0,005 ± 0,001 | +0,004 ± 0,001 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `completo_ap` | +0,003 ± 0,000 | +0,006 ± 0,001 | +0,006 ± 0,008, +0,000 ± 0,013 | +0,009 ± 0,001 | +0,006 ± 0,001 | +0,027 ± 0,010, +0,011 ± 0,029 | +0,004 ± 0,001 | +0,002 ± 0,001 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `completo_ancla` | -0,009 ± 0,001 | -0,008 ± 0,002 | +0,031 ± 0,009, +0,056 ± 0,025 | -0,067 ± 0,001 | -0,032 ± 0,001 | -0,130 ± 0,013, -0,011 ± 0,029 | -0,092 ± 0,001 | -0,054 ± 0,001 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_min` | +0,004 ± 0,000 | +0,010 ± 0,000 | +0,006 ± 0,005, +0,000 ± 0,014 | +0,007 ± 0,001 | +0,008 ± 0,001 | +0,018 ± 0,011, +0,033 ± 0,029 | +0,006 ± 0,001 | +0,008 ± 0,001 | PASA / PASA / PASA | pasa | confirma | **PASA** |

### Campo mixto

Nivel de `max_media`: 2000 ticks: 1,503 (H3a) y 1,473 (H3b), p5 de 3 rondas 0,882 y 0,911; 20 000 ticks, interiores: 1,855 (H3a) y 1,821 (H3b), p5 de 3 rondas 1,502 y 1,522; 20 000 ticks, parada: 1,721 (H3a) y 1,708 (H3b), p5 de 3 rondas 1,232 y 1,283.

| Candidata | 2000: dH3a | 2000: dH3b | 2000: dp5 | 20 000 int.: dH3a | 20 000 int.: dH3b | 20 000 int.: dp5 | parada: dH3a | parada: dH3b | 2000 / 20 000 / global | Literal | Parada | Final |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `base` | -0,038 ± 0,003 | -0,036 ± 0,004 | -0,047 ± 0,015, -0,039 ± 0,022 | -0,125 ± 0,004 | -0,079 ± 0,003 | -0,188 ± 0,019, -0,133 ± 0,021 | -0,074 ± 0,003 | -0,049 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `kalman` | -0,005 ± 0,002 | +0,004 ± 0,002 | +0,005 ± 0,012, -0,011 ± 0,022 | -0,014 ± 0,002 | +0,011 ± 0,002 | -0,002 ± 0,014, -0,011 ± 0,023 | -0,011 ± 0,001 | +0,009 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `ejec_a` | +0,007 ± 0,000 | +0,027 ± 0,001 | +0,009 ± 0,004, +0,022 ± 0,020 | +0,007 ± 0,000 | +0,050 ± 0,001 | +0,021 ± 0,007, +0,078 ± 0,019 | +0,007 ± 0,000 | +0,048 ± 0,001 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `ejec_b` | +0,012 ± 0,000 | +0,031 ± 0,001 | +0,019 ± 0,006, +0,022 ± 0,022 | +0,010 ± 0,000 | +0,041 ± 0,001 | +0,026 ± 0,008, +0,067 ± 0,023 | +0,011 ± 0,000 | +0,041 ± 0,001 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `espera` | +0,005 ± 0,002 | +0,017 ± 0,003 | +0,019 ± 0,013, -0,006 ± 0,026 | -0,021 ± 0,002 | +0,009 ± 0,002 | -0,016 ± 0,018, -0,056 ± 0,027 | -0,000 ± 0,002 | +0,025 ± 0,002 | PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `aprendiz` | -0,000 ± 0,000 | +0,000 ± 0,000 | +0,001 ± 0,003, +0,000 ± 0,010 | -0,028 ± 0,002 | -0,010 ± 0,002 | -0,024 ± 0,014, -0,061 ± 0,023 | -0,016 ± 0,001 | -0,002 ± 0,001 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `aprendiz_patron` | -0,001 ± 0,000 | -0,001 ± 0,001 | -0,000 ± 0,006, -0,011 ± 0,018 | -0,008 ± 0,001 | -0,000 ± 0,001 | -0,006 ± 0,009, -0,050 ± 0,025 | -0,004 ± 0,001 | +0,002 ± 0,001 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `espera_e` | +0,012 ± 0,002 | +0,025 ± 0,003 | +0,026 ± 0,013, +0,022 ± 0,023 | -0,014 ± 0,002 | +0,016 ± 0,002 | -0,001 ± 0,017, +0,011 ± 0,029 | +0,006 ± 0,002 | +0,032 ± 0,002 | PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `fondo_rec` | -0,004 ± 0,001 | +0,006 ± 0,002 | +0,005 ± 0,009, +0,011 ± 0,024 | -0,000 ± 0,001 | +0,016 ± 0,002 | +0,028 ± 0,012, +0,011 ± 0,020 | -0,008 ± 0,001 | +0,006 ± 0,001 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `fondo_min` | +0,000 ± 0,000 | +0,000 ± 0,000 | +0,000 ± 0,002, +0,006 ± 0,007 | -0,018 ± 0,002 | -0,003 ± 0,002 | -0,007 ± 0,015, -0,056 ± 0,021 | -0,019 ± 0,002 | -0,005 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `fondo_ancla` | -0,031 ± 0,002 | -0,020 ± 0,002 | +0,057 ± 0,010, +0,056 ± 0,025 | -0,135 ± 0,002 | -0,076 ± 0,002 | -0,136 ± 0,016, -0,122 ± 0,022 | -0,157 ± 0,002 | -0,091 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `rec_e` | +0,001 ± 0,001 | +0,013 ± 0,002 | +0,012 ± 0,008, +0,022 ± 0,021 | +0,006 ± 0,001 | +0,024 ± 0,002 | +0,036 ± 0,012, +0,011 ± 0,022 | -0,003 ± 0,001 | +0,014 ± 0,001 | NO_PASA / PASA / NO_PASA | pasa | no confirma | NO_PASA |
| `min_e` | +0,008 ± 0,000 | +0,027 ± 0,001 | +0,010 ± 0,005, +0,022 ± 0,021 | -0,010 ± 0,002 | +0,019 ± 0,002 | +0,012 ± 0,015, +0,000 ± 0,022 | -0,011 ± 0,002 | +0,019 ± 0,002 | PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo` | +0,002 ± 0,001 | +0,013 ± 0,001 | +0,010 ± 0,008, +0,022 ± 0,021 | +0,003 ± 0,001 | +0,019 ± 0,002 | +0,034 ± 0,011, +0,011 ± 0,019 | -0,002 ± 0,001 | +0,014 ± 0,001 | PASA / PASA / PASA | pasa | no confirma | NO_PASA |
| `completo_s` | -0,003 ± 0,001 | +0,005 ± 0,001 | +0,004 ± 0,008, +0,017 ± 0,024 | -0,003 ± 0,001 | +0,012 ± 0,002 | +0,024 ± 0,011, +0,011 ± 0,023 | -0,007 ± 0,001 | +0,007 ± 0,001 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_esp` | -0,004 ± 0,001 | +0,004 ± 0,002 | +0,003 ± 0,009, +0,022 ± 0,022 | +0,000 ± 0,001 | +0,016 ± 0,002 | +0,026 ± 0,012, +0,011 ± 0,023 | -0,004 ± 0,001 | +0,009 ± 0,001 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `completo_ap` | -0,000 ± 0,001 | +0,010 ± 0,002 | +0,006 ± 0,008, +0,022 ± 0,020 | -0,006 ± 0,001 | +0,007 ± 0,002 | +0,022 ± 0,013, +0,000 ± 0,029 | -0,010 ± 0,001 | +0,001 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_ancla` | -0,031 ± 0,002 | -0,020 ± 0,002 | +0,058 ± 0,010, +0,056 ± 0,026 | -0,141 ± 0,002 | -0,080 ± 0,002 | -0,141 ± 0,016, -0,133 ± 0,024 | -0,161 ± 0,002 | -0,093 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_min` | +0,007 ± 0,000 | +0,026 ± 0,001 | +0,009 ± 0,005, +0,022 ± 0,020 | -0,005 ± 0,002 | +0,019 ± 0,002 | +0,014 ± 0,014, +0,011 ± 0,019 | -0,002 ± 0,001 | +0,022 ± 0,001 | PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |

### Campo fuerte

Nivel de `max_media`: 2000 ticks: 1,423 (H3a) y 1,247 (H3b), p5 de 3 rondas 0,760 y 0,750; 20 000 ticks, interiores: 1,740 (H3a) y 1,479 (H3b), p5 de 3 rondas 1,352 y 1,061; 20 000 ticks, parada: 1,631 (H3a) y 1,406 (H3b), p5 de 3 rondas 1,120 y 0,967.

| Candidata | 2000: dH3a | 2000: dH3b | 2000: dp5 | 20 000 int.: dH3a | 20 000 int.: dH3b | 20 000 int.: dp5 | parada: dH3a | parada: dH3b | 2000 / 20 000 / global | Literal | Parada | Final |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `base` | -0,061 ± 0,005 | -0,079 ± 0,006 | -0,060 ± 0,017, -0,083 ± 0,022 | -0,205 ± 0,006 | -0,238 ± 0,008 | -0,252 ± 0,024, -0,289 ± 0,029 | -0,120 ± 0,005 | -0,150 ± 0,006 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `kalman` | -0,007 ± 0,002 | +0,011 ± 0,004 | +0,012 ± 0,014, -0,083 ± 0,023 | -0,016 ± 0,003 | +0,037 ± 0,006 | +0,001 ± 0,016, -0,050 ± 0,034 | -0,015 ± 0,002 | +0,027 ± 0,004 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `ejec_a` | +0,010 ± 0,000 | +0,081 ± 0,002 | +0,016 ± 0,005, +0,056 ± 0,018 | +0,011 ± 0,000 | +0,174 ± 0,002 | +0,019 ± 0,007, +0,150 ± 0,027 | +0,010 ± 0,000 | +0,163 ± 0,002 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `ejec_b` | +0,016 ± 0,001 | +0,081 ± 0,002 | +0,036 ± 0,007, +0,061 ± 0,019 | +0,018 ± 0,001 | +0,139 ± 0,003 | +0,033 ± 0,009, +0,117 ± 0,027 | +0,016 ± 0,000 | +0,133 ± 0,002 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `espera` | +0,002 ± 0,003 | +0,024 ± 0,005 | +0,032 ± 0,015, -0,039 ± 0,029 | -0,024 ± 0,004 | +0,034 ± 0,006 | -0,021 ± 0,019, -0,061 ± 0,034 | +0,001 ± 0,003 | +0,060 ± 0,005 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `aprendiz` | -0,000 ± 0,000 | -0,000 ± 0,001 | +0,001 ± 0,003, +0,006 ± 0,009 | -0,042 ± 0,003 | -0,034 ± 0,005 | -0,030 ± 0,015, -0,117 ± 0,024 | -0,024 ± 0,002 | -0,010 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `aprendiz_patron` | -0,002 ± 0,001 | -0,003 ± 0,002 | +0,004 ± 0,007, -0,022 ± 0,016 | -0,011 ± 0,001 | +0,001 ± 0,004 | -0,008 ± 0,011, -0,072 ± 0,029 | -0,007 ± 0,001 | +0,005 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `espera_e` | +0,011 ± 0,003 | +0,039 ± 0,005 | +0,045 ± 0,015, -0,017 ± 0,022 | -0,013 ± 0,004 | +0,055 ± 0,006 | -0,006 ± 0,019, -0,039 ± 0,033 | +0,011 ± 0,003 | +0,078 ± 0,005 | PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `fondo_rec` | -0,006 ± 0,001 | +0,015 ± 0,003 | +0,019 ± 0,010, -0,017 ± 0,024 | +0,002 ± 0,002 | +0,053 ± 0,005 | +0,018 ± 0,013, +0,006 ± 0,026 | -0,011 ± 0,001 | +0,024 ± 0,004 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `fondo_min` | +0,000 ± 0,000 | +0,001 ± 0,001 | -0,000 ± 0,004, -0,000 ± 0,011 | -0,020 ± 0,003 | -0,011 ± 0,005 | -0,019 ± 0,017, -0,106 ± 0,027 | -0,022 ± 0,002 | -0,016 ± 0,004 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `fondo_ancla` | -0,058 ± 0,002 | -0,097 ± 0,004 | +0,064 ± 0,012, -0,083 ± 0,019 | -0,213 ± 0,003 | -0,287 ± 0,005 | -0,174 ± 0,017, -0,361 ± 0,036 | -0,231 ± 0,003 | -0,274 ± 0,004 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `rec_e` | +0,000 ± 0,001 | +0,029 ± 0,003 | +0,026 ± 0,010, -0,017 ± 0,017 | +0,011 ± 0,002 | +0,077 ± 0,005 | +0,036 ± 0,013, +0,039 ± 0,029 | -0,002 ± 0,001 | +0,046 ± 0,004 | NO_PASA / PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `min_e` | +0,011 ± 0,000 | +0,080 ± 0,002 | +0,017 ± 0,006, +0,050 ± 0,017 | -0,006 ± 0,003 | +0,060 ± 0,006 | -0,001 ± 0,017, -0,017 ± 0,033 | -0,010 ± 0,002 | +0,064 ± 0,004 | PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo` | +0,001 ± 0,001 | +0,030 ± 0,003 | +0,025 ± 0,009, -0,017 ± 0,021 | +0,006 ± 0,002 | +0,062 ± 0,005 | +0,031 ± 0,013, +0,006 ± 0,028 | -0,001 ± 0,001 | +0,043 ± 0,003 | NO_PASA / PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `completo_s` | -0,005 ± 0,001 | +0,013 ± 0,003 | +0,017 ± 0,010, -0,028 ± 0,023 | -0,003 ± 0,002 | +0,041 ± 0,005 | +0,018 ± 0,013, -0,006 ± 0,030 | -0,009 ± 0,001 | +0,024 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_esp` | -0,008 ± 0,001 | +0,004 ± 0,003 | +0,020 ± 0,010, -0,028 ± 0,022 | +0,003 ± 0,002 | +0,054 ± 0,005 | +0,018 ± 0,014, -0,006 ± 0,031 | -0,005 ± 0,001 | +0,032 ± 0,004 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `completo_ap` | -0,001 ± 0,001 | +0,018 ± 0,003 | +0,024 ± 0,009, -0,017 ± 0,022 | -0,004 ± 0,002 | +0,021 ± 0,005 | +0,022 ± 0,016, -0,061 ± 0,031 | -0,012 ± 0,002 | +0,007 ± 0,004 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_ancla` | -0,059 ± 0,002 | -0,098 ± 0,004 | +0,064 ± 0,012, -0,083 ± 0,019 | -0,221 ± 0,003 | -0,297 ± 0,005 | -0,186 ± 0,016, -0,383 ± 0,038 | -0,236 ± 0,003 | -0,280 ± 0,004 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_min` | +0,010 ± 0,000 | +0,080 ± 0,002 | +0,015 ± 0,005, +0,050 ± 0,018 | -0,001 ± 0,003 | +0,059 ± 0,005 | +0,012 ± 0,015, -0,006 ± 0,030 | -0,000 ± 0,002 | +0,071 ± 0,003 | PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |

### Campo fijos2

Nivel de `max_media`: 2000 ticks: 1,483 (H3a) y 1,392 (H3b), p5 de 3 rondas 0,839 y 0,894; 20 000 ticks, interiores: 1,836 (H3a) y 1,702 (H3b), p5 de 3 rondas 1,505 y 1,411; 20 000 ticks, parada: 1,697 (H3a) y 1,595 (H3b), p5 de 3 rondas 1,210 y 1,200.

| Candidata | 2000: dH3a | 2000: dH3b | 2000: dp5 | 20 000 int.: dH3a | 20 000 int.: dH3b | 20 000 int.: dp5 | parada: dH3a | parada: dH3b | 2000 / 20 000 / global | Literal | Parada | Final |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `base` | -0,055 ± 0,004 | -0,054 ± 0,005 | -0,032 ± 0,016, -0,061 ± 0,018 | -0,206 ± 0,006 | -0,152 ± 0,005 | -0,236 ± 0,017, -0,189 ± 0,022 | -0,120 ± 0,004 | -0,094 ± 0,004 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `kalman` | -0,013 ± 0,002 | +0,007 ± 0,003 | +0,009 ± 0,012, -0,028 ± 0,017 | -0,030 ± 0,002 | +0,024 ± 0,004 | -0,021 ± 0,014, -0,022 ± 0,027 | -0,023 ± 0,002 | +0,017 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `ejec_a` | +0,008 ± 0,000 | +0,059 ± 0,001 | +0,014 ± 0,005, +0,044 ± 0,017 | +0,008 ± 0,000 | +0,125 ± 0,002 | +0,015 ± 0,005, +0,122 ± 0,023 | +0,008 ± 0,000 | +0,117 ± 0,001 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `ejec_b` | +0,013 ± 0,001 | +0,061 ± 0,002 | +0,025 ± 0,007, +0,050 ± 0,019 | +0,013 ± 0,001 | +0,098 ± 0,002 | +0,024 ± 0,007, +0,100 ± 0,025 | +0,013 ± 0,000 | +0,095 ± 0,002 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `espera` | -0,003 ± 0,003 | +0,022 ± 0,004 | +0,029 ± 0,013, -0,028 ± 0,019 | -0,039 ± 0,003 | +0,023 ± 0,004 | -0,035 ± 0,015, -0,044 ± 0,028 | -0,009 ± 0,003 | +0,046 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `aprendiz` | -0,000 ± 0,000 | +0,000 ± 0,000 | +0,002 ± 0,004, +0,000 ± 0,010 | -0,050 ± 0,002 | -0,022 ± 0,003 | -0,055 ± 0,014, -0,078 ± 0,019 | -0,029 ± 0,002 | -0,007 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `aprendiz_patron` | -0,003 ± 0,001 | -0,003 ± 0,001 | -0,001 ± 0,006, -0,028 ± 0,016 | -0,015 ± 0,001 | +0,001 ± 0,003 | -0,012 ± 0,009, -0,056 ± 0,025 | -0,009 ± 0,001 | +0,004 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `espera_e` | +0,005 ± 0,003 | +0,033 ± 0,004 | +0,041 ± 0,012, -0,028 ± 0,030 | -0,029 ± 0,003 | +0,037 ± 0,004 | -0,019 ± 0,015, -0,022 ± 0,025 | +0,000 ± 0,002 | +0,058 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `fondo_rec` | -0,010 ± 0,001 | +0,010 ± 0,002 | +0,009 ± 0,009, -0,028 ± 0,017 | -0,012 ± 0,001 | +0,035 ± 0,003 | +0,008 ± 0,011, -0,011 ± 0,024 | -0,018 ± 0,001 | +0,014 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `fondo_min` | -0,000 ± 0,000 | +0,000 ± 0,000 | +0,000 ± 0,003, +0,000 ± 0,007 | -0,041 ± 0,003 | -0,015 ± 0,003 | -0,035 ± 0,014, -0,078 ± 0,021 | -0,034 ± 0,002 | -0,017 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `fondo_ancla` | -0,058 ± 0,002 | -0,058 ± 0,003 | +0,071 ± 0,011, +0,017 ± 0,026 | -0,219 ± 0,003 | -0,176 ± 0,003 | -0,177 ± 0,014, -0,211 ± 0,022 | -0,232 ± 0,003 | -0,178 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `rec_e` | -0,004 ± 0,001 | +0,021 ± 0,002 | +0,019 ± 0,009, -0,028 ± 0,023 | -0,004 ± 0,001 | +0,051 ± 0,003 | +0,020 ± 0,011, +0,011 ± 0,029 | -0,011 ± 0,001 | +0,029 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `min_e` | +0,008 ± 0,000 | +0,058 ± 0,001 | +0,014 ± 0,005, +0,039 ± 0,017 | -0,029 ± 0,003 | +0,035 ± 0,004 | -0,017 ± 0,014, -0,022 ± 0,025 | -0,024 ± 0,002 | +0,041 ± 0,003 | PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo` | -0,003 ± 0,001 | +0,022 ± 0,002 | +0,017 ± 0,008, -0,028 ± 0,025 | -0,008 ± 0,001 | +0,042 ± 0,003 | +0,014 ± 0,011, +0,000 ± 0,025 | -0,009 ± 0,001 | +0,027 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_s` | -0,009 ± 0,001 | +0,008 ± 0,002 | +0,008 ± 0,008, -0,028 ± 0,017 | -0,015 ± 0,001 | +0,027 ± 0,003 | +0,003 ± 0,011, -0,011 ± 0,022 | -0,016 ± 0,001 | +0,013 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_esp` | -0,011 ± 0,001 | +0,004 ± 0,003 | +0,015 ± 0,009, -0,028 ± 0,021 | -0,009 ± 0,002 | +0,036 ± 0,003 | +0,008 ± 0,011, -0,011 ± 0,027 | -0,012 ± 0,001 | +0,019 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_ap` | -0,006 ± 0,001 | +0,013 ± 0,002 | +0,015 ± 0,009, -0,028 ± 0,020 | -0,023 ± 0,002 | +0,011 ± 0,003 | +0,001 ± 0,013, -0,056 ± 0,031 | -0,022 ± 0,001 | +0,002 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_ancla` | -0,059 ± 0,002 | -0,059 ± 0,003 | +0,071 ± 0,011, +0,017 ± 0,026 | -0,226 ± 0,003 | -0,183 ± 0,003 | -0,181 ± 0,014, -0,211 ± 0,028 | -0,237 ± 0,003 | -0,182 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_min` | +0,008 ± 0,000 | +0,058 ± 0,001 | +0,015 ± 0,005, +0,044 ± 0,017 | -0,020 ± 0,002 | +0,038 ± 0,003 | -0,012 ± 0,013, -0,011 ± 0,024 | -0,012 ± 0,002 | +0,047 ± 0,002 | PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |

### Campo fijos3

Nivel de `max_media`: 2000 ticks: 1,437 (H3a) y 1,345 (H3b), p5 de 3 rondas 0,830 y 0,856; 20 000 ticks, interiores: 1,738 (H3a) y 1,626 (H3b), p5 de 3 rondas 1,390 y 1,306; 20 000 ticks, parada: 1,627 (H3a) y 1,536 (H3b), p5 de 3 rondas 1,148 y 1,144.

| Candidata | 2000: dH3a | 2000: dH3b | 2000: dp5 | 20 000 int.: dH3a | 20 000 int.: dH3b | 20 000 int.: dp5 | parada: dH3a | parada: dH3b | 2000 / 20 000 / global | Literal | Parada | Final |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `base` | -0,054 ± 0,004 | -0,060 ± 0,005 | -0,050 ± 0,014, -0,044 ± 0,024 | -0,197 ± 0,006 | -0,170 ± 0,005 | -0,214 ± 0,017, -0,206 ± 0,020 | -0,115 ± 0,004 | -0,107 ± 0,004 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `kalman` | -0,007 ± 0,002 | +0,008 ± 0,003 | +0,003 ± 0,010, -0,028 ± 0,023 | -0,015 ± 0,003 | +0,026 ± 0,004 | +0,001 ± 0,014, -0,028 ± 0,027 | -0,013 ± 0,002 | +0,020 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `ejec_a` | +0,009 ± 0,000 | +0,058 ± 0,001 | +0,012 ± 0,004, +0,072 ± 0,017 | +0,010 ± 0,000 | +0,122 ± 0,002 | +0,018 ± 0,005, +0,161 ± 0,027 | +0,010 ± 0,000 | +0,114 ± 0,001 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `ejec_b` | +0,014 ± 0,001 | +0,060 ± 0,002 | +0,022 ± 0,006, +0,078 ± 0,018 | +0,017 ± 0,001 | +0,097 ± 0,002 | +0,028 ± 0,007, +0,094 ± 0,020 | +0,015 ± 0,000 | +0,094 ± 0,002 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `espera` | +0,003 ± 0,003 | +0,021 ± 0,004 | +0,023 ± 0,012, +0,011 ± 0,029 | -0,022 ± 0,003 | +0,025 ± 0,005 | -0,032 ± 0,018, -0,039 ± 0,026 | +0,003 ± 0,003 | +0,046 ± 0,004 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `aprendiz` | -0,000 ± 0,000 | +0,000 ± 0,000 | +0,000 ± 0,003, +0,000 ± 0,010 | -0,040 ± 0,003 | -0,024 ± 0,003 | -0,037 ± 0,013, -0,050 ± 0,023 | -0,022 ± 0,002 | -0,007 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `aprendiz_patron` | -0,002 ± 0,001 | -0,003 ± 0,001 | +0,000 ± 0,005, -0,011 ± 0,017 | -0,010 ± 0,001 | +0,001 ± 0,003 | -0,007 ± 0,008, -0,039 ± 0,021 | -0,006 ± 0,001 | +0,004 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `espera_e` | +0,011 ± 0,003 | +0,033 ± 0,004 | +0,034 ± 0,012, +0,011 ± 0,021 | -0,011 ± 0,003 | +0,039 ± 0,005 | -0,011 ± 0,017, -0,017 ± 0,029 | +0,013 ± 0,003 | +0,060 ± 0,003 | PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `fondo_rec` | -0,006 ± 0,001 | +0,011 ± 0,002 | +0,005 ± 0,008, +0,011 ± 0,025 | +0,002 ± 0,002 | +0,037 ± 0,003 | +0,027 ± 0,010, +0,028 ± 0,023 | -0,010 ± 0,001 | +0,017 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `fondo_min` | +0,000 ± 0,000 | +0,000 ± 0,000 | +0,001 ± 0,002, -0,000 ± 0,010 | -0,016 ± 0,003 | -0,007 ± 0,004 | -0,013 ± 0,014, -0,056 ± 0,022 | -0,020 ± 0,002 | -0,011 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `fondo_ancla` | -0,056 ± 0,002 | -0,065 ± 0,003 | +0,059 ± 0,011, +0,011 ± 0,019 | -0,209 ± 0,003 | -0,197 ± 0,004 | -0,154 ± 0,013, -0,239 ± 0,022 | -0,225 ± 0,003 | -0,197 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `rec_e` | -0,000 ± 0,001 | +0,022 ± 0,002 | +0,014 ± 0,008, +0,011 ± 0,019 | +0,011 ± 0,002 | +0,054 ± 0,003 | +0,041 ± 0,011, +0,028 ± 0,024 | -0,002 ± 0,001 | +0,033 ± 0,003 | NO_PASA / PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `min_e` | +0,009 ± 0,000 | +0,058 ± 0,001 | +0,013 ± 0,005, +0,072 ± 0,017 | -0,004 ± 0,003 | +0,043 ± 0,004 | +0,007 ± 0,014, +0,006 ± 0,029 | -0,009 ± 0,002 | +0,046 ± 0,003 | PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo` | +0,001 ± 0,001 | +0,023 ± 0,002 | +0,014 ± 0,007, +0,011 ± 0,020 | +0,006 ± 0,002 | +0,043 ± 0,003 | +0,031 ± 0,012, +0,028 ± 0,020 | -0,001 ± 0,001 | +0,031 ± 0,002 | NO_PASA / PASA / NO_PASA | pasa | no confirma | NO_PASA |
| `completo_s` | -0,005 ± 0,001 | +0,009 ± 0,002 | +0,003 ± 0,007, +0,011 ± 0,024 | -0,002 ± 0,002 | +0,028 ± 0,003 | +0,020 ± 0,012, +0,017 ± 0,025 | -0,008 ± 0,001 | +0,017 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_esp` | -0,008 ± 0,001 | +0,004 ± 0,003 | +0,005 ± 0,008, +0,011 ± 0,026 | +0,003 ± 0,002 | +0,037 ± 0,003 | +0,020 ± 0,011, +0,028 ± 0,023 | -0,004 ± 0,001 | +0,022 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `completo_ap` | -0,002 ± 0,001 | +0,014 ± 0,002 | +0,012 ± 0,007, +0,011 ± 0,018 | -0,003 ± 0,002 | +0,015 ± 0,004 | +0,031 ± 0,012, -0,039 ± 0,028 | -0,010 ± 0,002 | +0,005 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_ancla` | -0,057 ± 0,002 | -0,065 ± 0,003 | +0,059 ± 0,010, +0,011 ± 0,019 | -0,217 ± 0,003 | -0,205 ± 0,004 | -0,161 ± 0,013, -0,239 ± 0,022 | -0,230 ± 0,003 | -0,202 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_min` | +0,009 ± 0,000 | +0,058 ± 0,001 | +0,013 ± 0,004, +0,072 ± 0,017 | +0,000 ± 0,003 | +0,043 ± 0,004 | +0,013 ± 0,013, -0,000 ± 0,030 | +0,000 ± 0,002 | +0,050 ± 0,003 | PASA / NO_PASA / NO_PASA | pasa | confirma | NO_PASA |

### Campo racional

Nivel de `max_media`: 2000 ticks: 1,208 (H3a) y 1,245 (H3b), p5 de 3 rondas 0,647 y 0,728; 20 000 ticks, interiores: 1,500 (H3a) y 1,514 (H3b), p5 de 3 rondas 1,017 y 1,061; 20 000 ticks, parada: 1,404 (H3a) y 1,428 (H3b), p5 de 3 rondas 0,881 y 0,939.

| Candidata | 2000: dH3a | 2000: dH3b | 2000: dp5 | 20 000 int.: dH3a | 20 000 int.: dH3b | 20 000 int.: dp5 | parada: dH3a | parada: dH3b | 2000 / 20 000 / global | Literal | Parada | Final |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `base` | -0,094 ± 0,006 | -0,075 ± 0,006 | -0,108 ± 0,015, -0,083 ± 0,022 | -0,231 ± 0,007 | -0,204 ± 0,007 | -0,268 ± 0,024, -0,261 ± 0,024 | -0,141 ± 0,005 | -0,128 ± 0,005 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `kalman` | +0,004 ± 0,003 | +0,015 ± 0,004 | -0,003 ± 0,011, -0,006 ± 0,025 | +0,012 ± 0,003 | +0,026 ± 0,004 | +0,013 ± 0,017, -0,006 ± 0,031 | +0,008 ± 0,003 | +0,021 ± 0,003 | NO_PASA / PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `ejec_a` | +0,015 ± 0,000 | +0,036 ± 0,001 | +0,015 ± 0,004, +0,028 ± 0,020 | +0,018 ± 0,000 | +0,054 ± 0,001 | +0,028 ± 0,007, +0,072 ± 0,022 | +0,016 ± 0,000 | +0,050 ± 0,001 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `ejec_b` | +0,024 ± 0,001 | +0,046 ± 0,001 | +0,032 ± 0,006, +0,061 ± 0,017 | +0,029 ± 0,001 | +0,057 ± 0,002 | +0,044 ± 0,009, +0,072 ± 0,021 | +0,026 ± 0,000 | +0,054 ± 0,001 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `espera` | +0,022 ± 0,004 | +0,036 ± 0,004 | +0,025 ± 0,012, +0,006 ± 0,017 | +0,014 ± 0,004 | +0,029 ± 0,005 | -0,003 ± 0,020, -0,006 ± 0,030 | +0,038 ± 0,003 | +0,049 ± 0,004 | PASA / PASA / PASA | no pasa | confirma | **PASA** |
| `aprendiz` | +0,000 ± 0,000 | +0,000 ± 0,000 | -0,001 ± 0,003, +0,000 ± 0,009 | -0,031 ± 0,003 | -0,025 ± 0,004 | -0,034 ± 0,018, -0,050 ± 0,027 | -0,012 ± 0,002 | -0,008 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `aprendiz_patron` | -0,000 ± 0,001 | +0,002 ± 0,001 | -0,001 ± 0,005, +0,006 ± 0,012 | -0,001 ± 0,001 | +0,003 ± 0,002 | -0,000 ± 0,011, +0,006 ± 0,022 | +0,002 ± 0,001 | +0,006 ± 0,002 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `espera_e` | +0,034 ± 0,004 | +0,049 ± 0,004 | +0,039 ± 0,012, +0,006 ± 0,023 | +0,029 ± 0,004 | +0,045 ± 0,005 | +0,013 ± 0,021, +0,006 ± 0,032 | +0,051 ± 0,003 | +0,063 ± 0,004 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `fondo_rec` | +0,002 ± 0,002 | +0,009 ± 0,002 | +0,015 ± 0,008, +0,006 ± 0,015 | +0,023 ± 0,002 | +0,031 ± 0,003 | +0,046 ± 0,014, +0,050 ± 0,028 | +0,006 ± 0,002 | +0,014 ± 0,002 | NO_PASA / PASA / NO_PASA | pasa | confirma | NO_PASA |
| `fondo_min` | +0,001 ± 0,000 | +0,000 ± 0,001 | -0,000 ± 0,003, +0,000 ± 0,007 | +0,011 ± 0,004 | +0,007 ± 0,004 | +0,016 ± 0,018, -0,000 ± 0,025 | -0,002 ± 0,003 | -0,004 ± 0,003 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `fondo_ancla` | -0,096 ± 0,003 | -0,086 ± 0,004 | -0,036 ± 0,011, -0,061 ± 0,020 | -0,238 ± 0,004 | -0,204 ± 0,004 | -0,201 ± 0,017, -0,206 ± 0,031 | -0,263 ± 0,004 | -0,235 ± 0,004 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `rec_e` | +0,011 ± 0,002 | +0,019 ± 0,002 | +0,029 ± 0,008, +0,006 ± 0,022 | +0,036 ± 0,002 | +0,047 ± 0,003 | +0,063 ± 0,014, +0,072 ± 0,026 | +0,017 ± 0,002 | +0,029 ± 0,002 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `min_e` | +0,016 ± 0,001 | +0,036 ± 0,001 | +0,015 ± 0,005, +0,028 ± 0,020 | +0,031 ± 0,004 | +0,039 ± 0,004 | +0,038 ± 0,019, +0,017 ± 0,030 | +0,015 ± 0,003 | +0,029 ± 0,003 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `completo` | +0,010 ± 0,001 | +0,020 ± 0,002 | +0,028 ± 0,008, +0,017 ± 0,023 | +0,028 ± 0,002 | +0,036 ± 0,003 | +0,055 ± 0,014, +0,072 ± 0,027 | +0,017 ± 0,001 | +0,027 ± 0,002 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `completo_s` | +0,001 ± 0,001 | +0,009 ± 0,002 | +0,017 ± 0,007, +0,006 ± 0,016 | +0,016 ± 0,002 | +0,023 ± 0,003 | +0,040 ± 0,014, +0,039 ± 0,028 | +0,006 ± 0,001 | +0,014 ± 0,002 | NO_PASA / PASA / NO_PASA | pasa | confirma | NO_PASA |
| `completo_esp` | -0,001 ± 0,002 | +0,007 ± 0,002 | +0,029 ± 0,008, +0,006 ± 0,019 | +0,024 ± 0,002 | +0,033 ± 0,003 | +0,043 ± 0,013, +0,061 ± 0,030 | +0,012 ± 0,002 | +0,021 ± 0,002 | NO_PASA / PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_ap` | +0,007 ± 0,002 | +0,013 ± 0,002 | +0,025 ± 0,008, +0,006 ± 0,019 | +0,023 ± 0,003 | +0,025 ± 0,004 | +0,052 ± 0,015, +0,028 ± 0,028 | +0,009 ± 0,002 | +0,011 ± 0,003 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `completo_ancla` | -0,097 ± 0,003 | -0,087 ± 0,004 | -0,038 ± 0,011, -0,061 ± 0,020 | -0,249 ± 0,004 | -0,215 ± 0,004 | -0,211 ± 0,018, -0,228 ± 0,032 | -0,270 ± 0,004 | -0,242 ± 0,004 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_min` | +0,015 ± 0,000 | +0,036 ± 0,001 | +0,015 ± 0,004, +0,028 ± 0,019 | +0,026 ± 0,004 | +0,036 ± 0,004 | +0,034 ± 0,018, +0,017 ± 0,024 | +0,020 ± 0,002 | +0,035 ± 0,002 | PASA / PASA / PASA | pasa | confirma | **PASA** |

### Campo reversores

Nivel de `max_media`: 2000 ticks: 1,062 (H3a) y 1,041 (H3b), p5 de 3 rondas 0,215 y 0,506; 20 000 ticks, interiores: 1,250 (H3a) y 1,169 (H3b), p5 de 3 rondas 0,448 y 0,683; 20 000 ticks, parada: 1,212 (H3a) y 1,137 (H3b), p5 de 3 rondas 0,402 y 0,639.

| Candidata | 2000: dH3a | 2000: dH3b | 2000: dp5 | 20 000 int.: dH3a | 20 000 int.: dH3b | 20 000 int.: dp5 | parada: dH3a | parada: dH3b | 2000 / 20 000 / global | Literal | Parada | Final |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `base` | -0,183 ± 0,013 | -0,115 ± 0,009 | -0,215 ± 0,021, -0,111 ± 0,021 | -0,593 ± 0,018 | -0,384 ± 0,012 | -0,448 ± 0,036, -0,383 ± 0,027 | -0,369 ± 0,014 | -0,240 ± 0,009 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `kalman` | +0,007 ± 0,007 | +0,015 ± 0,006 | +0,110 ± 0,021, -0,106 ± 0,022 | -0,006 ± 0,010 | +0,060 ± 0,009 | +0,069 ± 0,036, -0,117 ± 0,044 | -0,011 ± 0,007 | +0,043 ± 0,007 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `ejec_a` | +0,034 ± 0,001 | +0,131 ± 0,003 | +0,053 ± 0,011, +0,089 ± 0,018 | +0,049 ± 0,002 | +0,291 ± 0,004 | +0,078 ± 0,018, +0,206 ± 0,029 | +0,043 ± 0,001 | +0,270 ± 0,003 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `ejec_b` | +0,051 ± 0,002 | +0,128 ± 0,004 | +0,119 ± 0,013, +0,094 ± 0,019 | +0,079 ± 0,003 | +0,227 ± 0,005 | +0,153 ± 0,023, +0,117 ± 0,030 | +0,067 ± 0,002 | +0,219 ± 0,004 | PASA / PASA / PASA | pasa | confirma | **PASA** |
| `espera` | +0,021 ± 0,008 | +0,034 ± 0,007 | +0,143 ± 0,022, -0,106 ± 0,017 | -0,012 ± 0,012 | +0,060 ± 0,010 | +0,058 ± 0,041, -0,150 ± 0,039 | +0,037 ± 0,008 | +0,094 ± 0,008 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `aprendiz` | -0,001 ± 0,001 | -0,000 ± 0,001 | -0,000 ± 0,005, -0,011 ± 0,012 | -0,095 ± 0,008 | -0,055 ± 0,008 | -0,047 ± 0,033, -0,211 ± 0,032 | -0,053 ± 0,005 | -0,019 ± 0,005 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `aprendiz_patron` | -0,001 ± 0,002 | -0,005 ± 0,003 | +0,033 ± 0,011, -0,039 ± 0,016 | -0,017 ± 0,005 | +0,001 ± 0,007 | +0,048 ± 0,026, -0,150 ± 0,032 | -0,011 ± 0,003 | +0,008 ± 0,005 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `espera_e` | +0,042 ± 0,008 | +0,054 ± 0,007 | +0,165 ± 0,023, -0,094 ± 0,029 | +0,021 ± 0,012 | +0,092 ± 0,010 | +0,099 ± 0,040, -0,128 ± 0,040 | +0,065 ± 0,008 | +0,122 ± 0,007 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `fondo_rec` | -0,001 ± 0,004 | +0,024 ± 0,005 | +0,104 ± 0,017, -0,083 ± 0,029 | +0,029 ± 0,007 | +0,086 ± 0,008 | +0,146 ± 0,031, -0,017 ± 0,029 | -0,001 ± 0,005 | +0,042 ± 0,006 | NO_PASA / PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `fondo_min` | +0,000 ± 0,001 | +0,001 ± 0,001 | -0,002 ± 0,006, -0,006 ± 0,012 | -0,029 ± 0,010 | -0,018 ± 0,009 | +0,019 ± 0,037, -0,194 ± 0,030 | -0,037 ± 0,006 | -0,028 ± 0,006 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `fondo_ancla` | -0,185 ± 0,007 | -0,168 ± 0,006 | -0,026 ± 0,022, -0,261 ± 0,025 | -0,577 ± 0,011 | -0,480 ± 0,009 | -0,365 ± 0,036, -0,550 ± 0,027 | -0,543 ± 0,008 | -0,446 ± 0,007 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `rec_e` | +0,016 ± 0,004 | +0,044 ± 0,005 | +0,130 ± 0,017, -0,039 ± 0,023 | +0,063 ± 0,007 | +0,125 ± 0,008 | +0,188 ± 0,030, -0,006 ± 0,032 | +0,028 ± 0,005 | +0,076 ± 0,006 | PASA / PASA / PASA | no pasa | confirma | **PASA** |
| `min_e` | +0,034 ± 0,002 | +0,129 ± 0,003 | +0,054 ± 0,012, +0,089 ± 0,019 | +0,016 ± 0,010 | +0,098 ± 0,009 | +0,073 ± 0,037, -0,083 ± 0,041 | +0,001 ± 0,006 | +0,105 ± 0,006 | PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo` | +0,018 ± 0,004 | +0,046 ± 0,005 | +0,118 ± 0,017, -0,039 ± 0,023 | +0,044 ± 0,007 | +0,101 ± 0,008 | +0,169 ± 0,031, -0,017 ± 0,027 | +0,023 ± 0,005 | +0,071 ± 0,005 | PASA / PASA / PASA | no pasa | confirma | **PASA** |
| `completo_s` | +0,000 ± 0,004 | +0,022 ± 0,005 | +0,099 ± 0,016, -0,061 ± 0,026 | +0,015 ± 0,007 | +0,067 ± 0,008 | +0,126 ± 0,031, -0,028 ± 0,030 | -0,003 ± 0,005 | +0,040 ± 0,005 | NO_PASA / PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `completo_esp` | -0,009 ± 0,005 | +0,005 ± 0,005 | +0,124 ± 0,018, -0,094 ± 0,027 | +0,036 ± 0,007 | +0,090 ± 0,008 | +0,148 ± 0,032, -0,017 ± 0,026 | +0,013 ± 0,005 | +0,054 ± 0,006 | NO_PASA / PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_ap` | +0,008 ± 0,004 | +0,027 ± 0,005 | +0,109 ± 0,017, -0,072 ± 0,025 | +0,006 ± 0,009 | +0,033 ± 0,009 | +0,096 ± 0,034, -0,139 ± 0,040 | -0,012 ± 0,006 | +0,014 ± 0,006 | NO_PASA / NO_PASA / NO_PASA | no pasa | no confirma | NO_PASA |
| `completo_ancla` | -0,187 ± 0,007 | -0,170 ± 0,006 | -0,030 ± 0,022, -0,261 ± 0,027 | -0,598 ± 0,011 | -0,495 ± 0,009 | -0,376 ± 0,036, -0,550 ± 0,027 | -0,556 ± 0,008 | -0,455 ± 0,007 | NO_PASA / NO_PASA / NO_PASA | no pasa | confirma | NO_PASA |
| `completo_min` | +0,033 ± 0,001 | +0,129 ± 0,003 | +0,053 ± 0,012, +0,089 ± 0,019 | +0,023 ± 0,008 | +0,097 ± 0,008 | +0,082 ± 0,036, -0,061 ± 0,039 | +0,019 ± 0,005 | +0,114 ± 0,006 | PASA / PASA / PASA | no pasa | confirma | **PASA** |

### Resumen del veredicto final por campo

| Candidata | ingenuo | mixto | fuerte | fijos2 | fijos3 | racional | reversores | Pasa en |
|---|---|---|---|---|---|---|---|---|
| `base` | no | no | no | no | no | no | no | 0 de 7 |
| `kalman` | no | no | no | no | no | no | no | 0 de 7 |
| `ejec_a` | PASA | PASA | PASA | PASA | PASA | PASA | PASA | 7 de 7 |
| `ejec_b` | PASA | PASA | PASA | PASA | PASA | PASA | PASA | 7 de 7 |
| `espera` | no | no | no | no | no | PASA | no | 1 de 7 |
| `aprendiz` | no | no | no | no | no | no | no | 0 de 7 |
| `aprendiz_patron` | no | no | no | no | no | no | no | 0 de 7 |
| `espera_e` | no | no | no | no | no | PASA | no | 1 de 7 |
| `fondo_rec` | PASA | no | no | no | no | no | no | 1 de 7 |
| `fondo_min` | no | no | no | no | no | no | no | 0 de 7 |
| `fondo_ancla` | no | no | no | no | no | no | no | 0 de 7 |
| `rec_e` | PASA | no | no | no | no | PASA | PASA | 3 de 7 |
| `min_e` | PASA | no | no | no | no | PASA | no | 2 de 7 |
| `completo` | PASA | no | no | no | no | PASA | PASA | 3 de 7 |
| `completo_s` | PASA | no | no | no | no | no | no | 1 de 7 |
| `completo_esp` | PASA | no | no | no | no | no | no | 1 de 7 |
| `completo_ap` | PASA | no | no | no | no | PASA | no | 2 de 7 |
| `completo_ancla` | no | no | no | no | no | no | no | 0 de 7 |
| `completo_min` | PASA | no | no | no | no | PASA | PASA | 3 de 7 |

## 2. H1 (patrimonio) y H2 (exceso sobre comprar y mantener)

La diferencia de H2 en pesos es la misma de H1, porque comprar y mantener es igual para todos en cada serie. Por eso se informa además la razón W/B&H. "p5 de 3 rondas" es el percentil 5 del promedio de tres rondas.

### 2000 ticks, conjunto evidencia (10000 series)

| Candidata | H1: media | H1: p5 | H1: dif. contra `max_media` | H1: p5 de 3 rondas (dif.) | H2: exceso medio | H2: p5 del exceso | H2: p5 de 3 rondas | H2: W/B&H media | H2: W/B&H dif. | Órdenes |
|---|---|---|---|---|---|---|---|---|---|---|
| `max_media` | 10 982 | 8 754 | +0 ± 0 | 9 525 (+0 ± 0) | +1 203 | -2 710 | -1 200 | 1,241 | +0,000 ± 0,000 | 55,2 |
| `base` | 10 879 | 8 875 | -103 ± 10 | 9 553 (+28 ± 32) | +1 100 | -2 908 | -1 324 | 1,239 | -0,002 ± 0,006 | 35,1 |
| `kalman` | 11 002 | 8 775 | +20 ± 6 | 9 540 (+15 ± 23) | +1 223 | -2 690 | -1 183 | 1,244 | +0,003 ± 0,002 | 55,6 |
| `ejec_a` | 10 997 | 8 781 | +15 ± 0 | 9 543 (+18 ± 9) | +1 218 | -2 703 | -1 183 | 1,243 | +0,002 ± 0,000 | 51,1 |
| `ejec_b` | 11 006 | 8 815 | +24 ± 1 | 9 566 (+42 ± 13) | +1 227 | -2 696 | -1 174 | 1,244 | +0,003 ± 0,000 | 47,7 |
| `espera` | 11 019 | 8 836 | +37 ± 7 | 9 614 (+89 ± 27) | +1 240 | -2 711 | -1 222 | 1,249 | +0,008 ± 0,005 | 50,0 |
| `aprendiz` | 10 980 | 8 749 | -2 ± 1 | 9 527 (+2 ± 7) | +1 201 | -2 710 | -1 193 | 1,242 | +0,001 ± 0,002 | 55,2 |
| `aprendiz_patron` | 10 983 | 8 753 | +1 ± 1 | 9 531 (+6 ± 13) | +1 204 | -2 712 | -1 187 | 1,241 | +0,000 ± 0,000 | 55,2 |
| `espera_e` | 11 032 | 8 856 | +50 ± 7 | 9 629 (+104 ± 27) | +1 253 | -2 703 | -1 213 | 1,251 | +0,010 ± 0,005 | 46,4 |
| `fondo_rec` | 10 988 | 8 756 | +6 ± 4 | 9 529 (+4 ± 19) | +1 209 | -2 699 | -1 168 | 1,240 | -0,001 ± 0,002 | 55,2 |
| `fondo_min` | 10 983 | 8 752 | +1 ± 1 | 9 523 (-2 ± 6) | +1 204 | -2 710 | -1 195 | 1,241 | +0,000 ± 0,000 | 55,4 |
| `fondo_ancla` | 10 817 | 8 692 | -165 ± 13 | 9 449 (-76 ± 22) | +1 038 | -2 367 | -1 054 | 1,211 | -0,030 ± 0,004 | 40,1 |
| `rec_e` | 10 998 | 8 769 | +16 ± 4 | 9 542 (+17 ± 19) | +1 219 | -2 696 | -1 160 | 1,242 | +0,001 ± 0,002 | 52,2 |
| `min_e` | 10 998 | 8 780 | +16 ± 1 | 9 541 (+16 ± 10) | +1 219 | -2 701 | -1 183 | 1,243 | +0,002 ± 0,000 | 51,2 |
| `completo` | 10 994 | 8 772 | +12 ± 3 | 9 544 (+19 ± 18) | +1 215 | -2 703 | -1 168 | 1,241 | +0,000 ± 0,001 | 52,4 |
| `completo_s` | 10 985 | 8 759 | +4 ± 3 | 9 532 (+7 ± 18) | +1 206 | -2 718 | -1 175 | 1,240 | -0,001 ± 0,001 | 55,3 |
| `completo_esp` | 10 987 | 8 794 | +5 ± 4 | 9 546 (+21 ± 19) | +1 208 | -2 716 | -1 193 | 1,242 | +0,001 ± 0,002 | 55,4 |
| `completo_ap` | 10 992 | 8 764 | +10 ± 3 | 9 535 (+10 ± 17) | +1 213 | -2 689 | -1 172 | 1,241 | -0,000 ± 0,002 | 53,8 |
| `completo_ancla` | 10 816 | 8 700 | -165 ± 13 | 9 452 (-73 ± 22) | +1 038 | -2 383 | -1 055 | 1,211 | -0,030 ± 0,004 | 39,8 |
| `completo_min` | 10 996 | 8 781 | +14 ± 1 | 9 543 (+18 ± 10) | +1 217 | -2 703 | -1 181 | 1,243 | +0,002 ± 0,000 | 51,1 |

### 20 000 ticks, interiores, conjunto evidencia (4021 series)

| Candidata | H1: media | H1: p5 | H1: dif. contra `max_media` | H1: p5 de 3 rondas (dif.) | H2: exceso medio | H2: p5 del exceso | H2: p5 de 3 rondas | H2: W/B&H media | H2: W/B&H dif. | Órdenes |
|---|---|---|---|---|---|---|---|---|---|---|
| `max_media` | 26 534 | 10 987 | +0 ± 0 | 14 918 (+0 ± 0) | +16 569 | -1 011 | +3 941 | 3,422 | +0,000 ± 0,000 | 723,4 |
| `base` | 23 256 | 10 435 | -3 278 ± 124 | 13 680 (-1 238 ± 190) | +13 291 | -2 146 | +2 399 | 3,020 | -0,402 ± 0,018 | 426,1 |
| `kalman` | 26 976 | 11 118 | +442 ± 63 | 15 076 (+158 ± 156) | +17 011 | -967 | +4 076 | 3,494 | +0,073 ± 0,010 | 738,0 |
| `ejec_a` | 26 710 | 11 127 | +176 ± 3 | 15 068 (+150 ± 52) | +16 745 | -831 | +4 063 | 3,445 | +0,024 ± 0,001 | 695,2 |
| `ejec_b` | 26 823 | 11 205 | +290 ± 7 | 15 156 (+238 ± 70) | +16 859 | -801 | +4 143 | 3,461 | +0,040 ± 0,001 | 666,9 |
| `espera` | 26 748 | 10 976 | +215 ± 82 | 15 157 (+239 ± 190) | +16 784 | -1 090 | +4 122 | 3,481 | +0,059 ± 0,012 | 663,1 |
| `aprendiz` | 26 235 | 10 781 | -298 ± 57 | 14 755 (-163 ± 145) | +16 271 | -994 | +3 866 | 3,368 | -0,053 ± 0,009 | 722,9 |
| `aprendiz_patron` | 26 559 | 10 968 | +26 ± 23 | 14 953 (+36 ± 104) | +16 595 | -1 056 | +3 868 | 3,429 | +0,007 ± 0,003 | 721,2 |
| `espera_e` | 26 900 | 11 091 | +366 ± 81 | 15 298 (+380 ± 189) | +16 935 | -963 | +4 242 | 3,501 | +0,079 ± 0,012 | 637,5 |
| `fondo_rec` | 27 054 | 11 010 | +520 ± 43 | 15 125 (+207 ± 131) | +17 089 | -857 | +4 062 | 3,491 | +0,069 ± 0,007 | 716,1 |
| `fondo_min` | 27 135 | 10 935 | +602 ± 86 | 15 075 (+157 ± 202) | +17 171 | -875 | +4 271 | 3,473 | +0,051 ± 0,013 | 795,4 |
| `fondo_ancla` | 22 788 | 10 901 | -3 746 ± 101 | 14 047 (-871 ± 147) | +12 823 | -725 | +3 314 | 2,850 | -0,572 ± 0,019 | 492,5 |
| `rec_e` | 27 196 | 11 192 | +662 ± 44 | 15 223 (+306 ± 129) | +17 231 | -727 | +4 190 | 3,510 | +0,088 ± 0,007 | 690,8 |
| `min_e` | 27 332 | 11 062 | +798 ± 86 | 15 265 (+347 ± 205) | +17 367 | -734 | +4 431 | 3,499 | +0,077 ± 0,013 | 765,1 |
| `completo` | 27 084 | 11 065 | +550 ± 43 | 15 119 (+201 ± 126) | +17 119 | -839 | +4 105 | 3,493 | +0,071 ± 0,006 | 694,4 |
| `completo_s` | 26 964 | 11 011 | +430 ± 42 | 15 054 (+136 ± 123) | +16 999 | -912 | +4 033 | 3,477 | +0,055 ± 0,006 | 717,8 |
| `completo_esp` | 27 055 | 10 944 | +521 ± 41 | 15 071 (+153 ± 140) | +17 090 | -1 014 | +4 068 | 3,499 | +0,077 ± 0,006 | 699,8 |
| `completo_ap` | 27 149 | 10 999 | +615 ± 64 | 15 141 (+223 ± 141) | +17 184 | -1 010 | +4 271 | 3,495 | +0,074 ± 0,009 | 751,9 |
| `completo_ancla` | 22 693 | 10 815 | -3 841 ± 103 | 13 993 (-925 ± 146) | +12 728 | -859 | +3 235 | 2,836 | -0,586 ± 0,020 | 497,7 |
| `completo_min` | 27 011 | 11 211 | +478 ± 69 | 15 158 (+240 ± 152) | +17 047 | -808 | +4 337 | 3,459 | +0,038 ± 0,010 | 735,0 |

### 20 000 ticks, parada, conjunto evidencia (8000 series)

| Candidata | H1: media | H1: p5 | H1: dif. contra `max_media` | H1: p5 de 3 rondas (dif.) | H2: exceso medio | H2: p5 del exceso | H2: p5 de 3 rondas | H2: W/B&H media | H2: W/B&H dif. | Órdenes |
|---|---|---|---|---|---|---|---|---|---|---|
| `max_media` | 21 556 | 6 689 | +0 ± 0 | 11 191 (+0 ± 0) | +13 059 | -4 572 | +1 363 | 5,040 | +0,000 ± 0,000 | 596,7 |
| `base` | 19 657 | 7 056 | -1 899 ± 74 | 10 944 (-247 ± 117) | +11 160 | -5 402 | +526 | 4,814 | -0,226 ± 0,022 | 363,3 |
| `kalman` | 21 860 | 6 622 | +304 ± 37 | 11 227 (+37 ± 93) | +13 362 | -4 712 | +1 414 | 5,128 | +0,088 ± 0,012 | 607,5 |
| `ejec_a` | 21 684 | 6 756 | +128 ± 2 | 11 264 (+73 ± 32) | +13 187 | -4 507 | +1 448 | 5,069 | +0,028 ± 0,001 | 574,0 |
| `ejec_b` | 21 776 | 6 805 | +220 ± 4 | 11 323 (+132 ± 45) | +13 279 | -4 534 | +1 506 | 5,095 | +0,055 ± 0,001 | 552,7 |
| `espera` | 21 936 | 7 082 | +380 ± 49 | 11 588 (+397 ± 102) | +13 438 | -4 788 | +1 466 | 5,277 | +0,237 ± 0,015 | 548,8 |
| `aprendiz` | 21 421 | 6 758 | -135 ± 34 | 11 165 (-26 ± 81) | +12 924 | -4 518 | +1 405 | 5,011 | -0,029 ± 0,011 | 596,7 |
| `aprendiz_patron` | 21 597 | 6 694 | +40 ± 13 | 11 214 (+23 ± 59) | +13 099 | -4 605 | +1 352 | 5,067 | +0,027 ± 0,004 | 595,1 |
| `espera_e` | 22 046 | 7 086 | +490 ± 49 | 11 659 (+468 ± 103) | +13 549 | -4 744 | +1 549 | 5,301 | +0,261 ± 0,016 | 528,2 |
| `fondo_rec` | 21 840 | 6 559 | +284 ± 25 | 11 162 (-28 ± 71) | +13 343 | -4 593 | +1 442 | 5,074 | +0,033 ± 0,008 | 589,5 |
| `fondo_min` | 21 852 | 6 492 | +296 ± 50 | 11 139 (-52 ± 93) | +13 354 | -4 418 | +1 561 | 5,030 | -0,010 ± 0,015 | 643,9 |
| `fondo_ancla` | 18 329 | 6 006 | -3 227 ± 63 | 10 113 (-1 078 ± 101) | +9 832 | -4 035 | +980 | 3,970 | -1,070 ± 0,025 | 408,3 |
| `rec_e` | 21 944 | 6 586 | +388 ± 26 | 11 226 (+35 ± 69) | +13 447 | -4 549 | +1 508 | 5,097 | +0,057 ± 0,008 | 569,4 |
| `min_e` | 21 993 | 6 526 | +437 ± 50 | 11 218 (+28 ± 95) | +13 495 | -4 377 | +1 653 | 5,060 | +0,020 ± 0,015 | 619,6 |
| `completo` | 21 905 | 6 649 | +349 ± 25 | 11 223 (+32 ± 70) | +13 408 | -4 563 | +1 509 | 5,101 | +0,060 ± 0,007 | 571,7 |
| `completo_s` | 21 816 | 6 621 | +260 ± 25 | 11 171 (-20 ± 72) | +13 319 | -4 594 | +1 435 | 5,079 | +0,039 ± 0,007 | 590,3 |
| `completo_esp` | 21 906 | 6 690 | +350 ± 24 | 11 220 (+30 ± 73) | +13 409 | -4 683 | +1 386 | 5,133 | +0,093 ± 0,008 | 577,1 |
| `completo_ap` | 21 914 | 6 637 | +358 ± 35 | 11 180 (-11 ± 88) | +13 417 | -4 523 | +1 512 | 5,081 | +0,040 ± 0,008 | 613,2 |
| `completo_ancla` | 18 272 | 6 022 | -3 284 ± 64 | 10 094 (-1 097 ± 104) | +9 775 | -4 107 | +949 | 3,962 | -1,079 ± 0,025 | 411,5 |
| `completo_min` | 21 845 | 6 700 | +289 ± 38 | 11 277 (+86 ± 76) | +13 348 | -4 403 | +1 595 | 5,058 | +0,017 ± 0,010 | 599,9 |

### 2000 ticks, conjunto estres (7000 series)

| Candidata | H1: media | H1: p5 | H1: dif. contra `max_media` | H1: p5 de 3 rondas (dif.) | H2: exceso medio | H2: p5 del exceso | H2: p5 de 3 rondas | H2: W/B&H media | H2: W/B&H dif. | Órdenes |
|---|---|---|---|---|---|---|---|---|---|---|
| `max_media` | 13 174 | 5 323 | +0 ± 0 | 7 678 (+0 ± 0) | +2 417 | -10 143 | -5 452 | 2,309 | +0,000 ± 0,000 | 94,6 |
| `base` | 12 691 | 5 733 | -483 ± 50 | 7 765 (+87 ± 75) | +1 935 | -10 433 | -5 769 | 2,220 | -0,089 ± 0,026 | 67,7 |
| `kalman` | 13 154 | 5 370 | -20 ± 25 | 7 662 (-16 ± 53) | +2 398 | -10 167 | -5 494 | 2,306 | -0,003 ± 0,019 | 93,3 |
| `ejec_a` | 13 197 | 5 388 | +23 ± 1 | 7 700 (+22 ± 16) | +2 440 | -10 143 | -5 426 | 2,316 | +0,007 ± 0,001 | 90,3 |
| `ejec_b` | 13 212 | 5 393 | +38 ± 4 | 7 715 (+37 ± 23) | +2 455 | -10 168 | -5 432 | 2,325 | +0,015 ± 0,005 | 87,8 |
| `espera` | 12 850 | 5 427 | -324 ± 43 | 7 681 (+3 ± 52) | +2 094 | -10 338 | -5 573 | 2,230 | -0,080 ± 0,036 | 85,1 |
| `aprendiz` | 13 186 | 5 458 | +12 ± 7 | 7 727 (+48 ± 41) | +2 429 | -10 136 | -5 434 | 2,314 | +0,004 ± 0,010 | 94,8 |
| `aprendiz_patron` | 13 165 | 5 362 | -9 ± 4 | 7 682 (+4 ± 22) | +2 409 | -10 159 | -5 458 | 2,308 | -0,001 ± 0,001 | 94,5 |
| `espera_e` | 12 870 | 5 479 | -304 ± 43 | 7 709 (+30 ± 52) | +2 113 | -10 324 | -5 554 | 2,235 | -0,074 ± 0,036 | 81,2 |
| `fondo_rec` | 13 435 | 5 344 | +261 ± 27 | 7 680 (+2 ± 44) | +2 678 | -9 994 | -5 338 | 2,385 | +0,076 ± 0,013 | 94,4 |
| `fondo_min` | 13 201 | 5 326 | +27 ± 9 | 7 681 (+3 ± 18) | +2 444 | -10 143 | -5 446 | 2,308 | -0,001 ± 0,004 | 95,3 |
| `fondo_ancla` | 13 552 | 5 539 | +378 ± 59 | 7 890 (+211 ± 59) | +2 796 | -8 968 | -4 830 | 2,253 | -0,056 ± 0,038 | 75,8 |
| `rec_e` | 13 454 | 5 372 | +280 ± 27 | 7 702 (+23 ± 45) | +2 697 | -9 964 | -5 326 | 2,391 | +0,082 ± 0,013 | 91,2 |
| `min_e` | 13 224 | 5 392 | +50 ± 9 | 7 707 (+29 ± 21) | +2 467 | -10 143 | -5 419 | 2,315 | +0,006 ± 0,005 | 91,0 |
| `completo` | 13 421 | 5 407 | +247 ± 24 | 7 708 (+30 ± 40) | +2 664 | -9 992 | -5 353 | 2,383 | +0,074 ± 0,012 | 91,2 |
| `completo_s` | 13 402 | 5 367 | +228 ± 23 | 7 686 (+8 ± 41) | +2 645 | -9 979 | -5 359 | 2,376 | +0,066 ± 0,011 | 94,3 |
| `completo_esp` | 13 393 | 5 353 | +219 ± 24 | 7 692 (+14 ± 41) | +2 637 | -10 066 | -5 399 | 2,382 | +0,073 ± 0,013 | 93,3 |
| `completo_ap` | 13 462 | 5 393 | +288 ± 27 | 7 719 (+41 ± 42) | +2 705 | -9 947 | -5 328 | 2,383 | +0,074 ± 0,011 | 93,4 |
| `completo_ancla` | 13 569 | 5 544 | +395 ± 59 | 7 908 (+229 ± 60) | +2 812 | -8 968 | -4 810 | 2,263 | -0,046 ± 0,036 | 75,2 |
| `completo_min` | 13 197 | 5 423 | +23 ± 4 | 7 725 (+47 ± 32) | +2 440 | -10 143 | -5 443 | 2,314 | +0,005 ± 0,007 | 90,3 |

### 20 000 ticks, interiores, conjunto estres (602 series)

| Candidata | H1: media | H1: p5 | H1: dif. contra `max_media` | H1: p5 de 3 rondas (dif.) | H2: exceso medio | H2: p5 del exceso | H2: p5 de 3 rondas | H2: W/B&H media | H2: W/B&H dif. | Órdenes |
|---|---|---|---|---|---|---|---|---|---|---|
| `max_media` | 51 265 | 5 976 | +0 ± 0 | 14 166 (+0 ± 0) | +39 993 | -7 804 | +1 530 | 5,041 | +0,000 ± 0,000 | 716,4 |
| `base` | 34 847 | 6 799 | -16 418 ± 1 016 | 11 876 (-2 290 ± 980) | +23 576 | -7 290 | -315 | 3,426 | -1,615 ± 0,101 | 370,2 |
| `kalman` | 51 208 | 6 049 | -57 ± 225 | 13 720 (-446 ± 500) | +39 936 | -8 057 | +1 483 | 5,028 | -0,012 ± 0,022 | 718,9 |
| `ejec_a` | 51 325 | 6 154 | +60 ± 7 | 14 240 (+74 ± 55) | +40 054 | -7 795 | +1 631 | 5,047 | +0,006 ± 0,001 | 694,9 |
| `ejec_b` | 51 152 | 6 232 | -112 ± 21 | 14 181 (+15 ± 109) | +39 881 | -7 757 | +1 646 | 5,030 | -0,011 ± 0,002 | 671,4 |
| `espera` | 43 497 | 5 793 | -7 768 ± 596 | 13 317 (-849 ± 576) | +32 225 | -7 825 | +980 | 4,281 | -0,760 ± 0,055 | 597,5 |
| `aprendiz` | 85 679 | 6 177 | +34 414 ± 2 072 | 17 553 (+3 387 ± 2 019) | +74 408 | -8 148 | +5 691 | 8,484 | +3,444 ± 0,208 | 1626,6 |
| `aprendiz_patron` | 50 259 | 5 994 | -1 006 ± 115 | 14 068 (-98 ± 239) | +38 988 | -7 869 | +1 508 | 4,944 | -0,097 ± 0,010 | 707,2 |
| `espera_e` | 43 549 | 5 937 | -7 716 ± 597 | 13 422 (-744 ± 582) | +32 277 | -7 505 | +1 048 | 4,286 | -0,755 ± 0,056 | 578,4 |
| `fondo_rec` | 55 118 | 5 969 | +3 853 ± 338 | 14 223 (+57 ± 356) | +43 846 | -8 051 | +1 985 | 5,418 | +0,377 ± 0,033 | 732,9 |
| `fondo_min` | 94 600 | 5 759 | +43 335 ± 2 320 | 19 870 (+5 704 ± 2 423) | +83 328 | -7 679 | +7 868 | 9,366 | +4,325 ± 0,233 | 1504,6 |
| `fondo_ancla` | 39 099 | 6 813 | -12 166 ± 813 | 13 159 (-1 007 ± 650) | +27 828 | -6 306 | +1 150 | 3,819 | -1,222 ± 0,081 | 493,4 |
| `rec_e` | 55 172 | 5 998 | +3 907 ± 341 | 14 285 (+119 ± 366) | +43 900 | -8 037 | +2 071 | 5,423 | +0,382 ± 0,033 | 715,1 |
| `min_e` | 94 707 | 5 959 | +43 442 ± 2 318 | 20 012 (+5 846 ± 2 419) | +83 436 | -7 537 | +7 999 | 9,377 | +4,336 ± 0,233 | 1474,9 |
| `completo` | 65 253 | 5 968 | +13 988 ± 973 | 15 463 (+1 297 ± 837) | +53 982 | -7 940 | +3 411 | 6,437 | +1,396 ± 0,098 | 901,0 |
| `completo_s` | 65 236 | 5 936 | +13 971 ± 975 | 15 412 (+1 246 ± 846) | +53 965 | -8 115 | +3 357 | 6,436 | +1,395 ± 0,098 | 917,9 |
| `completo_esp` | 53 154 | 5 818 | +1 889 ± 236 | 13 944 (-223 ± 324) | +41 883 | -8 143 | +1 567 | 5,228 | +0,187 ± 0,024 | 708,2 |
| `completo_ap` | 82 097 | 5 936 | +30 832 ± 1 883 | 18 028 (+3 862 ± 1 639) | +70 826 | -7 927 | +6 217 | 8,118 | +3,077 ± 0,189 | 1264,1 |
| `completo_ancla` | 39 916 | 6 842 | -11 349 ± 769 | 13 304 (-862 ± 645) | +28 644 | -6 343 | +1 051 | 3,901 | -1,140 ± 0,077 | 520,7 |
| `completo_min` | 94 179 | 6 067 | +42 914 ± 2 348 | 19 607 (+5 440 ± 2 518) | +82 907 | -7 797 | +7 381 | 9,339 | +4,298 ± 0,236 | 1528,2 |

### 20 000 ticks, parada, conjunto estres (2800 series)

| Candidata | H1: media | H1: p5 | H1: dif. contra `max_media` | H1: p5 de 3 rondas (dif.) | H2: exceso medio | H2: p5 del exceso | H2: p5 de 3 rondas | H2: W/B&H media | H2: W/B&H dif. | Órdenes |
|---|---|---|---|---|---|---|---|---|---|---|
| `max_media` | 21 807 | 2 520 | +0 ± 0 | 5 998 (+0 ± 0) | +8 353 | -18 625 | -28 448 | 3,801 | +0,000 ± 0,000 | 346,9 |
| `base` | 18 178 | 2 996 | -3 629 ± 267 | 6 337 (+339 ± 132) | +4 723 | -19 241 | -28 629 | 3,603 | -0,198 ± 0,041 | 222,9 |
| `kalman` | 21 827 | 2 588 | +20 ± 98 | 5 967 (-31 ± 109) | +8 373 | -19 306 | -28 434 | 3,793 | -0,008 ± 0,026 | 345,4 |
| `ejec_a` | 21 861 | 2 577 | +54 ± 5 | 6 039 (+41 ± 23) | +8 407 | -18 635 | -28 426 | 3,819 | +0,018 ± 0,002 | 334,0 |
| `ejec_b` | 21 848 | 2 573 | +41 ± 9 | 6 074 (+76 ± 39) | +8 394 | -18 640 | -28 436 | 3,828 | +0,028 ± 0,004 | 323,9 |
| `espera` | 20 144 | 2 741 | -1 663 ± 176 | 6 079 (+82 ± 101) | +6 690 | -18 819 | -28 512 | 3,752 | -0,049 ± 0,034 | 303,7 |
| `aprendiz` | 29 253 | 2 932 | +7 446 ± 521 | 6 184 (+186 ± 116) | +15 799 | -17 992 | -28 308 | 4,618 | +0,817 ± 0,057 | 542,3 |
| `aprendiz_patron` | 21 594 | 2 518 | -213 ± 32 | 5 989 (-9 ± 52) | +8 140 | -18 629 | -28 461 | 3,799 | -0,002 ± 0,010 | 344,1 |
| `espera_e` | 20 187 | 2 787 | -1 620 ± 175 | 6 113 (+115 ± 101) | +6 732 | -18 799 | -28 471 | 3,764 | -0,036 ± 0,034 | 292,1 |
| `fondo_rec` | 22 605 | 2 530 | +798 ± 101 | 5 930 (-67 ± 77) | +9 150 | -19 091 | -28 450 | 3,822 | +0,021 ± 0,026 | 350,3 |
| `fondo_min` | 31 145 | 2 612 | +9 338 ± 602 | 5 960 (-37 ± 90) | +17 690 | -19 083 | -28 355 | 4,692 | +0,891 ± 0,063 | 522,7 |
| `fondo_ancla` | 18 498 | 2 530 | -3 309 ± 239 | 5 971 (-26 ± 142) | +5 044 | -16 935 | -27 492 | 3,042 | -0,759 ± 0,074 | 254,6 |
| `rec_e` | 22 648 | 2 555 | +841 ± 100 | 5 961 (-37 ± 79) | +9 193 | -19 094 | -28 420 | 3,836 | +0,035 ± 0,025 | 339,8 |
| `min_e` | 31 210 | 2 634 | +9 403 ± 602 | 6 006 (+9 ± 90) | +17 755 | -19 049 | -28 321 | 4,711 | +0,910 ± 0,063 | 507,9 |
| `completo` | 24 852 | 2 602 | +3 045 ± 240 | 6 009 (+12 ± 76) | +11 397 | -18 593 | -28 401 | 4,088 | +0,287 ± 0,030 | 380,7 |
| `completo_s` | 24 821 | 2 578 | +3 014 ± 240 | 5 986 (-12 ± 77) | +11 367 | -18 666 | -28 426 | 4,077 | +0,276 ± 0,030 | 390,6 |
| `completo_esp` | 22 212 | 2 521 | +405 ± 74 | 5 944 (-53 ± 84) | +8 758 | -19 018 | -28 493 | 3,834 | +0,033 ± 0,020 | 342,8 |
| `completo_ap` | 28 468 | 2 638 | +6 661 ± 473 | 6 018 (+20 ± 82) | +15 013 | -18 336 | -28 359 | 4,447 | +0,646 ± 0,051 | 468,7 |
| `completo_ancla` | 18 669 | 2 569 | -3 138 ± 231 | 5 971 (-27 ± 139) | +5 215 | -16 982 | -27 583 | 3,067 | -0,734 ± 0,073 | 261,3 |
| `completo_min` | 31 111 | 2 683 | +9 304 ± 605 | 6 109 (+111 ± 98) | +17 657 | -18 456 | -28 368 | 4,764 | +0,963 ± 0,062 | 515,8 |

## 3. H3a y H3b (torneo): puntos esperados por campo

Cada celda: media de los puntos, percentil 5 de una ronda (diferencia de la media contra `max_media` ± error). El campo fuerte sale de la tabla de sensibilidad del arnés, que no trae el percentil 5 de una ronda. El de la competencia de tres rondas está en la sección 4 para los cuatro campos.

### H3a, lineal en patrimonio. 2000 ticks, conjunto evidencia

| Candidata | mixto | fuerte | racional | reversores |
|---|---|---|---|---|
| `max_media` | 1,503, p5 0,20 (+0,000 ± 0,000) | 1,423 (+0,000 ± 0,000) | 1,208, p5 0,20 (+0,000 ± 0,000) | 1,062, p5 0,00 (+0,000 ± 0,000) |
| `base` | 1,465, p5 0,18 (-0,038 ± 0,003) | 1,362 (-0,061 ± 0,005) | 1,114, p5 0,11 (-0,094 ± 0,006) | 0,879, p5 0,00 (-0,183 ± 0,013) |
| `kalman` | 1,499, p5 0,22 (-0,005 ± 0,002) | 1,416 (-0,007 ± 0,002) | 1,212, p5 0,20 (+0,004 ± 0,003) | 1,069, p5 0,00 (+0,007 ± 0,007) |
| `ejec_a` | 1,511, p5 0,21 (+0,007 ± 0,000) | 1,434 (+0,010 ± 0,000) | 1,222, p5 0,22 (+0,015 ± 0,000) | 1,096, p5 0,00 (+0,034 ± 0,001) |
| `ejec_b` | 1,515, p5 0,22 (+0,012 ± 0,000) | 1,439 (+0,016 ± 0,001) | 1,231, p5 0,25 (+0,024 ± 0,001) | 1,114, p5 0,00 (+0,051 ± 0,002) |
| `espera` | 1,509, p5 0,23 (+0,005 ± 0,002) | 1,425 (+0,002 ± 0,003) | 1,230, p5 0,23 (+0,022 ± 0,004) | 1,083, p5 0,00 (+0,021 ± 0,008) |
| `aprendiz` | 1,503, p5 0,20 (-0,000 ± 0,000) | 1,423 (-0,000 ± 0,000) | 1,208, p5 0,20 (+0,000 ± 0,000) | 1,061, p5 0,00 (-0,001 ± 0,001) |
| `aprendiz_patron` | 1,502, p5 0,20 (-0,001 ± 0,000) | 1,421 (-0,002 ± 0,001) | 1,207, p5 0,20 (-0,000 ± 0,001) | 1,061, p5 0,00 (-0,001 ± 0,002) |
| `espera_e` | 1,515, p5 0,24 (+0,012 ± 0,002) | 1,434 (+0,011 ± 0,003) | 1,242, p5 0,25 (+0,034 ± 0,004) | 1,104, p5 0,00 (+0,042 ± 0,008) |
| `fondo_rec` | 1,500, p5 0,21 (-0,004 ± 0,001) | 1,417 (-0,006 ± 0,001) | 1,209, p5 0,24 (+0,002 ± 0,002) | 1,061, p5 0,00 (-0,001 ± 0,004) |
| `fondo_min` | 1,503, p5 0,20 (+0,000 ± 0,000) | 1,423 (+0,000 ± 0,000) | 1,208, p5 0,20 (+0,001 ± 0,000) | 1,063, p5 0,00 (+0,000 ± 0,001) |
| `fondo_ancla` | 1,473, p5 0,40 (-0,031 ± 0,002) | 1,365 (-0,058 ± 0,002) | 1,112, p5 0,24 (-0,096 ± 0,003) | 0,877, p5 0,00 (-0,185 ± 0,007) |
| `rec_e` | 1,504, p5 0,22 (+0,001 ± 0,001) | 1,423 (+0,000 ± 0,001) | 1,218, p5 0,25 (+0,011 ± 0,002) | 1,079, p5 0,00 (+0,016 ± 0,004) |
| `min_e` | 1,511, p5 0,21 (+0,008 ± 0,000) | 1,434 (+0,011 ± 0,000) | 1,223, p5 0,22 (+0,016 ± 0,001) | 1,096, p5 0,00 (+0,034 ± 0,002) |
| `completo` | 1,505, p5 0,22 (+0,002 ± 0,001) | 1,424 (+0,001 ± 0,001) | 1,218, p5 0,25 (+0,010 ± 0,001) | 1,081, p5 0,00 (+0,018 ± 0,004) |
| `completo_s` | 1,500, p5 0,21 (-0,003 ± 0,001) | 1,418 (-0,005 ± 0,001) | 1,209, p5 0,23 (+0,001 ± 0,001) | 1,063, p5 0,00 (+0,000 ± 0,004) |
| `completo_esp` | 1,499, p5 0,21 (-0,004 ± 0,001) | 1,415 (-0,008 ± 0,001) | 1,207, p5 0,27 (-0,001 ± 0,002) | 1,053, p5 0,00 (-0,009 ± 0,005) |
| `completo_ap` | 1,503, p5 0,21 (-0,000 ± 0,001) | 1,422 (-0,001 ± 0,001) | 1,215, p5 0,25 (+0,007 ± 0,002) | 1,070, p5 0,00 (+0,008 ± 0,004) |
| `completo_ancla` | 1,472, p5 0,40 (-0,031 ± 0,002) | 1,364 (-0,059 ± 0,002) | 1,111, p5 0,24 (-0,097 ± 0,003) | 0,876, p5 0,00 (-0,187 ± 0,007) |
| `completo_min` | 1,511, p5 0,21 (+0,007 ± 0,000) | 1,433 (+0,010 ± 0,000) | 1,222, p5 0,22 (+0,015 ± 0,000) | 1,096, p5 0,00 (+0,033 ± 0,001) |

### H3b, lineal en el puesto. 2000 ticks, conjunto evidencia

| Candidata | mixto | fuerte | racional | reversores |
|---|---|---|---|---|
| `max_media` | 1,473, p5 0,30 (+0,000 ± 0,000) | 1,247 (+0,000 ± 0,000) | 1,245, p5 0,30 (+0,000 ± 0,000) | 1,041, p5 0,20 (+0,000 ± 0,000) |
| `base` | 1,437, p5 0,30 (-0,036 ± 0,004) | 1,168 (-0,079 ± 0,006) | 1,170, p5 0,30 (-0,075 ± 0,006) | 0,927, p5 0,20 (-0,115 ± 0,009) |
| `kalman` | 1,478, p5 0,40 (+0,004 ± 0,002) | 1,258 (+0,011 ± 0,004) | 1,260, p5 0,20 (+0,015 ± 0,004) | 1,057, p5 0,00 (+0,015 ± 0,006) |
| `ejec_a` | 1,500, p5 0,40 (+0,027 ± 0,001) | 1,328 (+0,081 ± 0,002) | 1,281, p5 0,40 (+0,036 ± 0,001) | 1,172, p5 0,20 (+0,131 ± 0,003) |
| `ejec_b` | 1,504, p5 0,40 (+0,031 ± 0,001) | 1,328 (+0,081 ± 0,002) | 1,291, p5 0,40 (+0,046 ± 0,001) | 1,170, p5 0,20 (+0,128 ± 0,004) |
| `espera` | 1,490, p5 0,40 (+0,017 ± 0,003) | 1,271 (+0,024 ± 0,005) | 1,281, p5 0,20 (+0,036 ± 0,004) | 1,075, p5 0,00 (+0,034 ± 0,007) |
| `aprendiz` | 1,474, p5 0,30 (+0,000 ± 0,000) | 1,247 (-0,000 ± 0,001) | 1,245, p5 0,30 (+0,000 ± 0,000) | 1,041, p5 0,20 (-0,000 ± 0,001) |
| `aprendiz_patron` | 1,472, p5 0,30 (-0,001 ± 0,001) | 1,244 (-0,003 ± 0,002) | 1,247, p5 0,20 (+0,002 ± 0,001) | 1,036, p5 0,00 (-0,005 ± 0,003) |
| `espera_e` | 1,499, p5 0,40 (+0,025 ± 0,003) | 1,286 (+0,039 ± 0,005) | 1,294, p5 0,40 (+0,049 ± 0,004) | 1,095, p5 0,00 (+0,054 ± 0,007) |
| `fondo_rec` | 1,479, p5 0,40 (+0,006 ± 0,002) | 1,262 (+0,015 ± 0,003) | 1,254, p5 0,40 (+0,009 ± 0,002) | 1,065, p5 0,00 (+0,024 ± 0,005) |
| `fondo_min` | 1,474, p5 0,30 (+0,000 ± 0,000) | 1,248 (+0,001 ± 0,001) | 1,245, p5 0,30 (+0,000 ± 0,001) | 1,042, p5 0,20 (+0,001 ± 0,001) |
| `fondo_ancla` | 1,453, p5 0,40 (-0,020 ± 0,002) | 1,150 (-0,097 ± 0,004) | 1,159, p5 0,20 (-0,086 ± 0,004) | 0,873, p5 0,00 (-0,168 ± 0,006) |
| `rec_e` | 1,487, p5 0,40 (+0,013 ± 0,002) | 1,276 (+0,029 ± 0,003) | 1,264, p5 0,40 (+0,019 ± 0,002) | 1,086, p5 0,00 (+0,044 ± 0,005) |
| `min_e` | 1,500, p5 0,40 (+0,027 ± 0,001) | 1,327 (+0,080 ± 0,002) | 1,281, p5 0,40 (+0,036 ± 0,001) | 1,171, p5 0,20 (+0,129 ± 0,003) |
| `completo` | 1,487, p5 0,40 (+0,013 ± 0,001) | 1,277 (+0,030 ± 0,003) | 1,266, p5 0,40 (+0,020 ± 0,002) | 1,088, p5 0,00 (+0,046 ± 0,005) |
| `completo_s` | 1,479, p5 0,40 (+0,005 ± 0,001) | 1,260 (+0,013 ± 0,003) | 1,254, p5 0,40 (+0,009 ± 0,002) | 1,063, p5 0,00 (+0,022 ± 0,005) |
| `completo_esp` | 1,477, p5 0,40 (+0,004 ± 0,002) | 1,251 (+0,004 ± 0,003) | 1,252, p5 0,40 (+0,007 ± 0,002) | 1,047, p5 0,00 (+0,005 ± 0,005) |
| `completo_ap` | 1,483, p5 0,40 (+0,010 ± 0,002) | 1,265 (+0,018 ± 0,003) | 1,259, p5 0,40 (+0,013 ± 0,002) | 1,068, p5 0,00 (+0,027 ± 0,005) |
| `completo_ancla` | 1,453, p5 0,40 (-0,020 ± 0,002) | 1,149 (-0,098 ± 0,004) | 1,158, p5 0,20 (-0,087 ± 0,004) | 0,871, p5 0,00 (-0,170 ± 0,006) |
| `completo_min` | 1,500, p5 0,40 (+0,026 ± 0,001) | 1,327 (+0,080 ± 0,002) | 1,281, p5 0,40 (+0,036 ± 0,001) | 1,170, p5 0,20 (+0,129 ± 0,003) |

### H3a, lineal en patrimonio. 20 000 ticks, interiores, conjunto evidencia

| Candidata | mixto | fuerte | racional | reversores |
|---|---|---|---|---|
| `max_media` | 1,855, p5 1,24 (+0,000 ± 0,000) | 1,740 (+0,000 ± 0,000) | 1,500, p5 0,67 (+0,000 ± 0,000) | 1,250, p5 0,00 (+0,000 ± 0,000) |
| `base` | 1,730, p5 1,06 (-0,125 ± 0,004) | 1,535 (-0,205 ± 0,006) | 1,268, p5 0,44 (-0,231 ± 0,007) | 0,657, p5 0,00 (-0,593 ± 0,018) |
| `kalman` | 1,841, p5 1,25 (-0,014 ± 0,002) | 1,724 (-0,016 ± 0,003) | 1,511, p5 0,67 (+0,012 ± 0,003) | 1,245, p5 0,00 (-0,006 ± 0,010) |
| `ejec_a` | 1,861, p5 1,25 (+0,007 ± 0,000) | 1,751 (+0,011 ± 0,000) | 1,517, p5 0,70 (+0,018 ± 0,000) | 1,300, p5 0,03 (+0,049 ± 0,002) |
| `ejec_b` | 1,865, p5 1,27 (+0,010 ± 0,000) | 1,758 (+0,018 ± 0,001) | 1,529, p5 0,71 (+0,029 ± 0,001) | 1,330, p5 0,07 (+0,079 ± 0,003) |
| `espera` | 1,834, p5 1,21 (-0,021 ± 0,002) | 1,716 (-0,024 ± 0,004) | 1,514, p5 0,64 (+0,014 ± 0,004) | 1,239, p5 0,00 (-0,012 ± 0,012) |
| `aprendiz` | 1,826, p5 1,22 (-0,028 ± 0,002) | 1,698 (-0,042 ± 0,003) | 1,469, p5 0,64 (-0,031 ± 0,003) | 1,156, p5 0,00 (-0,095 ± 0,008) |
| `aprendiz_patron` | 1,846, p5 1,23 (-0,008 ± 0,001) | 1,728 (-0,011 ± 0,001) | 1,499, p5 0,67 (-0,001 ± 0,001) | 1,234, p5 0,00 (-0,017 ± 0,005) |
| `espera_e` | 1,841, p5 1,23 (-0,014 ± 0,002) | 1,727 (-0,013 ± 0,004) | 1,528, p5 0,66 (+0,029 ± 0,004) | 1,271, p5 0,00 (+0,021 ± 0,012) |
| `fondo_rec` | 1,854, p5 1,28 (-0,000 ± 0,001) | 1,741 (+0,002 ± 0,002) | 1,522, p5 0,72 (+0,023 ± 0,002) | 1,279, p5 0,00 (+0,029 ± 0,007) |
| `fondo_min` | 1,836, p5 1,24 (-0,018 ± 0,002) | 1,720 (-0,020 ± 0,003) | 1,511, p5 0,66 (+0,011 ± 0,004) | 1,222, p5 0,00 (-0,029 ± 0,010) |
| `fondo_ancla` | 1,719, p5 1,14 (-0,135 ± 0,002) | 1,527 (-0,213 ± 0,003) | 1,261, p5 0,56 (-0,238 ± 0,004) | 0,674, p5 0,00 (-0,577 ± 0,011) |
| `rec_e` | 1,860, p5 1,30 (+0,006 ± 0,001) | 1,751 (+0,011 ± 0,002) | 1,536, p5 0,75 (+0,036 ± 0,002) | 1,313, p5 0,00 (+0,063 ± 0,007) |
| `min_e` | 1,845, p5 1,25 (-0,010 ± 0,002) | 1,734 (-0,006 ± 0,003) | 1,531, p5 0,69 (+0,031 ± 0,004) | 1,266, p5 0,00 (+0,016 ± 0,010) |
| `completo` | 1,857, p5 1,29 (+0,003 ± 0,001) | 1,746 (+0,006 ± 0,002) | 1,527, p5 0,73 (+0,028 ± 0,002) | 1,294, p5 0,00 (+0,044 ± 0,007) |
| `completo_s` | 1,852, p5 1,28 (-0,003 ± 0,001) | 1,737 (-0,003 ± 0,002) | 1,515, p5 0,71 (+0,016 ± 0,002) | 1,265, p5 0,00 (+0,015 ± 0,007) |
| `completo_esp` | 1,855, p5 1,28 (+0,000 ± 0,001) | 1,742 (+0,003 ± 0,002) | 1,524, p5 0,72 (+0,024 ± 0,002) | 1,286, p5 0,00 (+0,036 ± 0,007) |
| `completo_ap` | 1,849, p5 1,28 (-0,006 ± 0,001) | 1,735 (-0,004 ± 0,002) | 1,523, p5 0,73 (+0,023 ± 0,003) | 1,256, p5 0,00 (+0,006 ± 0,009) |
| `completo_ancla` | 1,714, p5 1,13 (-0,141 ± 0,002) | 1,518 (-0,221 ± 0,003) | 1,251, p5 0,55 (-0,249 ± 0,004) | 0,653, p5 0,00 (-0,598 ± 0,011) |
| `completo_min` | 1,850, p5 1,26 (-0,005 ± 0,002) | 1,739 (-0,001 ± 0,003) | 1,526, p5 0,69 (+0,026 ± 0,004) | 1,274, p5 0,00 (+0,023 ± 0,008) |

### H3b, lineal en el puesto. 20 000 ticks, interiores, conjunto evidencia

| Candidata | mixto | fuerte | racional | reversores |
|---|---|---|---|---|
| `max_media` | 1,821, p5 1,40 (+0,000 ± 0,000) | 1,479 (+0,000 ± 0,000) | 1,514, p5 0,70 (+0,000 ± 0,000) | 1,169, p5 0,30 (+0,000 ± 0,000) |
| `base` | 1,742, p5 1,20 (-0,079 ± 0,003) | 1,241 (-0,238 ± 0,008) | 1,311, p5 0,50 (-0,204 ± 0,007) | 0,785, p5 0,10 (-0,384 ± 0,012) |
| `kalman` | 1,832, p5 1,40 (+0,011 ± 0,002) | 1,517 (+0,037 ± 0,006) | 1,540, p5 0,80 (+0,026 ± 0,004) | 1,229, p5 0,00 (+0,060 ± 0,009) |
| `ejec_a` | 1,871, p5 1,40 (+0,050 ± 0,001) | 1,654 (+0,174 ± 0,002) | 1,569, p5 0,80 (+0,054 ± 0,001) | 1,460, p5 0,40 (+0,291 ± 0,004) |
| `ejec_b` | 1,862, p5 1,40 (+0,041 ± 0,001) | 1,618 (+0,139 ± 0,003) | 1,572, p5 0,80 (+0,057 ± 0,002) | 1,396, p5 0,40 (+0,227 ± 0,005) |
| `espera` | 1,830, p5 1,40 (+0,009 ± 0,002) | 1,514 (+0,034 ± 0,006) | 1,543, p5 0,60 (+0,029 ± 0,005) | 1,229, p5 0,00 (+0,060 ± 0,010) |
| `aprendiz` | 1,811, p5 1,40 (-0,010 ± 0,002) | 1,445 (-0,034 ± 0,005) | 1,489, p5 0,60 (-0,025 ± 0,004) | 1,114, p5 0,00 (-0,055 ± 0,008) |
| `aprendiz_patron` | 1,821, p5 1,40 (-0,000 ± 0,001) | 1,480 (+0,001 ± 0,004) | 1,517, p5 0,80 (+0,003 ± 0,002) | 1,170, p5 0,00 (+0,001 ± 0,007) |
| `espera_e` | 1,838, p5 1,40 (+0,016 ± 0,002) | 1,534 (+0,055 ± 0,006) | 1,559, p5 0,60 (+0,045 ± 0,005) | 1,261, p5 0,00 (+0,092 ± 0,010) |
| `fondo_rec` | 1,838, p5 1,40 (+0,016 ± 0,002) | 1,533 (+0,053 ± 0,005) | 1,545, p5 0,80 (+0,031 ± 0,003) | 1,255, p5 0,00 (+0,086 ± 0,008) |
| `fondo_min` | 1,818, p5 1,40 (-0,003 ± 0,002) | 1,468 (-0,011 ± 0,005) | 1,521, p5 0,60 (+0,007 ± 0,004) | 1,151, p5 0,00 (-0,018 ± 0,009) |
| `fondo_ancla` | 1,745, p5 1,20 (-0,076 ± 0,002) | 1,192 (-0,287 ± 0,005) | 1,310, p5 0,60 (-0,204 ± 0,004) | 0,689, p5 0,00 (-0,480 ± 0,009) |
| `rec_e` | 1,845, p5 1,40 (+0,024 ± 0,002) | 1,556 (+0,077 ± 0,005) | 1,561, p5 0,80 (+0,047 ± 0,003) | 1,294, p5 0,00 (+0,125 ± 0,008) |
| `min_e` | 1,841, p5 1,40 (+0,019 ± 0,002) | 1,539 (+0,060 ± 0,006) | 1,553, p5 0,80 (+0,039 ± 0,004) | 1,267, p5 0,00 (+0,098 ± 0,009) |
| `completo` | 1,840, p5 1,40 (+0,019 ± 0,002) | 1,541 (+0,062 ± 0,005) | 1,550, p5 0,80 (+0,036 ± 0,003) | 1,270, p5 0,00 (+0,101 ± 0,008) |
| `completo_s` | 1,834, p5 1,40 (+0,012 ± 0,002) | 1,520 (+0,041 ± 0,005) | 1,537, p5 0,80 (+0,023 ± 0,003) | 1,236, p5 0,00 (+0,067 ± 0,008) |
| `completo_esp` | 1,837, p5 1,40 (+0,016 ± 0,002) | 1,534 (+0,054 ± 0,005) | 1,547, p5 0,80 (+0,033 ± 0,003) | 1,259, p5 0,00 (+0,090 ± 0,008) |
| `completo_ap` | 1,828, p5 1,40 (+0,007 ± 0,002) | 1,501 (+0,021 ± 0,005) | 1,539, p5 0,80 (+0,025 ± 0,004) | 1,202, p5 0,00 (+0,033 ± 0,009) |
| `completo_ancla` | 1,741, p5 1,20 (-0,080 ± 0,002) | 1,183 (-0,297 ± 0,005) | 1,300, p5 0,60 (-0,215 ± 0,004) | 0,675, p5 0,00 (-0,495 ± 0,009) |
| `completo_min` | 1,840, p5 1,40 (+0,019 ± 0,002) | 1,538 (+0,059 ± 0,005) | 1,550, p5 0,80 (+0,036 ± 0,004) | 1,266, p5 0,00 (+0,097 ± 0,008) |

### H3a, lineal en patrimonio. 20 000 ticks, parada, conjunto evidencia

| Candidata | mixto | fuerte | racional | reversores |
|---|---|---|---|---|
| `max_media` | 1,721, p5 0,75 (+0,000 ± 0,000) | 1,631 (+0,000 ± 0,000) | 1,404, p5 0,48 (+0,000 ± 0,000) | 1,212, p5 0,00 (+0,000 ± 0,000) |
| `base` | 1,647, p5 0,70 (-0,074 ± 0,003) | 1,511 (-0,120 ± 0,005) | 1,262, p5 0,39 (-0,141 ± 0,005) | 0,842, p5 0,00 (-0,369 ± 0,014) |
| `kalman` | 1,710, p5 0,75 (-0,011 ± 0,001) | 1,616 (-0,015 ± 0,002) | 1,412, p5 0,48 (+0,008 ± 0,003) | 1,201, p5 0,00 (-0,011 ± 0,007) |
| `ejec_a` | 1,728, p5 0,76 (+0,007 ± 0,000) | 1,642 (+0,010 ± 0,000) | 1,419, p5 0,49 (+0,016 ± 0,000) | 1,254, p5 0,02 (+0,043 ± 0,001) |
| `ejec_b` | 1,732, p5 0,77 (+0,011 ± 0,000) | 1,648 (+0,016 ± 0,000) | 1,429, p5 0,51 (+0,026 ± 0,000) | 1,279, p5 0,04 (+0,067 ± 0,002) |
| `espera` | 1,721, p5 0,76 (-0,000 ± 0,002) | 1,633 (+0,001 ± 0,003) | 1,442, p5 0,49 (+0,038 ± 0,003) | 1,249, p5 0,00 (+0,037 ± 0,008) |
| `aprendiz` | 1,706, p5 0,75 (-0,016 ± 0,001) | 1,608 (-0,024 ± 0,002) | 1,392, p5 0,48 (-0,012 ± 0,002) | 1,158, p5 0,00 (-0,053 ± 0,005) |
| `aprendiz_patron` | 1,717, p5 0,74 (-0,004 ± 0,001) | 1,625 (-0,007 ± 0,001) | 1,406, p5 0,48 (+0,002 ± 0,001) | 1,201, p5 0,00 (-0,011 ± 0,003) |
| `espera_e` | 1,728, p5 0,77 (+0,006 ± 0,002) | 1,643 (+0,011 ± 0,003) | 1,455, p5 0,51 (+0,051 ± 0,003) | 1,277, p5 0,00 (+0,065 ± 0,008) |
| `fondo_rec` | 1,713, p5 0,74 (-0,008 ± 0,001) | 1,620 (-0,011 ± 0,001) | 1,410, p5 0,49 (+0,006 ± 0,002) | 1,211, p5 0,00 (-0,001 ± 0,005) |
| `fondo_min` | 1,702, p5 0,73 (-0,019 ± 0,002) | 1,609 (-0,022 ± 0,002) | 1,402, p5 0,44 (-0,002 ± 0,003) | 1,174, p5 0,00 (-0,037 ± 0,006) |
| `fondo_ancla` | 1,564, p5 0,75 (-0,157 ± 0,002) | 1,400 (-0,231 ± 0,003) | 1,141, p5 0,30 (-0,263 ± 0,004) | 0,669, p5 0,00 (-0,543 ± 0,008) |
| `rec_e` | 1,719, p5 0,74 (-0,003 ± 0,001) | 1,629 (-0,002 ± 0,001) | 1,421, p5 0,50 (+0,017 ± 0,002) | 1,239, p5 0,00 (+0,028 ± 0,005) |
| `min_e` | 1,710, p5 0,74 (-0,011 ± 0,002) | 1,621 (-0,010 ± 0,002) | 1,419, p5 0,45 (+0,015 ± 0,003) | 1,213, p5 0,00 (+0,001 ± 0,006) |
| `completo` | 1,720, p5 0,75 (-0,002 ± 0,001) | 1,630 (-0,001 ± 0,001) | 1,420, p5 0,51 (+0,017 ± 0,001) | 1,235, p5 0,00 (+0,023 ± 0,005) |
| `completo_s` | 1,715, p5 0,74 (-0,007 ± 0,001) | 1,622 (-0,009 ± 0,001) | 1,410, p5 0,50 (+0,006 ± 0,001) | 1,209, p5 0,00 (-0,003 ± 0,005) |
| `completo_esp` | 1,717, p5 0,74 (-0,004 ± 0,001) | 1,626 (-0,005 ± 0,001) | 1,416, p5 0,50 (+0,012 ± 0,002) | 1,224, p5 0,00 (+0,013 ± 0,005) |
| `completo_ap` | 1,712, p5 0,74 (-0,010 ± 0,001) | 1,619 (-0,012 ± 0,002) | 1,412, p5 0,49 (+0,009 ± 0,002) | 1,199, p5 0,00 (-0,012 ± 0,006) |
| `completo_ancla` | 1,560, p5 0,75 (-0,161 ± 0,002) | 1,395 (-0,236 ± 0,003) | 1,134, p5 0,30 (-0,270 ± 0,004) | 0,656, p5 0,00 (-0,556 ± 0,008) |
| `completo_min` | 1,719, p5 0,75 (-0,002 ± 0,001) | 1,631 (-0,000 ± 0,002) | 1,424, p5 0,49 (+0,020 ± 0,002) | 1,230, p5 0,00 (+0,019 ± 0,005) |

### H3b, lineal en el puesto. 20 000 ticks, parada, conjunto evidencia

| Candidata | mixto | fuerte | racional | reversores |
|---|---|---|---|---|
| `max_media` | 1,708, p5 0,90 (+0,000 ± 0,000) | 1,406 (+0,000 ± 0,000) | 1,428, p5 0,60 (+0,000 ± 0,000) | 1,137, p5 0,20 (+0,000 ± 0,000) |
| `base` | 1,659, p5 0,80 (-0,049 ± 0,003) | 1,256 (-0,150 ± 0,006) | 1,299, p5 0,50 (-0,128 ± 0,005) | 0,896, p5 0,20 (-0,240 ± 0,009) |
| `kalman` | 1,717, p5 0,80 (+0,009 ± 0,002) | 1,433 (+0,027 ± 0,004) | 1,449, p5 0,60 (+0,021 ± 0,003) | 1,180, p5 0,00 (+0,043 ± 0,007) |
| `ejec_a` | 1,756, p5 1,00 (+0,048 ± 0,001) | 1,569 (+0,163 ± 0,002) | 1,478, p5 0,60 (+0,050 ± 0,001) | 1,407, p5 0,40 (+0,270 ± 0,003) |
| `ejec_b` | 1,750, p5 1,00 (+0,041 ± 0,001) | 1,539 (+0,133 ± 0,002) | 1,482, p5 0,60 (+0,054 ± 0,001) | 1,356, p5 0,40 (+0,219 ± 0,004) |
| `espera` | 1,734, p5 1,00 (+0,025 ± 0,002) | 1,466 (+0,060 ± 0,005) | 1,477, p5 0,60 (+0,049 ± 0,004) | 1,231, p5 0,00 (+0,094 ± 0,008) |
| `aprendiz` | 1,707, p5 0,90 (-0,002 ± 0,001) | 1,396 (-0,010 ± 0,003) | 1,420, p5 0,60 (-0,008 ± 0,003) | 1,118, p5 0,00 (-0,019 ± 0,005) |
| `aprendiz_patron` | 1,710, p5 0,80 (+0,002 ± 0,001) | 1,410 (+0,005 ± 0,003) | 1,433, p5 0,60 (+0,006 ± 0,002) | 1,145, p5 0,00 (+0,008 ± 0,005) |
| `espera_e` | 1,741, p5 1,00 (+0,032 ± 0,002) | 1,484 (+0,078 ± 0,005) | 1,491, p5 0,60 (+0,063 ± 0,004) | 1,259, p5 0,00 (+0,122 ± 0,007) |
| `fondo_rec` | 1,714, p5 0,80 (+0,006 ± 0,001) | 1,430 (+0,024 ± 0,004) | 1,442, p5 0,60 (+0,014 ± 0,002) | 1,179, p5 0,00 (+0,042 ± 0,006) |
| `fondo_min` | 1,703, p5 0,80 (-0,005 ± 0,002) | 1,390 (-0,016 ± 0,004) | 1,424, p5 0,50 (-0,004 ± 0,003) | 1,109, p5 0,00 (-0,028 ± 0,006) |
| `fondo_ancla` | 1,618, p5 0,80 (-0,091 ± 0,002) | 1,132 (-0,274 ± 0,004) | 1,193, p5 0,40 (-0,235 ± 0,004) | 0,691, p5 0,00 (-0,446 ± 0,007) |
| `rec_e` | 1,722, p5 0,80 (+0,014 ± 0,001) | 1,452 (+0,046 ± 0,004) | 1,456, p5 0,60 (+0,029 ± 0,002) | 1,213, p5 0,00 (+0,076 ± 0,006) |
| `min_e` | 1,728, p5 1,00 (+0,019 ± 0,002) | 1,470 (+0,064 ± 0,004) | 1,456, p5 0,60 (+0,029 ± 0,003) | 1,242, p5 0,00 (+0,105 ± 0,006) |
| `completo` | 1,722, p5 0,80 (+0,014 ± 0,001) | 1,449 (+0,043 ± 0,003) | 1,454, p5 0,60 (+0,027 ± 0,002) | 1,208, p5 0,00 (+0,071 ± 0,005) |
| `completo_s` | 1,715, p5 0,80 (+0,007 ± 0,001) | 1,430 (+0,024 ± 0,003) | 1,442, p5 0,60 (+0,014 ± 0,002) | 1,177, p5 0,00 (+0,040 ± 0,005) |
| `completo_esp` | 1,717, p5 0,80 (+0,009 ± 0,001) | 1,438 (+0,032 ± 0,004) | 1,448, p5 0,60 (+0,021 ± 0,002) | 1,191, p5 0,00 (+0,054 ± 0,006) |
| `completo_ap` | 1,710, p5 0,80 (+0,001 ± 0,002) | 1,413 (+0,007 ± 0,004) | 1,439, p5 0,60 (+0,011 ± 0,003) | 1,150, p5 0,00 (+0,014 ± 0,006) |
| `completo_ancla` | 1,615, p5 0,80 (-0,093 ± 0,002) | 1,126 (-0,280 ± 0,004) | 1,186, p5 0,40 (-0,242 ± 0,004) | 0,681, p5 0,00 (-0,455 ± 0,007) |
| `completo_min` | 1,731, p5 1,00 (+0,022 ± 0,001) | 1,477 (+0,071 ± 0,003) | 1,462, p5 0,60 (+0,035 ± 0,002) | 1,251, p5 0,00 (+0,114 ± 0,006) |

### H3a, lineal en patrimonio. 2000 ticks, conjunto estres

| Candidata | mixto | fuerte | racional | reversores |
|---|---|---|---|---|
| `max_media` | 1,177, p5 0,00 (+0,000 ± 0,000) | 1,124 (+0,000 ± 0,000) | 1,016, p5 0,05 (+0,000 ± 0,000) | 0,988, p5 0,00 (+0,000 ± 0,000) |
| `base` | 1,159, p5 0,00 (-0,018 ± 0,004) | 1,082 (-0,042 ± 0,006) | 0,911, p5 0,00 (-0,105 ± 0,007) | 0,844, p5 0,00 (-0,144 ± 0,015) |
| `kalman` | 1,166, p5 0,00 (-0,011 ± 0,002) | 1,110 (-0,013 ± 0,003) | 1,007, p5 0,05 (-0,010 ± 0,003) | 0,974, p5 0,00 (-0,014 ± 0,008) |
| `ejec_a` | 1,183, p5 0,00 (+0,006 ± 0,000) | 1,132 (+0,009 ± 0,000) | 1,028, p5 0,06 (+0,012 ± 0,000) | 1,024, p5 0,00 (+0,035 ± 0,002) |
| `ejec_b` | 1,187, p5 0,00 (+0,010 ± 0,000) | 1,137 (+0,013 ± 0,001) | 1,033, p5 0,08 (+0,017 ± 0,001) | 1,040, p5 0,00 (+0,052 ± 0,002) |
| `espera` | 1,157, p5 0,00 (-0,020 ± 0,002) | 1,092 (-0,032 ± 0,003) | 0,971, p5 0,05 (-0,045 ± 0,004) | 0,911, p5 0,00 (-0,078 ± 0,009) |
| `aprendiz` | 1,180, p5 0,00 (+0,003 ± 0,001) | 1,128 (+0,004 ± 0,001) | 1,022, p5 0,05 (+0,005 ± 0,001) | 1,004, p5 0,00 (+0,016 ± 0,003) |
| `aprendiz_patron` | 1,176, p5 0,00 (-0,001 ± 0,000) | 1,122 (-0,001 ± 0,001) | 1,015, p5 0,05 (-0,001 ± 0,001) | 0,987, p5 0,00 (-0,001 ± 0,002) |
| `espera_e` | 1,163, p5 0,00 (-0,014 ± 0,002) | 1,100 (-0,024 ± 0,003) | 0,982, p5 0,06 (-0,035 ± 0,004) | 0,934, p5 0,00 (-0,054 ± 0,009) |
| `fondo_rec` | 1,177, p5 0,00 (-0,000 ± 0,001) | 1,127 (+0,004 ± 0,002) | 1,033, p5 0,08 (+0,016 ± 0,002) | 1,020, p5 0,00 (+0,031 ± 0,005) |
| `fondo_min` | 1,178, p5 0,00 (+0,001 ± 0,000) | 1,127 (+0,003 ± 0,001) | 1,026, p5 0,05 (+0,010 ± 0,001) | 0,997, p5 0,00 (+0,009 ± 0,002) |
| `fondo_ancla` | 1,205, p5 0,09 (+0,028 ± 0,002) | 1,153 (+0,030 ± 0,003) | 1,087, p5 0,16 (+0,070 ± 0,005) | 1,067, p5 0,00 (+0,079 ± 0,010) |
| `rec_e` | 1,181, p5 0,00 (+0,004 ± 0,001) | 1,133 (+0,010 ± 0,002) | 1,041, p5 0,10 (+0,024 ± 0,002) | 1,042, p5 0,00 (+0,054 ± 0,005) |
| `min_e` | 1,184, p5 0,00 (+0,007 ± 0,001) | 1,135 (+0,012 ± 0,001) | 1,038, p5 0,07 (+0,021 ± 0,001) | 1,033, p5 0,00 (+0,045 ± 0,002) |
| `completo` | 1,182, p5 0,00 (+0,006 ± 0,001) | 1,134 (+0,011 ± 0,001) | 1,039, p5 0,09 (+0,023 ± 0,002) | 1,040, p5 0,00 (+0,051 ± 0,005) |
| `completo_s` | 1,178, p5 0,00 (+0,001 ± 0,001) | 1,128 (+0,004 ± 0,001) | 1,031, p5 0,08 (+0,015 ± 0,002) | 1,017, p5 0,00 (+0,029 ± 0,005) |
| `completo_esp` | 1,174, p5 0,00 (-0,003 ± 0,001) | 1,121 (-0,003 ± 0,002) | 1,018, p5 0,09 (+0,001 ± 0,002) | 0,990, p5 0,00 (+0,002 ± 0,006) |
| `completo_ap` | 1,184, p5 0,00 (+0,007 ± 0,001) | 1,138 (+0,014 ± 0,002) | 1,053, p5 0,10 (+0,036 ± 0,002) | 1,053, p5 0,00 (+0,064 ± 0,005) |
| `completo_ancla` | 1,206, p5 0,09 (+0,029 ± 0,002) | 1,155 (+0,031 ± 0,003) | 1,088, p5 0,17 (+0,071 ± 0,005) | 1,071, p5 0,00 (+0,082 ± 0,010) |
| `completo_min` | 1,184, p5 0,00 (+0,007 ± 0,001) | 1,134 (+0,010 ± 0,001) | 1,030, p5 0,07 (+0,014 ± 0,001) | 1,030, p5 0,00 (+0,042 ± 0,002) |

### H3b, lineal en el puesto. 2000 ticks, conjunto estres

| Candidata | mixto | fuerte | racional | reversores |
|---|---|---|---|---|
| `max_media` | 1,212, p5 0,10 (+0,000 ± 0,000) | 1,100 (+0,000 ± 0,000) | 1,148, p5 0,20 (+0,000 ± 0,000) | 1,003, p5 0,20 (+0,000 ± 0,000) |
| `base` | 1,183, p5 0,10 (-0,029 ± 0,005) | 1,038 (-0,062 ± 0,007) | 1,062, p5 0,20 (-0,085 ± 0,007) | 0,910, p5 0,20 (-0,093 ± 0,010) |
| `kalman` | 1,209, p5 0,00 (-0,003 ± 0,003) | 1,093 (-0,007 ± 0,005) | 1,145, p5 0,20 (-0,003 ± 0,004) | 0,989, p5 0,00 (-0,014 ± 0,007) |
| `ejec_a` | 1,237, p5 0,10 (+0,025 ± 0,001) | 1,178 (+0,078 ± 0,002) | 1,178, p5 0,20 (+0,030 ± 0,001) | 1,131, p5 0,20 (+0,127 ± 0,003) |
| `ejec_b` | 1,238, p5 0,10 (+0,026 ± 0,001) | 1,175 (+0,075 ± 0,003) | 1,183, p5 0,20 (+0,035 ± 0,001) | 1,124, p5 0,10 (+0,121 ± 0,004) |
| `espera` | 1,197, p5 0,00 (-0,014 ± 0,003) | 1,063 (-0,037 ± 0,005) | 1,117, p5 0,20 (-0,031 ± 0,004) | 0,946, p5 0,00 (-0,057 ± 0,008) |
| `aprendiz` | 1,215, p5 0,10 (+0,003 ± 0,001) | 1,107 (+0,007 ± 0,002) | 1,153, p5 0,20 (+0,006 ± 0,001) | 1,014, p5 0,20 (+0,010 ± 0,003) |
| `aprendiz_patron` | 1,210, p5 0,10 (-0,002 ± 0,001) | 1,095 (-0,005 ± 0,002) | 1,148, p5 0,20 (+0,000 ± 0,001) | 0,995, p5 0,00 (-0,008 ± 0,003) |
| `espera_e` | 1,206, p5 0,00 (-0,006 ± 0,003) | 1,081 (-0,019 ± 0,005) | 1,130, p5 0,20 (-0,018 ± 0,004) | 0,972, p5 0,00 (-0,032 ± 0,008) |
| `fondo_rec` | 1,221, p5 0,00 (+0,010 ± 0,002) | 1,133 (+0,033 ± 0,004) | 1,168, p5 0,20 (+0,020 ± 0,003) | 1,055, p5 0,00 (+0,052 ± 0,006) |
| `fondo_min` | 1,214, p5 0,10 (+0,002 ± 0,001) | 1,108 (+0,008 ± 0,001) | 1,154, p5 0,20 (+0,006 ± 0,001) | 1,016, p5 0,20 (+0,013 ± 0,002) |
| `fondo_ancla` | 1,265, p5 0,20 (+0,053 ± 0,003) | 1,163 (+0,063 ± 0,006) | 1,224, p5 0,20 (+0,076 ± 0,005) | 1,079, p5 0,00 (+0,075 ± 0,008) |
| `rec_e` | 1,229, p5 0,00 (+0,018 ± 0,002) | 1,153 (+0,053 ± 0,004) | 1,180, p5 0,20 (+0,032 ± 0,003) | 1,087, p5 0,00 (+0,083 ± 0,006) |
| `min_e` | 1,239, p5 0,10 (+0,027 ± 0,001) | 1,183 (+0,083 ± 0,002) | 1,184, p5 0,20 (+0,036 ± 0,001) | 1,140, p5 0,10 (+0,137 ± 0,004) |
| `completo` | 1,232, p5 0,00 (+0,021 ± 0,002) | 1,158 (+0,058 ± 0,004) | 1,180, p5 0,20 (+0,033 ± 0,002) | 1,096, p5 0,00 (+0,092 ± 0,006) |
| `completo_s` | 1,224, p5 0,00 (+0,013 ± 0,002) | 1,138 (+0,038 ± 0,004) | 1,169, p5 0,20 (+0,021 ± 0,002) | 1,062, p5 0,00 (+0,059 ± 0,006) |
| `completo_esp` | 1,215, p5 0,00 (+0,003 ± 0,002) | 1,110 (+0,010 ± 0,004) | 1,154, p5 0,20 (+0,006 ± 0,003) | 1,018, p5 0,00 (+0,014 ± 0,006) |
| `completo_ap` | 1,233, p5 0,00 (+0,021 ± 0,002) | 1,158 (+0,058 ± 0,004) | 1,188, p5 0,20 (+0,040 ± 0,003) | 1,096, p5 0,00 (+0,093 ± 0,006) |
| `completo_ancla` | 1,265, p5 0,20 (+0,054 ± 0,003) | 1,164 (+0,064 ± 0,006) | 1,225, p5 0,20 (+0,077 ± 0,005) | 1,081, p5 0,00 (+0,077 ± 0,008) |
| `completo_min` | 1,236, p5 0,10 (+0,025 ± 0,001) | 1,173 (+0,073 ± 0,002) | 1,179, p5 0,20 (+0,031 ± 0,001) | 1,122, p5 0,10 (+0,119 ± 0,004) |

### H3a, lineal en patrimonio. 20 000 ticks, interiores, conjunto estres

| Candidata | mixto | fuerte | racional | reversores |
|---|---|---|---|---|
| `max_media` | 1,559, p5 0,06 (+0,000 ± 0,000) | 1,404 (+0,000 ± 0,000) | 1,144, p5 0,42 (+0,000 ± 0,000) | 1,063, p5 0,00 (+0,000 ± 0,000) |
| `base` | 1,312, p5 0,22 (-0,247 ± 0,014) | 1,062 (-0,342 ± 0,019) | 0,792, p5 0,16 (-0,353 ± 0,019) | 0,349, p5 0,00 (-0,715 ± 0,045) |
| `kalman` | 1,543, p5 0,09 (-0,016 ± 0,005) | 1,389 (-0,015 ± 0,007) | 1,136, p5 0,43 (-0,008 ± 0,007) | 1,052, p5 0,00 (-0,012 ± 0,019) |
| `ejec_a` | 1,568, p5 0,09 (+0,009 ± 0,001) | 1,418 (+0,014 ± 0,001) | 1,159, p5 0,45 (+0,014 ± 0,001) | 1,106, p5 0,05 (+0,043 ± 0,005) |
| `ejec_b` | 1,568, p5 0,11 (+0,009 ± 0,002) | 1,419 (+0,014 ± 0,002) | 1,158, p5 0,46 (+0,014 ± 0,002) | 1,112, p5 0,11 (+0,048 ± 0,008) |
| `espera` | 1,449, p5 0,11 (-0,110 ± 0,007) | 1,247 (-0,157 ± 0,010) | 0,991, p5 0,37 (-0,153 ± 0,009) | 0,742, p5 0,00 (-0,322 ± 0,024) |
| `aprendiz` | 1,656, p5 0,10 (+0,097 ± 0,008) | 1,620 (+0,216 ± 0,013) | 1,602, p5 0,43 (+0,458 ± 0,018) | 1,548, p5 0,00 (+0,484 ± 0,028) |
| `aprendiz_patron` | 1,547, p5 0,09 (-0,012 ± 0,002) | 1,389 (-0,015 ± 0,003) | 1,130, p5 0,43 (-0,015 ± 0,003) | 1,036, p5 0,00 (-0,028 ± 0,010) |
| `espera_e` | 1,458, p5 0,13 (-0,102 ± 0,007) | 1,260 (-0,144 ± 0,010) | 1,004, p5 0,39 (-0,140 ± 0,010) | 0,767, p5 0,00 (-0,296 ± 0,025) |
| `fondo_rec` | 1,578, p5 0,06 (+0,019 ± 0,003) | 1,449 (+0,045 ± 0,005) | 1,200, p5 0,43 (+0,056 ± 0,005) | 1,166, p5 0,00 (+0,102 ± 0,012) |
| `fondo_min` | 1,658, p5 0,05 (+0,099 ± 0,007) | 1,627 (+0,223 ± 0,012) | 1,665, p5 0,43 (+0,520 ± 0,019) | 1,572, p5 0,00 (+0,509 ± 0,025) |
| `fondo_ancla` | 1,414, p5 0,36 (-0,145 ± 0,010) | 1,203 (-0,201 ± 0,013) | 0,944, p5 0,38 (-0,200 ± 0,014) | 0,676, p5 0,00 (-0,387 ± 0,034) |
| `rec_e` | 1,584, p5 0,08 (+0,025 ± 0,003) | 1,458 (+0,054 ± 0,004) | 1,210, p5 0,46 (+0,065 ± 0,004) | 1,189, p5 0,00 (+0,125 ± 0,012) |
| `min_e` | 1,667, p5 0,09 (+0,108 ± 0,007) | 1,640 (+0,236 ± 0,012) | 1,678, p5 0,46 (+0,534 ± 0,018) | 1,600, p5 0,00 (+0,537 ± 0,024) |
| `completo` | 1,633, p5 0,07 (+0,073 ± 0,005) | 1,569 (+0,165 ± 0,008) | 1,388, p5 0,46 (+0,244 ± 0,009) | 1,434, p5 0,00 (+0,371 ± 0,019) |
| `completo_s` | 1,628, p5 0,05 (+0,068 ± 0,005) | 1,561 (+0,157 ± 0,009) | 1,381, p5 0,45 (+0,236 ± 0,010) | 1,414, p5 0,00 (+0,351 ± 0,020) |
| `completo_esp` | 1,553, p5 0,03 (-0,006 ± 0,003) | 1,406 (+0,001 ± 0,005) | 1,147, p5 0,40 (+0,003 ± 0,005) | 1,072, p5 0,00 (+0,008 ± 0,013) |
| `completo_ap` | 1,650, p5 0,04 (+0,091 ± 0,007) | 1,614 (+0,210 ± 0,012) | 1,578, p5 0,40 (+0,433 ± 0,017) | 1,532, p5 0,00 (+0,468 ± 0,026) |
| `completo_ancla` | 1,423, p5 0,34 (-0,136 ± 0,009) | 1,213 (-0,191 ± 0,013) | 0,954, p5 0,40 (-0,190 ± 0,013) | 0,691, p5 0,00 (-0,372 ± 0,032) |
| `completo_min` | 1,668, p5 0,10 (+0,109 ± 0,007) | 1,640 (+0,236 ± 0,012) | 1,675, p5 0,50 (+0,531 ± 0,018) | 1,591, p5 0,00 (+0,528 ± 0,025) |

### H3b, lineal en el puesto. 20 000 ticks, interiores, conjunto estres

| Candidata | mixto | fuerte | racional | reversores |
|---|---|---|---|---|
| `max_media` | 1,570, p5 0,20 (+0,000 ± 0,000) | 1,279 (+0,000 ± 0,000) | 1,331, p5 0,50 (+0,000 ± 0,000) | 1,023, p5 0,30 (+0,000 ± 0,000) |
| `base` | 1,516, p5 0,40 (-0,054 ± 0,010) | 1,025 (-0,253 ± 0,019) | 1,045, p5 0,40 (-0,286 ± 0,019) | 0,582, p5 0,10 (-0,441 ± 0,028) |
| `kalman` | 1,562, p5 0,20 (-0,007 ± 0,006) | 1,256 (-0,023 ± 0,013) | 1,321, p5 0,40 (-0,011 ± 0,008) | 0,987, p5 0,00 (-0,037 ± 0,020) |
| `ejec_a` | 1,604, p5 0,20 (+0,034 ± 0,003) | 1,377 (+0,098 ± 0,008) | 1,365, p5 0,60 (+0,034 ± 0,003) | 1,174, p5 0,40 (+0,151 ± 0,013) |
| `ejec_b` | 1,580, p5 0,20 (+0,010 ± 0,004) | 1,277 (-0,002 ± 0,010) | 1,348, p5 0,60 (+0,017 ± 0,004) | 1,010, p5 0,20 (-0,013 ± 0,016) |
| `espera` | 1,524, p5 0,20 (-0,045 ± 0,007) | 1,119 (-0,160 ± 0,013) | 1,222, p5 0,40 (-0,110 ± 0,010) | 0,762, p5 0,00 (-0,261 ± 0,020) |
| `aprendiz` | 1,656, p5 0,20 (+0,086 ± 0,007) | 1,606 (+0,327 ± 0,017) | 1,605, p5 0,40 (+0,273 ± 0,013) | 1,565, p5 0,00 (+0,541 ± 0,026) |
| `aprendiz_patron` | 1,553, p5 0,20 (-0,016 ± 0,004) | 1,198 (-0,080 ± 0,010) | 1,310, p5 0,40 (-0,021 ± 0,005) | 0,888, p5 0,00 (-0,135 ± 0,016) |
| `espera_e` | 1,539, p5 0,20 (-0,031 ± 0,007) | 1,143 (-0,136 ± 0,013) | 1,238, p5 0,40 (-0,093 ± 0,010) | 0,797, p5 0,00 (-0,226 ± 0,020) |
| `fondo_rec` | 1,604, p5 0,20 (+0,035 ± 0,004) | 1,400 (+0,122 ± 0,010) | 1,379, p5 0,40 (+0,048 ± 0,006) | 1,224, p5 0,00 (+0,201 ± 0,016) |
| `fondo_min` | 1,660, p5 0,20 (+0,090 ± 0,006) | 1,616 (+0,337 ± 0,015) | 1,655, p5 0,40 (+0,323 ± 0,013) | 1,585, p5 0,00 (+0,562 ± 0,023) |
| `fondo_ancla` | 1,564, p5 0,40 (-0,006 ± 0,008) | 1,168 (-0,111 ± 0,017) | 1,220, p5 0,60 (-0,111 ± 0,014) | 0,821, p5 0,00 (-0,203 ± 0,025) |
| `rec_e` | 1,612, p5 0,20 (+0,042 ± 0,005) | 1,418 (+0,139 ± 0,010) | 1,390, p5 0,40 (+0,059 ± 0,006) | 1,249, p5 0,00 (+0,226 ± 0,015) |
| `min_e` | 1,676, p5 0,20 (+0,106 ± 0,006) | 1,651 (+0,372 ± 0,014) | 1,675, p5 0,40 (+0,344 ± 0,012) | 1,636, p5 0,00 (+0,613 ± 0,021) |
| `completo` | 1,637, p5 0,20 (+0,067 ± 0,005) | 1,518 (+0,240 ± 0,013) | 1,480, p5 0,40 (+0,149 ± 0,008) | 1,404, p5 0,00 (+0,381 ± 0,020) |
| `completo_s` | 1,629, p5 0,20 (+0,059 ± 0,005) | 1,503 (+0,224 ± 0,013) | 1,469, p5 0,40 (+0,138 ± 0,009) | 1,384, p5 0,00 (+0,361 ± 0,021) |
| `completo_esp` | 1,570, p5 0,20 (+0,000 ± 0,005) | 1,304 (+0,025 ± 0,012) | 1,330, p5 0,40 (-0,002 ± 0,006) | 1,068, p5 0,00 (+0,045 ± 0,018) |
| `completo_ap` | 1,652, p5 0,20 (+0,083 ± 0,006) | 1,593 (+0,314 ± 0,016) | 1,580, p5 0,40 (+0,249 ± 0,012) | 1,549, p5 0,00 (+0,525 ± 0,025) |
| `completo_ancla` | 1,559, p5 0,40 (-0,011 ± 0,008) | 1,162 (-0,117 ± 0,016) | 1,220, p5 0,60 (-0,111 ± 0,013) | 0,812, p5 0,00 (-0,211 ± 0,025) |
| `completo_min` | 1,672, p5 0,20 (+0,103 ± 0,006) | 1,650 (+0,371 ± 0,014) | 1,669, p5 0,40 (+0,338 ± 0,012) | 1,634, p5 0,00 (+0,610 ± 0,023) |

### H3a, lineal en patrimonio. 20 000 ticks, parada, conjunto estres

| Candidata | mixto | fuerte | racional | reversores |
|---|---|---|---|---|
| `max_media` | 1,140, p5 0,00 (+0,000 ± 0,000) | 1,087 (+0,000 ± 0,000) | 0,977, p5 0,02 (+0,000 ± 0,000) | 0,975, p5 0,00 (+0,000 ± 0,000) |
| `base` | 1,107, p5 0,00 (-0,033 ± 0,007) | 1,033 (-0,054 ± 0,009) | 0,896, p5 0,02 (-0,080 ± 0,010) | 0,868, p5 0,00 (-0,108 ± 0,024) |
| `kalman` | 1,134, p5 0,00 (-0,006 ± 0,003) | 1,079 (-0,008 ± 0,004) | 0,973, p5 0,02 (-0,004 ± 0,005) | 0,971, p5 0,00 (-0,004 ± 0,012) |
| `ejec_a` | 1,146, p5 0,00 (+0,006 ± 0,000) | 1,096 (+0,009 ± 0,000) | 0,988, p5 0,04 (+0,011 ± 0,000) | 1,014, p5 0,00 (+0,039 ± 0,002) |
| `ejec_b` | 1,149, p5 0,00 (+0,009 ± 0,001) | 1,100 (+0,013 ± 0,001) | 0,992, p5 0,05 (+0,015 ± 0,001) | 1,027, p5 0,00 (+0,052 ± 0,003) |
| `espera` | 1,113, p5 0,00 (-0,027 ± 0,004) | 1,048 (-0,039 ± 0,005) | 0,938, p5 0,05 (-0,039 ± 0,006) | 0,893, p5 0,00 (-0,082 ± 0,014) |
| `aprendiz` | 1,179, p5 0,00 (+0,039 ± 0,003) | 1,156 (+0,069 ± 0,004) | 1,102, p5 0,04 (+0,125 ± 0,006) | 1,146, p5 0,00 (+0,171 ± 0,011) |
| `aprendiz_patron` | 1,136, p5 0,00 (-0,004 ± 0,001) | 1,082 (-0,005 ± 0,001) | 0,973, p5 0,03 (-0,004 ± 0,001) | 0,968, p5 0,00 (-0,007 ± 0,004) |
| `espera_e` | 1,120, p5 0,00 (-0,020 ± 0,004) | 1,057 (-0,030 ± 0,005) | 0,948, p5 0,06 (-0,029 ± 0,006) | 0,921, p5 0,00 (-0,054 ± 0,014) |
| `fondo_rec` | 1,138, p5 0,00 (-0,001 ± 0,002) | 1,089 (+0,001 ± 0,003) | 0,985, p5 0,05 (+0,008 ± 0,003) | 0,981, p5 0,00 (+0,006 ± 0,008) |
| `fondo_min` | 1,160, p5 0,00 (+0,021 ± 0,003) | 1,134 (+0,047 ± 0,004) | 1,090, p5 0,02 (+0,113 ± 0,006) | 1,092, p5 0,00 (+0,117 ± 0,009) |
| `fondo_ancla` | 1,091, p5 0,04 (-0,049 ± 0,004) | 1,018 (-0,069 ± 0,006) | 0,938, p5 0,04 (-0,039 ± 0,008) | 0,864, p5 0,00 (-0,111 ± 0,016) |
| `rec_e` | 1,143, p5 0,00 (+0,004 ± 0,002) | 1,096 (+0,009 ± 0,003) | 0,993, p5 0,06 (+0,017 ± 0,003) | 1,007, p5 0,00 (+0,032 ± 0,008) |
| `min_e` | 1,167, p5 0,00 (+0,027 ± 0,003) | 1,143 (+0,056 ± 0,004) | 1,101, p5 0,03 (+0,125 ± 0,006) | 1,125, p5 0,00 (+0,150 ± 0,009) |
| `completo` | 1,158, p5 0,00 (+0,018 ± 0,002) | 1,124 (+0,037 ± 0,003) | 1,036, p5 0,07 (+0,059 ± 0,004) | 1,070, p5 0,00 (+0,095 ± 0,009) |
| `completo_s` | 1,153, p5 0,00 (+0,013 ± 0,002) | 1,117 (+0,030 ± 0,003) | 1,028, p5 0,06 (+0,052 ± 0,004) | 1,045, p5 0,00 (+0,070 ± 0,009) |
| `completo_esp` | 1,134, p5 0,00 (-0,006 ± 0,002) | 1,080 (-0,007 ± 0,003) | 0,970, p5 0,06 (-0,007 ± 0,003) | 0,957, p5 0,00 (-0,018 ± 0,009) |
| `completo_ap` | 1,162, p5 0,00 (+0,023 ± 0,003) | 1,135 (+0,048 ± 0,004) | 1,078, p5 0,06 (+0,101 ± 0,006) | 1,097, p5 0,00 (+0,122 ± 0,011) |
| `completo_ancla` | 1,092, p5 0,04 (-0,047 ± 0,004) | 1,021 (-0,066 ± 0,006) | 0,940, p5 0,04 (-0,036 ± 0,008) | 0,876, p5 0,00 (-0,099 ± 0,016) |
| `completo_min` | 1,175, p5 0,00 (+0,036 ± 0,003) | 1,152 (+0,065 ± 0,004) | 1,109, p5 0,04 (+0,133 ± 0,006) | 1,149, p5 0,00 (+0,174 ± 0,010) |

### H3b, lineal en el puesto. 20 000 ticks, parada, conjunto estres

| Candidata | mixto | fuerte | racional | reversores |
|---|---|---|---|---|
| `max_media` | 1,213, p5 0,10 (+0,000 ± 0,000) | 1,101 (+0,000 ± 0,000) | 1,143, p5 0,20 (+0,000 ± 0,000) | 0,996, p5 0,20 (+0,000 ± 0,000) |
| `base` | 1,220, p5 0,20 (+0,007 ± 0,007) | 1,065 (-0,035 ± 0,011) | 1,086, p5 0,30 (-0,057 ± 0,010) | 0,923, p5 0,20 (-0,073 ± 0,016) |
| `kalman` | 1,213, p5 0,10 (+0,000 ± 0,004) | 1,094 (-0,007 ± 0,007) | 1,142, p5 0,20 (-0,001 ± 0,006) | 0,984, p5 0,00 (-0,012 ± 0,011) |
| `ejec_a` | 1,246, p5 0,20 (+0,033 ± 0,001) | 1,207 (+0,106 ± 0,003) | 1,178, p5 0,20 (+0,035 ± 0,001) | 1,170, p5 0,20 (+0,173 ± 0,006) |
| `ejec_b` | 1,241, p5 0,20 (+0,028 ± 0,002) | 1,178 (+0,077 ± 0,004) | 1,176, p5 0,30 (+0,033 ± 0,002) | 1,119, p5 0,20 (+0,123 ± 0,007) |
| `espera` | 1,208, p5 0,20 (-0,005 ± 0,004) | 1,065 (-0,036 ± 0,008) | 1,119, p5 0,20 (-0,025 ± 0,006) | 0,933, p5 0,00 (-0,063 ± 0,012) |
| `aprendiz` | 1,255, p5 0,20 (+0,042 ± 0,003) | 1,209 (+0,108 ± 0,007) | 1,233, p5 0,20 (+0,090 ± 0,005) | 1,168, p5 0,00 (+0,171 ± 0,010) |
| `aprendiz_patron` | 1,209, p5 0,10 (-0,004 ± 0,002) | 1,083 (-0,018 ± 0,004) | 1,139, p5 0,20 (-0,004 ± 0,002) | 0,968, p5 0,00 (-0,028 ± 0,007) |
| `espera_e` | 1,218, p5 0,20 (+0,005 ± 0,004) | 1,087 (-0,014 ± 0,008) | 1,133, p5 0,20 (-0,010 ± 0,006) | 0,965, p5 0,00 (-0,032 ± 0,012) |
| `fondo_rec` | 1,218, p5 0,00 (+0,005 ± 0,003) | 1,121 (+0,020 ± 0,006) | 1,150, p5 0,20 (+0,006 ± 0,004) | 1,028, p5 0,00 (+0,032 ± 0,009) |
| `fondo_min` | 1,232, p5 0,10 (+0,019 ± 0,003) | 1,168 (+0,067 ± 0,006) | 1,215, p5 0,20 (+0,071 ± 0,005) | 1,111, p5 0,00 (+0,115 ± 0,009) |
| `fondo_ancla` | 1,212, p5 0,20 (-0,001 ± 0,005) | 1,063 (-0,038 ± 0,009) | 1,119, p5 0,20 (-0,025 ± 0,008) | 0,924, p5 0,00 (-0,073 ± 0,013) |
| `rec_e` | 1,227, p5 0,20 (+0,014 ± 0,003) | 1,143 (+0,042 ± 0,006) | 1,164, p5 0,20 (+0,021 ± 0,004) | 1,064, p5 0,00 (+0,067 ± 0,009) |
| `min_e` | 1,253, p5 0,20 (+0,040 ± 0,003) | 1,235 (+0,134 ± 0,006) | 1,241, p5 0,20 (+0,098 ± 0,005) | 1,218, p5 0,00 (+0,222 ± 0,009) |
| `completo` | 1,239, p5 0,20 (+0,026 ± 0,003) | 1,176 (+0,075 ± 0,006) | 1,192, p5 0,20 (+0,048 ± 0,004) | 1,120, p5 0,00 (+0,124 ± 0,010) |
| `completo_s` | 1,231, p5 0,20 (+0,018 ± 0,003) | 1,157 (+0,056 ± 0,006) | 1,178, p5 0,20 (+0,035 ± 0,004) | 1,089, p5 0,00 (+0,093 ± 0,010) |
| `completo_esp` | 1,209, p5 0,00 (-0,004 ± 0,003) | 1,092 (-0,009 ± 0,006) | 1,137, p5 0,20 (-0,006 ± 0,004) | 0,982, p5 0,00 (-0,014 ± 0,010) |
| `completo_ap` | 1,241, p5 0,20 (+0,028 ± 0,003) | 1,184 (+0,083 ± 0,007) | 1,212, p5 0,20 (+0,068 ± 0,005) | 1,134, p5 0,00 (+0,138 ± 0,011) |
| `completo_ancla` | 1,213, p5 0,20 (+0,000 ± 0,005) | 1,068 (-0,033 ± 0,009) | 1,121, p5 0,20 (-0,022 ± 0,008) | 0,931, p5 0,00 (-0,065 ± 0,013) |
| `completo_min` | 1,260, p5 0,20 (+0,047 ± 0,003) | 1,236 (+0,135 ± 0,006) | 1,250, p5 0,20 (+0,107 ± 0,005) | 1,218, p5 0,00 (+0,222 ± 0,010) |

## 4. Competencia de tres rondas: media y percentil 5 de los puntos

La media de los puntos de la competencia es la media de una ronda (sección 3). Cada celda: percentil 5 del promedio de las tres rondas (diferencia contra `max_media` ± error). El error que da el arnés para el percentil 5 es unas 2,8 veces el real.

### 2000 ticks, conjunto evidencia

| Candidata | mixto: H3a | mixto: H3b | fuerte: H3a | fuerte: H3b | racional: H3a | racional: H3b | reversores: H3a | reversores: H3b |
|---|---|---|---|---|---|---|---|---|
| `max_media` | 0,882 (+0,000 ± 0,000) | 0,911 (+0,000 ± 0,000) | 0,760 (+0,000 ± 0,000) | 0,750 (+0,000 ± 0,000) | 0,647 (+0,000 ± 0,000) | 0,728 (+0,000 ± 0,000) | 0,215 (+0,000 ± 0,000) | 0,506 (+0,000 ± 0,000) |
| `base` | 0,835 (-0,047 ± 0,015) | 0,872 (-0,039 ± 0,022) | 0,701 (-0,060 ± 0,017) | 0,667 (-0,083 ± 0,022) | 0,540 (-0,108 ± 0,015) | 0,644 (-0,083 ± 0,022) | 0,000 (-0,215 ± 0,021) | 0,394 (-0,111 ± 0,021) |
| `kalman` | 0,888 (+0,005 ± 0,012) | 0,900 (-0,011 ± 0,022) | 0,772 (+0,012 ± 0,014) | 0,667 (-0,083 ± 0,023) | 0,644 (-0,003 ± 0,011) | 0,722 (-0,006 ± 0,025) | 0,325 (+0,110 ± 0,021) | 0,400 (-0,106 ± 0,022) |
| `ejec_a` | 0,891 (+0,009 ± 0,004) | 0,933 (+0,022 ± 0,020) | 0,776 (+0,016 ± 0,005) | 0,806 (+0,056 ± 0,018) | 0,662 (+0,015 ± 0,004) | 0,756 (+0,028 ± 0,020) | 0,268 (+0,053 ± 0,011) | 0,594 (+0,089 ± 0,018) |
| `ejec_b` | 0,901 (+0,019 ± 0,006) | 0,933 (+0,022 ± 0,022) | 0,796 (+0,036 ± 0,007) | 0,811 (+0,061 ± 0,019) | 0,679 (+0,032 ± 0,006) | 0,789 (+0,061 ± 0,017) | 0,334 (+0,119 ± 0,013) | 0,600 (+0,094 ± 0,019) |
| `espera` | 0,901 (+0,019 ± 0,013) | 0,906 (-0,006 ± 0,026) | 0,793 (+0,032 ± 0,015) | 0,711 (-0,039 ± 0,029) | 0,672 (+0,025 ± 0,012) | 0,733 (+0,006 ± 0,017) | 0,358 (+0,143 ± 0,022) | 0,400 (-0,106 ± 0,017) |
| `aprendiz` | 0,883 (+0,001 ± 0,003) | 0,911 (+0,000 ± 0,010) | 0,762 (+0,001 ± 0,003) | 0,756 (+0,006 ± 0,009) | 0,647 (-0,001 ± 0,003) | 0,728 (+0,000 ± 0,009) | 0,215 (-0,000 ± 0,005) | 0,494 (-0,011 ± 0,012) |
| `aprendiz_patron` | 0,882 (-0,000 ± 0,006) | 0,900 (-0,011 ± 0,018) | 0,764 (+0,004 ± 0,007) | 0,728 (-0,022 ± 0,016) | 0,646 (-0,001 ± 0,005) | 0,733 (+0,006 ± 0,012) | 0,248 (+0,033 ± 0,011) | 0,467 (-0,039 ± 0,016) |
| `espera_e` | 0,908 (+0,026 ± 0,013) | 0,933 (+0,022 ± 0,023) | 0,805 (+0,045 ± 0,015) | 0,733 (-0,017 ± 0,022) | 0,686 (+0,039 ± 0,012) | 0,733 (+0,006 ± 0,023) | 0,380 (+0,165 ± 0,023) | 0,411 (-0,094 ± 0,029) |
| `fondo_rec` | 0,887 (+0,005 ± 0,009) | 0,922 (+0,011 ± 0,024) | 0,779 (+0,019 ± 0,010) | 0,733 (-0,017 ± 0,024) | 0,663 (+0,015 ± 0,008) | 0,733 (+0,006 ± 0,015) | 0,320 (+0,104 ± 0,017) | 0,422 (-0,083 ± 0,029) |
| `fondo_min` | 0,882 (+0,000 ± 0,002) | 0,917 (+0,006 ± 0,007) | 0,760 (-0,000 ± 0,004) | 0,750 (-0,000 ± 0,011) | 0,647 (-0,000 ± 0,003) | 0,728 (+0,000 ± 0,007) | 0,213 (-0,002 ± 0,006) | 0,500 (-0,006 ± 0,012) |
| `fondo_ancla` | 0,939 (+0,057 ± 0,010) | 0,967 (+0,056 ± 0,025) | 0,824 (+0,064 ± 0,012) | 0,667 (-0,083 ± 0,019) | 0,612 (-0,036 ± 0,011) | 0,667 (-0,061 ± 0,020) | 0,190 (-0,026 ± 0,022) | 0,244 (-0,261 ± 0,025) |
| `rec_e` | 0,894 (+0,012 ± 0,008) | 0,933 (+0,022 ± 0,021) | 0,787 (+0,026 ± 0,010) | 0,733 (-0,017 ± 0,017) | 0,676 (+0,029 ± 0,008) | 0,733 (+0,006 ± 0,022) | 0,345 (+0,130 ± 0,017) | 0,467 (-0,039 ± 0,023) |
| `min_e` | 0,892 (+0,010 ± 0,005) | 0,933 (+0,022 ± 0,021) | 0,777 (+0,017 ± 0,006) | 0,800 (+0,050 ± 0,017) | 0,662 (+0,015 ± 0,005) | 0,756 (+0,028 ± 0,020) | 0,269 (+0,054 ± 0,012) | 0,594 (+0,089 ± 0,019) |
| `completo` | 0,892 (+0,010 ± 0,008) | 0,933 (+0,022 ± 0,021) | 0,786 (+0,025 ± 0,009) | 0,733 (-0,017 ± 0,021) | 0,676 (+0,028 ± 0,008) | 0,744 (+0,017 ± 0,023) | 0,333 (+0,118 ± 0,017) | 0,467 (-0,039 ± 0,023) |
| `completo_s` | 0,886 (+0,004 ± 0,008) | 0,928 (+0,017 ± 0,024) | 0,778 (+0,017 ± 0,010) | 0,722 (-0,028 ± 0,023) | 0,665 (+0,017 ± 0,007) | 0,733 (+0,006 ± 0,016) | 0,315 (+0,099 ± 0,016) | 0,444 (-0,061 ± 0,026) |
| `completo_esp` | 0,885 (+0,003 ± 0,009) | 0,933 (+0,022 ± 0,022) | 0,780 (+0,020 ± 0,010) | 0,722 (-0,028 ± 0,022) | 0,676 (+0,029 ± 0,008) | 0,733 (+0,006 ± 0,019) | 0,339 (+0,124 ± 0,018) | 0,411 (-0,094 ± 0,027) |
| `completo_ap` | 0,888 (+0,006 ± 0,008) | 0,933 (+0,022 ± 0,020) | 0,784 (+0,024 ± 0,009) | 0,733 (-0,017 ± 0,022) | 0,673 (+0,025 ± 0,008) | 0,733 (+0,006 ± 0,019) | 0,324 (+0,109 ± 0,017) | 0,433 (-0,072 ± 0,025) |
| `completo_ancla` | 0,941 (+0,058 ± 0,010) | 0,967 (+0,056 ± 0,026) | 0,824 (+0,064 ± 0,012) | 0,667 (-0,083 ± 0,019) | 0,610 (-0,038 ± 0,011) | 0,667 (-0,061 ± 0,020) | 0,186 (-0,030 ± 0,022) | 0,244 (-0,261 ± 0,027) |
| `completo_min` | 0,892 (+0,009 ± 0,005) | 0,933 (+0,022 ± 0,020) | 0,776 (+0,015 ± 0,005) | 0,800 (+0,050 ± 0,018) | 0,662 (+0,015 ± 0,004) | 0,756 (+0,028 ± 0,019) | 0,268 (+0,053 ± 0,012) | 0,594 (+0,089 ± 0,019) |

### 20 000 ticks, interiores, conjunto evidencia

| Candidata | mixto: H3a | mixto: H3b | fuerte: H3a | fuerte: H3b | racional: H3a | racional: H3b | reversores: H3a | reversores: H3b |
|---|---|---|---|---|---|---|---|---|
| `max_media` | 1,502 (+0,000 ± 0,000) | 1,522 (+0,000 ± 0,000) | 1,352 (+0,000 ± 0,000) | 1,061 (+0,000 ± 0,000) | 1,017 (+0,000 ± 0,000) | 1,061 (+0,000 ± 0,000) | 0,448 (+0,000 ± 0,000) | 0,683 (+0,000 ± 0,000) |
| `base` | 1,314 (-0,188 ± 0,019) | 1,389 (-0,133 ± 0,021) | 1,100 (-0,252 ± 0,024) | 0,772 (-0,289 ± 0,029) | 0,750 (-0,268 ± 0,024) | 0,800 (-0,261 ± 0,024) | 0,000 (-0,448 ± 0,036) | 0,300 (-0,383 ± 0,027) |
| `kalman` | 1,500 (-0,002 ± 0,014) | 1,511 (-0,011 ± 0,023) | 1,353 (+0,001 ± 0,016) | 1,011 (-0,050 ± 0,034) | 1,030 (+0,013 ± 0,017) | 1,056 (-0,006 ± 0,031) | 0,517 (+0,069 ± 0,036) | 0,567 (-0,117 ± 0,044) |
| `ejec_a` | 1,522 (+0,021 ± 0,007) | 1,600 (+0,078 ± 0,019) | 1,371 (+0,019 ± 0,007) | 1,211 (+0,150 ± 0,027) | 1,045 (+0,028 ± 0,007) | 1,133 (+0,072 ± 0,022) | 0,526 (+0,078 ± 0,018) | 0,889 (+0,206 ± 0,029) |
| `ejec_b` | 1,528 (+0,026 ± 0,008) | 1,589 (+0,067 ± 0,023) | 1,384 (+0,033 ± 0,009) | 1,178 (+0,117 ± 0,027) | 1,062 (+0,044 ± 0,009) | 1,133 (+0,072 ± 0,021) | 0,601 (+0,153 ± 0,023) | 0,800 (+0,117 ± 0,030) |
| `espera` | 1,486 (-0,016 ± 0,018) | 1,467 (-0,056 ± 0,027) | 1,331 (-0,021 ± 0,019) | 1,000 (-0,061 ± 0,034) | 1,014 (-0,003 ± 0,020) | 1,056 (-0,006 ± 0,030) | 0,506 (+0,058 ± 0,041) | 0,533 (-0,150 ± 0,039) |
| `aprendiz` | 1,477 (-0,024 ± 0,014) | 1,461 (-0,061 ± 0,023) | 1,321 (-0,030 ± 0,015) | 0,944 (-0,117 ± 0,024) | 0,984 (-0,034 ± 0,018) | 1,011 (-0,050 ± 0,027) | 0,401 (-0,047 ± 0,033) | 0,472 (-0,211 ± 0,032) |
| `aprendiz_patron` | 1,496 (-0,006 ± 0,009) | 1,472 (-0,050 ± 0,025) | 1,344 (-0,008 ± 0,011) | 0,989 (-0,072 ± 0,029) | 1,017 (-0,000 ± 0,011) | 1,067 (+0,006 ± 0,022) | 0,497 (+0,048 ± 0,026) | 0,533 (-0,150 ± 0,032) |
| `espera_e` | 1,501 (-0,001 ± 0,017) | 1,533 (+0,011 ± 0,029) | 1,345 (-0,006 ± 0,019) | 1,022 (-0,039 ± 0,033) | 1,030 (+0,013 ± 0,021) | 1,067 (+0,006 ± 0,032) | 0,547 (+0,099 ± 0,040) | 0,556 (-0,128 ± 0,040) |
| `fondo_rec` | 1,530 (+0,028 ± 0,012) | 1,533 (+0,011 ± 0,020) | 1,370 (+0,018 ± 0,013) | 1,067 (+0,006 ± 0,026) | 1,063 (+0,046 ± 0,014) | 1,111 (+0,050 ± 0,028) | 0,595 (+0,146 ± 0,031) | 0,667 (-0,017 ± 0,029) |
| `fondo_min` | 1,494 (-0,007 ± 0,015) | 1,467 (-0,056 ± 0,021) | 1,332 (-0,019 ± 0,017) | 0,956 (-0,106 ± 0,027) | 1,034 (+0,016 ± 0,018) | 1,061 (-0,000 ± 0,025) | 0,467 (+0,019 ± 0,037) | 0,489 (-0,194 ± 0,030) |
| `fondo_ancla` | 1,366 (-0,136 ± 0,016) | 1,400 (-0,122 ± 0,022) | 1,177 (-0,174 ± 0,017) | 0,700 (-0,361 ± 0,036) | 0,816 (-0,201 ± 0,017) | 0,856 (-0,206 ± 0,031) | 0,083 (-0,365 ± 0,036) | 0,133 (-0,550 ± 0,027) |
| `rec_e` | 1,537 (+0,036 ± 0,012) | 1,533 (+0,011 ± 0,022) | 1,387 (+0,036 ± 0,013) | 1,100 (+0,039 ± 0,029) | 1,081 (+0,063 ± 0,014) | 1,133 (+0,072 ± 0,026) | 0,636 (+0,188 ± 0,030) | 0,678 (-0,006 ± 0,032) |
| `min_e` | 1,513 (+0,012 ± 0,015) | 1,522 (+0,000 ± 0,022) | 1,351 (-0,001 ± 0,017) | 1,044 (-0,017 ± 0,033) | 1,056 (+0,038 ± 0,019) | 1,078 (+0,017 ± 0,030) | 0,521 (+0,073 ± 0,037) | 0,600 (-0,083 ± 0,041) |
| `completo` | 1,535 (+0,034 ± 0,011) | 1,533 (+0,011 ± 0,019) | 1,383 (+0,031 ± 0,013) | 1,067 (+0,006 ± 0,028) | 1,073 (+0,055 ± 0,014) | 1,133 (+0,072 ± 0,027) | 0,617 (+0,169 ± 0,031) | 0,667 (-0,017 ± 0,027) |
| `completo_s` | 1,525 (+0,024 ± 0,011) | 1,533 (+0,011 ± 0,023) | 1,369 (+0,018 ± 0,013) | 1,056 (-0,006 ± 0,030) | 1,058 (+0,040 ± 0,014) | 1,100 (+0,039 ± 0,028) | 0,574 (+0,126 ± 0,031) | 0,656 (-0,028 ± 0,030) |
| `completo_esp` | 1,528 (+0,026 ± 0,012) | 1,533 (+0,011 ± 0,023) | 1,369 (+0,018 ± 0,014) | 1,056 (-0,006 ± 0,031) | 1,061 (+0,043 ± 0,013) | 1,122 (+0,061 ± 0,030) | 0,597 (+0,148 ± 0,032) | 0,667 (-0,017 ± 0,026) |
| `completo_ap` | 1,523 (+0,022 ± 0,013) | 1,522 (+0,000 ± 0,029) | 1,373 (+0,022 ± 0,016) | 1,000 (-0,061 ± 0,031) | 1,069 (+0,052 ± 0,015) | 1,089 (+0,028 ± 0,028) | 0,544 (+0,096 ± 0,034) | 0,544 (-0,139 ± 0,040) |
| `completo_ancla` | 1,360 (-0,141 ± 0,016) | 1,389 (-0,133 ± 0,024) | 1,166 (-0,186 ± 0,016) | 0,678 (-0,383 ± 0,038) | 0,806 (-0,211 ± 0,018) | 0,833 (-0,228 ± 0,032) | 0,072 (-0,376 ± 0,036) | 0,133 (-0,550 ± 0,027) |
| `completo_min` | 1,516 (+0,014 ± 0,014) | 1,533 (+0,011 ± 0,019) | 1,364 (+0,012 ± 0,015) | 1,056 (-0,006 ± 0,030) | 1,052 (+0,034 ± 0,018) | 1,078 (+0,017 ± 0,024) | 0,530 (+0,082 ± 0,036) | 0,622 (-0,061 ± 0,039) |

### 20 000 ticks, parada, conjunto evidencia

| Candidata | mixto: H3a | mixto: H3b | fuerte: H3a | fuerte: H3b | racional: H3a | racional: H3b | reversores: H3a | reversores: H3b |
|---|---|---|---|---|---|---|---|---|
| `max_media` | 1,232 (+0,000 ± 0,000) | 1,283 (+0,000 ± 0,000) | 1,120 (+0,000 ± 0,000) | 0,967 (+0,000 ± 0,000) | 0,881 (+0,000 ± 0,000) | 0,939 (+0,000 ± 0,000) | 0,402 (+0,000 ± 0,000) | 0,639 (+0,000 ± 0,000) |
| `base` | 1,141 (-0,091 ± 0,014) | 1,217 (-0,067 ± 0,020) | 0,980 (-0,140 ± 0,018) | 0,783 (-0,183 ± 0,024) | 0,738 (-0,143 ± 0,017) | 0,811 (-0,128 ± 0,020) | 0,000 (-0,402 ± 0,024) | 0,333 (-0,306 ± 0,033) |
| `kalman` | 1,235 (+0,002 ± 0,011) | 1,278 (-0,006 ± 0,022) | 1,116 (-0,004 ± 0,011) | 0,889 (-0,078 ± 0,029) | 0,886 (+0,005 ± 0,013) | 0,933 (-0,006 ± 0,024) | 0,470 (+0,068 ± 0,025) | 0,522 (-0,117 ± 0,033) |
| `ejec_a` | 1,245 (+0,013 ± 0,004) | 1,333 (+0,050 ± 0,017) | 1,136 (+0,016 ± 0,004) | 1,089 (+0,122 ± 0,026) | 0,898 (+0,018 ± 0,004) | 1,000 (+0,061 ± 0,018) | 0,472 (+0,070 ± 0,012) | 0,811 (+0,172 ± 0,024) |
| `ejec_b` | 1,253 (+0,021 ± 0,006) | 1,333 (+0,050 ± 0,018) | 1,144 (+0,024 ± 0,006) | 1,072 (+0,106 ± 0,019) | 0,914 (+0,033 ± 0,006) | 1,000 (+0,061 ± 0,017) | 0,518 (+0,116 ± 0,015) | 0,789 (+0,150 ± 0,024) |
| `espera` | 1,252 (+0,020 ± 0,013) | 1,311 (+0,028 ± 0,028) | 1,132 (+0,012 ± 0,013) | 0,933 (-0,033 ± 0,024) | 0,913 (+0,032 ± 0,014) | 0,967 (+0,028 ± 0,030) | 0,508 (+0,106 ± 0,026) | 0,533 (-0,106 ± 0,031) |
| `aprendiz` | 1,230 (-0,002 ± 0,009) | 1,272 (-0,011 ± 0,016) | 1,106 (-0,014 ± 0,010) | 0,900 (-0,067 ± 0,021) | 0,869 (-0,011 ± 0,011) | 0,933 (-0,006 ± 0,017) | 0,390 (-0,011 ± 0,020) | 0,506 (-0,133 ± 0,025) |
| `aprendiz_patron` | 1,236 (+0,004 ± 0,007) | 1,267 (-0,017 ± 0,016) | 1,116 (-0,005 ± 0,007) | 0,894 (-0,072 ± 0,027) | 0,885 (+0,005 ± 0,009) | 0,933 (-0,006 ± 0,016) | 0,452 (+0,050 ± 0,017) | 0,522 (-0,117 ± 0,031) |
| `espera_e` | 1,261 (+0,029 ± 0,013) | 1,333 (+0,050 ± 0,024) | 1,145 (+0,025 ± 0,013) | 0,933 (-0,033 ± 0,026) | 0,931 (+0,050 ± 0,014) | 1,000 (+0,061 ± 0,019) | 0,546 (+0,145 ± 0,027) | 0,578 (-0,061 ± 0,038) |
| `fondo_rec` | 1,238 (+0,006 ± 0,008) | 1,267 (-0,017 ± 0,019) | 1,119 (-0,001 ± 0,008) | 0,933 (-0,033 ± 0,018) | 0,901 (+0,020 ± 0,009) | 0,944 (+0,006 ± 0,024) | 0,498 (+0,096 ± 0,020) | 0,589 (-0,050 ± 0,033) |
| `fondo_min` | 1,217 (-0,015 ± 0,011) | 1,267 (-0,017 ± 0,015) | 1,107 (-0,014 ± 0,011) | 0,867 (-0,100 ± 0,019) | 0,868 (-0,013 ± 0,012) | 0,928 (-0,011 ± 0,020) | 0,397 (-0,004 ± 0,022) | 0,483 (-0,156 ± 0,026) |
| `fondo_ancla` | 1,114 (-0,118 ± 0,012) | 1,200 (-0,083 ± 0,020) | 0,967 (-0,154 ± 0,013) | 0,611 (-0,356 ± 0,026) | 0,646 (-0,235 ± 0,013) | 0,667 (-0,272 ± 0,021) | 0,052 (-0,350 ± 0,024) | 0,122 (-0,517 ± 0,029) |
| `rec_e` | 1,246 (+0,014 ± 0,008) | 1,289 (+0,006 ± 0,025) | 1,132 (+0,011 ± 0,009) | 0,944 (-0,022 ± 0,027) | 0,914 (+0,033 ± 0,010) | 0,983 (+0,044 ± 0,026) | 0,535 (+0,133 ± 0,020) | 0,622 (-0,017 ± 0,032) |
| `min_e` | 1,231 (-0,001 ± 0,011) | 1,317 (+0,033 ± 0,025) | 1,123 (+0,003 ± 0,011) | 0,939 (-0,028 ± 0,023) | 0,888 (+0,007 ± 0,012) | 0,944 (+0,006 ± 0,022) | 0,448 (+0,046 ± 0,023) | 0,578 (-0,061 ± 0,033) |
| `completo` | 1,248 (+0,016 ± 0,008) | 1,289 (+0,006 ± 0,024) | 1,131 (+0,011 ± 0,009) | 0,944 (-0,022 ± 0,027) | 0,914 (+0,033 ± 0,009) | 1,000 (+0,061 ± 0,026) | 0,533 (+0,131 ± 0,020) | 0,622 (-0,017 ± 0,034) |
| `completo_s` | 1,241 (+0,009 ± 0,008) | 1,278 (-0,006 ± 0,021) | 1,121 (+0,001 ± 0,009) | 0,933 (-0,033 ± 0,019) | 0,902 (+0,021 ± 0,009) | 0,967 (+0,028 ± 0,028) | 0,498 (+0,096 ± 0,021) | 0,578 (-0,061 ± 0,031) |
| `completo_esp` | 1,243 (+0,011 ± 0,008) | 1,267 (-0,017 ± 0,019) | 1,120 (+0,000 ± 0,009) | 0,933 (-0,033 ± 0,019) | 0,908 (+0,028 ± 0,010) | 0,978 (+0,039 ± 0,025) | 0,525 (+0,123 ± 0,022) | 0,589 (-0,050 ± 0,033) |
| `completo_ap` | 1,236 (+0,004 ± 0,010) | 1,267 (-0,017 ± 0,019) | 1,122 (+0,002 ± 0,010) | 0,900 (-0,067 ± 0,027) | 0,901 (+0,020 ± 0,011) | 0,933 (-0,006 ± 0,019) | 0,480 (+0,078 ± 0,023) | 0,522 (-0,117 ± 0,029) |
| `completo_ancla` | 1,115 (-0,117 ± 0,012) | 1,200 (-0,083 ± 0,021) | 0,958 (-0,162 ± 0,013) | 0,600 (-0,367 ± 0,022) | 0,639 (-0,241 ± 0,013) | 0,667 (-0,272 ± 0,017) | 0,049 (-0,353 ± 0,024) | 0,122 (-0,517 ± 0,032) |
| `completo_min` | 1,244 (+0,012 ± 0,010) | 1,322 (+0,039 ± 0,023) | 1,131 (+0,011 ± 0,010) | 0,956 (-0,011 ± 0,025) | 0,903 (+0,022 ± 0,011) | 0,983 (+0,044 ± 0,028) | 0,462 (+0,060 ± 0,022) | 0,628 (-0,011 ± 0,033) |

### 2000 ticks, conjunto estres

| Candidata | mixto: H3a | mixto: H3b | fuerte: H3a | fuerte: H3b | racional: H3a | racional: H3b | reversores: H3a | reversores: H3b |
|---|---|---|---|---|---|---|---|---|
| `max_media` | 0,425 (+0,000 ± 0,000) | 0,556 (+0,000 ± 0,000) | 0,391 (+0,000 ± 0,000) | 0,600 (+0,000 ± 0,000) | 0,446 (+0,000 ± 0,000) | 0,622 (+0,000 ± 0,000) | 0,197 (+0,000 ± 0,000) | 0,494 (+0,000 ± 0,000) |
| `base` | 0,436 (+0,012 ± 0,018) | 0,567 (+0,011 ± 0,023) | 0,365 (-0,026 ± 0,022) | 0,544 (-0,056 ± 0,022) | 0,330 (-0,116 ± 0,018) | 0,567 (-0,056 ± 0,029) | 0,000 (-0,197 ± 0,021) | 0,333 (-0,161 ± 0,032) |
| `kalman` | 0,425 (+0,000 ± 0,013) | 0,539 (-0,017 ± 0,026) | 0,398 (+0,007 ± 0,017) | 0,533 (-0,067 ± 0,021) | 0,448 (+0,003 ± 0,012) | 0,600 (-0,022 ± 0,027) | 0,256 (+0,059 ± 0,022) | 0,350 (-0,144 ± 0,027) |
| `ejec_a` | 0,434 (+0,009 ± 0,005) | 0,589 (+0,033 ± 0,022) | 0,403 (+0,012 ± 0,006) | 0,667 (+0,067 ± 0,018) | 0,458 (+0,012 ± 0,005) | 0,667 (+0,044 ± 0,022) | 0,242 (+0,045 ± 0,011) | 0,550 (+0,056 ± 0,020) |
| `ejec_b` | 0,437 (+0,012 ± 0,008) | 0,594 (+0,039 ± 0,024) | 0,417 (+0,026 ± 0,009) | 0,667 (+0,067 ± 0,018) | 0,467 (+0,021 ± 0,007) | 0,667 (+0,044 ± 0,022) | 0,287 (+0,090 ± 0,014) | 0,550 (+0,056 ± 0,020) |
| `espera` | 0,419 (-0,006 ± 0,015) | 0,556 (+0,000 ± 0,025) | 0,390 (-0,001 ± 0,018) | 0,528 (-0,072 ± 0,026) | 0,420 (-0,026 ± 0,013) | 0,600 (-0,022 ± 0,025) | 0,234 (+0,037 ± 0,022) | 0,333 (-0,161 ± 0,025) |
| `aprendiz` | 0,431 (+0,006 ± 0,007) | 0,561 (+0,006 ± 0,016) | 0,404 (+0,012 ± 0,009) | 0,594 (-0,006 ± 0,015) | 0,455 (+0,009 ± 0,007) | 0,639 (+0,017 ± 0,017) | 0,210 (+0,013 ± 0,010) | 0,472 (-0,022 ± 0,017) |
| `aprendiz_patron` | 0,423 (-0,002 ± 0,005) | 0,550 (-0,006 ± 0,017) | 0,395 (+0,004 ± 0,007) | 0,583 (-0,017 ± 0,019) | 0,445 (-0,001 ± 0,006) | 0,622 (+0,000 ± 0,017) | 0,207 (+0,010 ± 0,011) | 0,444 (-0,050 ± 0,020) |
| `espera_e` | 0,427 (+0,002 ± 0,015) | 0,556 (+0,000 ± 0,022) | 0,402 (+0,010 ± 0,018) | 0,533 (-0,067 ± 0,021) | 0,429 (-0,017 ± 0,013) | 0,600 (-0,022 ± 0,025) | 0,250 (+0,053 ± 0,022) | 0,333 (-0,161 ± 0,030) |
| `fondo_rec` | 0,429 (+0,004 ± 0,011) | 0,544 (-0,011 ± 0,022) | 0,403 (+0,012 ± 0,014) | 0,556 (-0,044 ± 0,030) | 0,466 (+0,020 ± 0,010) | 0,661 (+0,039 ± 0,024) | 0,310 (+0,113 ± 0,019) | 0,433 (-0,061 ± 0,029) |
| `fondo_min` | 0,423 (-0,002 ± 0,005) | 0,561 (+0,006 ± 0,009) | 0,393 (+0,002 ± 0,006) | 0,606 (+0,006 ± 0,010) | 0,451 (+0,005 ± 0,005) | 0,633 (+0,011 ± 0,014) | 0,202 (+0,005 ± 0,008) | 0,494 (+0,000 ± 0,012) |
| `fondo_ancla` | 0,542 (+0,118 ± 0,015) | 0,689 (+0,133 ± 0,026) | 0,538 (+0,147 ± 0,018) | 0,667 (+0,067 ± 0,024) | 0,539 (+0,093 ± 0,015) | 0,711 (+0,089 ± 0,034) | 0,322 (+0,125 ± 0,024) | 0,389 (-0,106 ± 0,028) |
| `rec_e` | 0,434 (+0,010 ± 0,012) | 0,556 (+0,000 ± 0,023) | 0,415 (+0,024 ± 0,014) | 0,600 (+0,000 ± 0,023) | 0,476 (+0,030 ± 0,010) | 0,667 (+0,044 ± 0,024) | 0,331 (+0,134 ± 0,019) | 0,467 (-0,028 ± 0,024) |
| `min_e` | 0,431 (+0,007 ± 0,007) | 0,589 (+0,033 ± 0,021) | 0,404 (+0,012 ± 0,008) | 0,667 (+0,067 ± 0,018) | 0,463 (+0,017 ± 0,007) | 0,667 (+0,044 ± 0,022) | 0,250 (+0,053 ± 0,013) | 0,550 (+0,056 ± 0,020) |
| `completo` | 0,432 (+0,008 ± 0,011) | 0,556 (+0,000 ± 0,024) | 0,415 (+0,023 ± 0,013) | 0,600 (+0,000 ± 0,022) | 0,476 (+0,030 ± 0,009) | 0,667 (+0,044 ± 0,024) | 0,323 (+0,126 ± 0,018) | 0,467 (-0,028 ± 0,026) |
| `completo_s` | 0,428 (+0,004 ± 0,010) | 0,544 (-0,011 ± 0,021) | 0,405 (+0,014 ± 0,013) | 0,600 (+0,000 ± 0,029) | 0,467 (+0,021 ± 0,010) | 0,667 (+0,044 ± 0,024) | 0,299 (+0,102 ± 0,017) | 0,433 (-0,061 ± 0,028) |
| `completo_esp` | 0,426 (+0,002 ± 0,011) | 0,544 (-0,011 ± 0,023) | 0,401 (+0,009 ± 0,014) | 0,539 (-0,061 ± 0,027) | 0,461 (+0,015 ± 0,010) | 0,633 (+0,011 ± 0,028) | 0,302 (+0,105 ± 0,019) | 0,400 (-0,094 ± 0,019) |
| `completo_ap` | 0,434 (+0,009 ± 0,011) | 0,567 (+0,011 ± 0,025) | 0,423 (+0,031 ± 0,014) | 0,600 (+0,000 ± 0,020) | 0,490 (+0,044 ± 0,010) | 0,667 (+0,044 ± 0,026) | 0,332 (+0,135 ± 0,019) | 0,467 (-0,028 ± 0,026) |
| `completo_ancla` | 0,547 (+0,122 ± 0,015) | 0,689 (+0,133 ± 0,026) | 0,542 (+0,150 ± 0,018) | 0,667 (+0,067 ± 0,025) | 0,541 (+0,095 ± 0,015) | 0,733 (+0,111 ± 0,033) | 0,321 (+0,124 ± 0,025) | 0,378 (-0,117 ± 0,026) |
| `completo_min` | 0,436 (+0,012 ± 0,007) | 0,594 (+0,039 ± 0,023) | 0,408 (+0,017 ± 0,008) | 0,656 (+0,056 ± 0,017) | 0,463 (+0,017 ± 0,007) | 0,667 (+0,044 ± 0,022) | 0,252 (+0,055 ± 0,012) | 0,544 (+0,050 ± 0,019) |

### 20 000 ticks, interiores, conjunto estres

| Candidata | mixto: H3a | mixto: H3b | fuerte: H3a | fuerte: H3b | racional: H3a | racional: H3b | reversores: H3a | reversores: H3b |
|---|---|---|---|---|---|---|---|---|
| `max_media` | 0,961 (+0,000 ± 0,000) | 0,989 (+0,000 ± 0,000) | 0,770 (+0,000 ± 0,000) | 0,772 (+0,000 ± 0,000) | 0,685 (+0,000 ± 0,000) | 0,872 (+0,000 ± 0,000) | 0,400 (+0,000 ± 0,000) | 0,567 (+0,000 ± 0,000) |
| `base` | 0,764 (-0,198 ± 0,063) | 0,994 (+0,006 ± 0,077) | 0,613 (-0,158 ± 0,062) | 0,606 (-0,167 ± 0,053) | 0,331 (-0,354 ± 0,043) | 0,594 (-0,278 ± 0,066) | 0,000 (-0,400 ± 0,077) | 0,167 (-0,400 ± 0,055) |
| `kalman` | 0,953 (-0,008 ± 0,038) | 0,922 (-0,067 ± 0,060) | 0,757 (-0,013 ± 0,052) | 0,700 (-0,072 ± 0,055) | 0,668 (-0,017 ± 0,037) | 0,844 (-0,028 ± 0,046) | 0,437 (+0,038 ± 0,075) | 0,389 (-0,178 ± 0,062) |
| `ejec_a` | 0,975 (+0,013 ± 0,011) | 1,022 (+0,033 ± 0,040) | 0,798 (+0,027 ± 0,022) | 0,867 (+0,094 ± 0,048) | 0,695 (+0,010 ± 0,014) | 0,900 (+0,028 ± 0,035) | 0,499 (+0,099 ± 0,046) | 0,633 (+0,067 ± 0,052) |
| `ejec_b` | 0,978 (+0,017 ± 0,019) | 1,033 (+0,044 ± 0,047) | 0,803 (+0,033 ± 0,025) | 0,800 (+0,028 ± 0,047) | 0,695 (+0,010 ± 0,019) | 0,900 (+0,028 ± 0,034) | 0,520 (+0,120 ± 0,055) | 0,433 (-0,133 ± 0,062) |
| `espera` | 0,911 (-0,051 ± 0,048) | 0,978 (-0,011 ± 0,064) | 0,697 (-0,074 ± 0,049) | 0,622 (-0,150 ± 0,064) | 0,546 (-0,139 ± 0,035) | 0,756 (-0,117 ± 0,054) | 0,256 (-0,144 ± 0,075) | 0,244 (-0,322 ± 0,058) |
| `aprendiz` | 1,000 (+0,039 ± 0,064) | 0,989 (+0,000 ± 0,059) | 0,882 (+0,112 ± 0,061) | 0,922 (+0,150 ± 0,058) | 1,053 (+0,368 ± 0,056) | 1,056 (+0,183 ± 0,063) | 0,709 (+0,309 ± 0,087) | 0,822 (+0,256 ± 0,099) |
| `aprendiz_patron` | 0,958 (-0,004 ± 0,019) | 0,978 (-0,011 ± 0,045) | 0,753 (-0,017 ± 0,026) | 0,678 (-0,094 ± 0,047) | 0,681 (-0,004 ± 0,018) | 0,833 (-0,039 ± 0,044) | 0,403 (+0,003 ± 0,057) | 0,322 (-0,244 ± 0,070) |
| `espera_e` | 0,924 (-0,037 ± 0,048) | 1,000 (+0,011 ± 0,066) | 0,725 (-0,046 ± 0,048) | 0,667 (-0,106 ± 0,053) | 0,558 (-0,127 ± 0,033) | 0,778 (-0,094 ± 0,052) | 0,293 (-0,106 ± 0,076) | 0,256 (-0,311 ± 0,065) |
| `fondo_rec` | 0,959 (-0,002 ± 0,036) | 0,967 (-0,022 ± 0,053) | 0,778 (+0,008 ± 0,038) | 0,789 (+0,017 ± 0,054) | 0,716 (+0,031 ± 0,026) | 0,900 (+0,028 ± 0,045) | 0,502 (+0,102 ± 0,063) | 0,589 (+0,022 ± 0,060) |
| `fondo_min` | 1,006 (+0,045 ± 0,064) | 0,978 (-0,011 ± 0,061) | 0,854 (+0,083 ± 0,054) | 0,933 (+0,161 ± 0,059) | 1,067 (+0,382 ± 0,071) | 1,067 (+0,194 ± 0,064) | 0,676 (+0,276 ± 0,078) | 0,811 (+0,244 ± 0,083) |
| `fondo_ancla` | 0,923 (-0,038 ± 0,054) | 1,067 (+0,078 ± 0,072) | 0,773 (+0,003 ± 0,050) | 0,722 (-0,050 ± 0,060) | 0,503 (-0,182 ± 0,039) | 0,756 (-0,117 ± 0,059) | 0,157 (-0,242 ± 0,081) | 0,233 (-0,333 ± 0,053) |
| `rec_e` | 0,974 (+0,013 ± 0,036) | 0,978 (-0,011 ± 0,053) | 0,785 (+0,015 ± 0,040) | 0,822 (+0,050 ± 0,054) | 0,735 (+0,050 ± 0,024) | 0,911 (+0,039 ± 0,041) | 0,536 (+0,137 ± 0,063) | 0,633 (+0,067 ± 0,057) |
| `min_e` | 1,028 (+0,067 ± 0,065) | 1,011 (+0,022 ± 0,057) | 0,877 (+0,107 ± 0,054) | 1,011 (+0,239 ± 0,054) | 1,084 (+0,399 ± 0,069) | 1,111 (+0,239 ± 0,063) | 0,756 (+0,356 ± 0,083) | 0,922 (+0,356 ± 0,093) |
| `completo` | 0,996 (+0,035 ± 0,049) | 0,956 (-0,033 ± 0,050) | 0,830 (+0,059 ± 0,053) | 0,878 (+0,106 ± 0,059) | 0,884 (+0,199 ± 0,041) | 1,000 (+0,128 ± 0,051) | 0,694 (+0,294 ± 0,073) | 0,733 (+0,167 ± 0,069) |
| `completo_s` | 0,987 (+0,026 ± 0,049) | 0,967 (-0,022 ± 0,050) | 0,818 (+0,047 ± 0,050) | 0,844 (+0,072 ± 0,057) | 0,871 (+0,186 ± 0,042) | 0,978 (+0,106 ± 0,055) | 0,672 (+0,272 ± 0,072) | 0,689 (+0,122 ± 0,067) |
| `completo_esp` | 0,942 (-0,019 ± 0,032) | 0,911 (-0,078 ± 0,055) | 0,742 (-0,029 ± 0,042) | 0,700 (-0,072 ± 0,053) | 0,678 (-0,007 ± 0,029) | 0,844 (-0,028 ± 0,048) | 0,422 (+0,023 ± 0,068) | 0,433 (-0,133 ± 0,058) |
| `completo_ap` | 0,980 (+0,018 ± 0,058) | 0,967 (-0,022 ± 0,054) | 0,821 (+0,051 ± 0,058) | 0,867 (+0,094 ± 0,063) | 1,027 (+0,342 ± 0,071) | 1,033 (+0,161 ± 0,067) | 0,696 (+0,297 ± 0,079) | 0,778 (+0,211 ± 0,088) |
| `completo_ancla` | 0,937 (-0,025 ± 0,051) | 1,044 (+0,056 ± 0,073) | 0,778 (+0,007 ± 0,049) | 0,756 (-0,017 ± 0,059) | 0,527 (-0,158 ± 0,039) | 0,756 (-0,117 ± 0,057) | 0,185 (-0,215 ± 0,080) | 0,233 (-0,333 ± 0,057) |
| `completo_min` | 1,027 (+0,066 ± 0,058) | 1,033 (+0,044 ± 0,053) | 0,894 (+0,124 ± 0,058) | 0,956 (+0,183 ± 0,059) | 1,126 (+0,441 ± 0,063) | 1,122 (+0,250 ± 0,066) | 0,792 (+0,392 ± 0,083) | 0,900 (+0,333 ± 0,084) |

### 20 000 ticks, parada, conjunto estres

| Candidata | mixto: H3a | mixto: H3b | fuerte: H3a | fuerte: H3b | racional: H3a | racional: H3b | reversores: H3a | reversores: H3b |
|---|---|---|---|---|---|---|---|---|
| `max_media` | 0,400 (+0,000 ± 0,000) | 0,594 (+0,000 ± 0,000) | 0,360 (+0,000 ± 0,000) | 0,606 (+0,000 ± 0,000) | 0,409 (+0,000 ± 0,000) | 0,650 (+0,000 ± 0,000) | 0,213 (+0,000 ± 0,000) | 0,500 (+0,000 ± 0,000) |
| `base` | 0,421 (+0,022 ± 0,027) | 0,622 (+0,028 ± 0,029) | 0,358 (-0,003 ± 0,031) | 0,589 (-0,017 ± 0,033) | 0,351 (-0,058 ± 0,026) | 0,617 (-0,033 ± 0,034) | 0,000 (-0,213 ± 0,031) | 0,367 (-0,133 ± 0,039) |
| `kalman` | 0,408 (+0,009 ± 0,020) | 0,567 (-0,028 ± 0,029) | 0,361 (+0,000 ± 0,026) | 0,533 (-0,072 ± 0,035) | 0,407 (-0,002 ± 0,018) | 0,611 (-0,039 ± 0,030) | 0,275 (+0,062 ± 0,031) | 0,378 (-0,122 ± 0,033) |
| `ejec_a` | 0,414 (+0,014 ± 0,007) | 0,611 (+0,017 ± 0,026) | 0,370 (+0,009 ± 0,009) | 0,678 (+0,072 ± 0,026) | 0,415 (+0,006 ± 0,006) | 0,678 (+0,028 ± 0,022) | 0,269 (+0,056 ± 0,018) | 0,594 (+0,094 ± 0,029) |
| `ejec_b` | 0,418 (+0,019 ± 0,009) | 0,622 (+0,028 ± 0,026) | 0,383 (+0,022 ± 0,013) | 0,667 (+0,061 ± 0,024) | 0,422 (+0,013 ± 0,009) | 0,689 (+0,039 ± 0,023) | 0,301 (+0,088 ± 0,021) | 0,550 (+0,050 ± 0,029) |
| `espera` | 0,419 (+0,019 ± 0,021) | 0,578 (-0,017 ± 0,028) | 0,357 (-0,003 ± 0,025) | 0,533 (-0,072 ± 0,030) | 0,400 (-0,009 ± 0,021) | 0,622 (-0,028 ± 0,030) | 0,236 (+0,022 ± 0,034) | 0,311 (-0,189 ± 0,035) |
| `aprendiz` | 0,429 (+0,029 ± 0,019) | 0,606 (+0,011 ± 0,027) | 0,392 (+0,032 ± 0,023) | 0,622 (+0,017 ± 0,028) | 0,468 (+0,059 ± 0,022) | 0,689 (+0,039 ± 0,023) | 0,319 (+0,105 ± 0,037) | 0,517 (+0,017 ± 0,030) |
| `aprendiz_patron` | 0,409 (+0,009 ± 0,011) | 0,606 (+0,011 ± 0,021) | 0,362 (+0,001 ± 0,013) | 0,572 (-0,033 ± 0,024) | 0,407 (-0,002 ± 0,011) | 0,644 (-0,006 ± 0,020) | 0,247 (+0,033 ± 0,021) | 0,400 (-0,100 ± 0,026) |
| `espera_e` | 0,425 (+0,026 ± 0,021) | 0,600 (+0,006 ± 0,027) | 0,371 (+0,011 ± 0,024) | 0,544 (-0,061 ± 0,033) | 0,408 (-0,001 ± 0,021) | 0,656 (+0,006 ± 0,029) | 0,263 (+0,050 ± 0,033) | 0,356 (-0,144 ± 0,037) |
| `fondo_rec` | 0,404 (+0,004 ± 0,016) | 0,578 (-0,017 ± 0,026) | 0,362 (+0,002 ± 0,023) | 0,550 (-0,056 ± 0,029) | 0,425 (+0,016 ± 0,016) | 0,644 (-0,006 ± 0,025) | 0,281 (+0,068 ± 0,030) | 0,411 (-0,089 ± 0,030) |
| `fondo_min` | 0,393 (-0,007 ± 0,018) | 0,594 (+0,000 ± 0,022) | 0,360 (-0,001 ± 0,019) | 0,589 (-0,017 ± 0,025) | 0,433 (+0,023 ± 0,019) | 0,644 (-0,006 ± 0,024) | 0,259 (+0,045 ± 0,032) | 0,478 (-0,022 ± 0,032) |
| `fondo_ancla` | 0,450 (+0,050 ± 0,025) | 0,644 (+0,050 ± 0,032) | 0,428 (+0,068 ± 0,029) | 0,567 (-0,039 ± 0,036) | 0,386 (-0,023 ± 0,024) | 0,600 (-0,050 ± 0,030) | 0,160 (-0,054 ± 0,036) | 0,256 (-0,244 ± 0,030) |
| `rec_e` | 0,408 (+0,008 ± 0,017) | 0,583 (-0,011 ± 0,026) | 0,372 (+0,012 ± 0,023) | 0,567 (-0,039 ± 0,031) | 0,435 (+0,026 ± 0,016) | 0,667 (+0,017 ± 0,028) | 0,304 (+0,091 ± 0,030) | 0,428 (-0,072 ± 0,034) |
| `min_e` | 0,410 (+0,011 ± 0,018) | 0,617 (+0,022 ± 0,025) | 0,370 (+0,010 ± 0,018) | 0,650 (+0,044 ± 0,027) | 0,442 (+0,033 ± 0,020) | 0,678 (+0,028 ± 0,028) | 0,305 (+0,092 ± 0,031) | 0,550 (+0,050 ± 0,036) |
| `completo` | 0,415 (+0,015 ± 0,018) | 0,600 (+0,006 ± 0,024) | 0,377 (+0,017 ± 0,020) | 0,606 (+0,000 ± 0,031) | 0,449 (+0,040 ± 0,018) | 0,678 (+0,028 ± 0,027) | 0,336 (+0,122 ± 0,028) | 0,494 (-0,006 ± 0,034) |
| `completo_s` | 0,409 (+0,009 ± 0,017) | 0,589 (-0,006 ± 0,025) | 0,367 (+0,006 ± 0,020) | 0,572 (-0,033 ± 0,028) | 0,444 (+0,035 ± 0,018) | 0,656 (+0,006 ± 0,028) | 0,313 (+0,100 ± 0,030) | 0,467 (-0,033 ± 0,033) |
| `completo_esp` | 0,404 (+0,004 ± 0,018) | 0,556 (-0,039 ± 0,027) | 0,352 (-0,009 ± 0,022) | 0,533 (-0,072 ± 0,030) | 0,423 (+0,014 ± 0,016) | 0,639 (-0,011 ± 0,027) | 0,283 (+0,069 ± 0,030) | 0,400 (-0,100 ± 0,028) |
| `completo_ap` | 0,409 (+0,009 ± 0,018) | 0,589 (-0,006 ± 0,027) | 0,365 (+0,005 ± 0,022) | 0,561 (-0,044 ± 0,032) | 0,460 (+0,051 ± 0,019) | 0,678 (+0,028 ± 0,028) | 0,332 (+0,119 ± 0,031) | 0,467 (-0,033 ± 0,037) |
| `completo_ancla` | 0,451 (+0,052 ± 0,025) | 0,656 (+0,061 ± 0,030) | 0,429 (+0,068 ± 0,028) | 0,578 (-0,028 ± 0,036) | 0,392 (-0,017 ± 0,022) | 0,600 (-0,050 ± 0,029) | 0,177 (-0,036 ± 0,038) | 0,267 (-0,233 ± 0,031) |
| `completo_min` | 0,426 (+0,026 ± 0,019) | 0,628 (+0,033 ± 0,025) | 0,393 (+0,032 ± 0,020) | 0,656 (+0,050 ± 0,027) | 0,454 (+0,045 ± 0,020) | 0,706 (+0,056 ± 0,024) | 0,347 (+0,133 ± 0,030) | 0,578 (+0,078 ± 0,033) |

## 5. El signo en cada evidencia por separado (campo mixto)

Diferencia de puntos esperados contra `max_media` en el remuestreo y en las familias plausibles. Una mejora vale como evidencia si el signo se repite en las dos.

### 2000 ticks

| Candidata | H1: remuestreo | H1: plausibles | H3a: remuestreo | H3a: plausibles | H3b: remuestreo | H3b: plausibles | Mismo signo en H3a y H3b |
|---|---|---|---|---|---|---|---|
| `base` | -55 ± 11 | -136 ± 11 | -0,026 ± 0,005 | -0,053 ± 0,003 | -0,019 ± 0,005 | -0,052 ± 0,004 | sí |
| `kalman` | +40 ± 6 | +6 ± 7 | +0,003 ± 0,003 | -0,012 ± 0,002 | +0,017 ± 0,003 | -0,005 ± 0,002 | no |
| `ejec_a` | +12 ± 0 | +17 ± 0 | +0,007 ± 0,000 | +0,008 ± 0,000 | +0,025 ± 0,001 | +0,029 ± 0,001 | sí |
| `ejec_b` | +22 ± 1 | +26 ± 1 | +0,012 ± 0,001 | +0,012 ± 0,000 | +0,030 ± 0,001 | +0,032 ± 0,001 | sí |
| `espera` | +158 ± 8 | -70 ± 8 | +0,042 ± 0,003 | -0,033 ± 0,002 | +0,062 ± 0,004 | -0,026 ± 0,003 | no |
| `aprendiz` | +0 ± 1 | -2 ± 1 | -0,000 ± 0,000 | -0,000 ± 0,000 | +0,000 ± 0,000 | +0,000 ± 0,000 | sí |
| `aprendiz_patron` | +7 ± 2 | -4 ± 1 | -0,000 ± 0,001 | -0,003 ± 0,000 | +0,001 ± 0,001 | -0,003 ± 0,001 | no |
| `espera_e` | +167 ± 8 | -54 ± 8 | +0,047 ± 0,003 | -0,025 ± 0,002 | +0,068 ± 0,004 | -0,016 ± 0,003 | no |
| `fondo_rec` | -16 ± 3 | +30 ± 5 | -0,010 ± 0,001 | +0,003 ± 0,001 | -0,003 ± 0,002 | +0,013 ± 0,002 | no |
| `fondo_min` | +0 ± 1 | +2 ± 1 | -0,000 ± 0,000 | -0,000 ± 0,000 | +0,000 ± 0,000 | -0,000 ± 0,000 | no |
| `fondo_ancla` | -198 ± 7 | -148 ± 14 | -0,040 ± 0,002 | -0,024 ± 0,002 | -0,028 ± 0,003 | -0,014 ± 0,002 | sí |
| `rec_e` | -9 ± 3 | +41 ± 5 | -0,006 ± 0,001 | +0,008 ± 0,001 | +0,003 ± 0,002 | +0,022 ± 0,002 | no |
| `min_e` | +13 ± 1 | +19 ± 1 | +0,007 ± 0,000 | +0,008 ± 0,000 | +0,025 ± 0,001 | +0,028 ± 0,001 | sí |
| `completo` | -9 ± 3 | +35 ± 4 | -0,004 ± 0,001 | +0,008 ± 0,001 | +0,005 ± 0,002 | +0,021 ± 0,001 | no |
| `completo_s` | -16 ± 3 | +25 ± 4 | -0,009 ± 0,001 | +0,002 ± 0,001 | -0,002 ± 0,002 | +0,012 ± 0,001 | no |
| `completo_esp` | +10 ± 4 | +1 ± 4 | +0,001 ± 0,002 | -0,010 ± 0,001 | +0,011 ± 0,002 | -0,006 ± 0,002 | no |
| `completo_ap` | -12 ± 3 | +32 ± 5 | -0,006 ± 0,001 | +0,005 ± 0,001 | -0,000 ± 0,002 | +0,016 ± 0,002 | no |
| `completo_ancla` | -198 ± 7 | -148 ± 14 | -0,040 ± 0,002 | -0,024 ± 0,002 | -0,028 ± 0,003 | -0,014 ± 0,002 | sí |
| `completo_min` | +12 ± 1 | +16 ± 1 | +0,007 ± 0,000 | +0,008 ± 0,000 | +0,025 ± 0,001 | +0,028 ± 0,001 | sí |

### 20 000 ticks, interiores

| Candidata | H1: remuestreo | H1: plausibles | H3a: remuestreo | H3a: plausibles | H3b: remuestreo | H3b: plausibles | Mismo signo en H3a y H3b |
|---|---|---|---|---|---|---|---|
| `base` | -2 778 ± 142 | -3 754 ± 200 | -0,096 ± 0,005 | -0,151 ± 0,006 | -0,063 ± 0,004 | -0,093 ± 0,005 | sí |
| `kalman` | +859 ± 74 | +46 ± 101 | -0,004 ± 0,002 | -0,022 ± 0,002 | +0,025 ± 0,003 | +0,000 ± 0,003 | sí |
| `ejec_a` | +155 ± 4 | +197 ± 5 | +0,005 ± 0,000 | +0,008 ± 0,000 | +0,049 ± 0,001 | +0,053 ± 0,001 | sí |
| `ejec_b` | +291 ± 9 | +288 ± 11 | +0,008 ± 0,001 | +0,012 ± 0,001 | +0,039 ± 0,002 | +0,044 ± 0,002 | sí |
| `espera` | +2 044 ± 96 | -1 525 ± 119 | +0,029 ± 0,003 | -0,067 ± 0,003 | +0,064 ± 0,003 | -0,039 ± 0,003 | no |
| `aprendiz` | -596 ± 62 | -15 ± 95 | -0,037 ± 0,002 | -0,019 ± 0,003 | -0,018 ± 0,002 | -0,002 ± 0,003 | sí |
| `aprendiz_patron` | +298 ± 29 | -234 ± 33 | -0,001 ± 0,001 | -0,014 ± 0,001 | +0,013 ± 0,002 | -0,013 ± 0,002 | no |
| `espera_e` | +2 161 ± 96 | -1 340 ± 118 | +0,032 ± 0,003 | -0,055 ± 0,003 | +0,066 ± 0,003 | -0,028 ± 0,003 | no |
| `fondo_rec` | +177 ± 48 | +846 ± 70 | -0,014 ± 0,001 | +0,012 ± 0,001 | +0,001 ± 0,002 | +0,031 ± 0,002 | no |
| `fondo_min` | -351 ± 79 | +1 508 ± 147 | -0,040 ± 0,003 | +0,002 ± 0,003 | -0,022 ± 0,002 | +0,014 ± 0,003 | no |
| `fondo_ancla` | -3 801 ± 104 | -3 694 ± 170 | -0,150 ± 0,003 | -0,122 ± 0,003 | -0,090 ± 0,003 | -0,065 ± 0,003 | sí |
| `rec_e` | +289 ± 49 | +1 017 ± 71 | -0,009 ± 0,001 | +0,019 ± 0,001 | +0,008 ± 0,002 | +0,041 ± 0,002 | no |
| `min_e` | -187 ± 79 | +1 735 ± 148 | -0,033 ± 0,003 | +0,012 ± 0,003 | +0,001 ± 0,003 | +0,036 ± 0,003 | no |
| `completo` | +177 ± 43 | +905 ± 72 | -0,011 ± 0,001 | +0,015 ± 0,002 | +0,005 ± 0,002 | +0,033 ± 0,002 | no |
| `completo_s` | +82 ± 43 | +762 ± 71 | -0,016 ± 0,001 | +0,009 ± 0,002 | -0,002 ± 0,002 | +0,025 ± 0,003 | no |
| `completo_esp` | +533 ± 50 | +509 ± 63 | +0,001 ± 0,002 | -0,001 ± 0,002 | +0,020 ± 0,002 | +0,013 ± 0,002 | no |
| `completo_ap` | -111 ± 52 | +1 306 ± 112 | -0,027 ± 0,002 | +0,014 ± 0,002 | -0,012 ± 0,002 | +0,025 ± 0,003 | no |
| `completo_ancla` | -3 907 ± 106 | -3 778 ± 173 | -0,156 ± 0,003 | -0,128 ± 0,003 | -0,094 ± 0,003 | -0,069 ± 0,003 | sí |
| `completo_min` | -109 ± 57 | +1 035 ± 121 | -0,020 ± 0,002 | +0,009 ± 0,003 | +0,007 ± 0,002 | +0,030 ± 0,003 | no |

### 20 000 ticks, parada

| Candidata | H1: remuestreo | H1: plausibles | H3a: remuestreo | H3a: plausibles | H3b: remuestreo | H3b: plausibles | Mismo signo en H3a y H3b |
|---|---|---|---|---|---|---|---|
| `base` | -1 513 ± 88 | -2 285 ± 118 | -0,049 ± 0,004 | -0,102 ± 0,004 | -0,032 ± 0,004 | -0,068 ± 0,004 | sí |
| `kalman` | +599 ± 45 | +8 ± 58 | -0,003 ± 0,002 | -0,020 ± 0,002 | +0,024 ± 0,002 | -0,005 ± 0,003 | no |
| `ejec_a` | +111 ± 2 | +145 ± 3 | +0,005 ± 0,000 | +0,008 ± 0,000 | +0,047 ± 0,001 | +0,049 ± 0,001 | sí |
| `ejec_b` | +213 ± 5 | +226 ± 7 | +0,009 ± 0,000 | +0,013 ± 0,000 | +0,040 ± 0,001 | +0,044 ± 0,001 | sí |
| `espera` | +1 721 ± 58 | -962 ± 73 | +0,050 ± 0,002 | -0,050 ± 0,003 | +0,081 ± 0,003 | -0,029 ± 0,003 | no |
| `aprendiz` | -287 ± 41 | +17 ± 54 | -0,022 ± 0,002 | -0,011 ± 0,002 | -0,006 ± 0,002 | +0,003 ± 0,002 | no |
| `aprendiz_patron` | +230 ± 18 | -149 ± 20 | +0,002 ± 0,001 | -0,011 ± 0,001 | +0,016 ± 0,002 | -0,011 ± 0,002 | no |
| `espera_e` | +1 807 ± 58 | -827 ± 72 | +0,054 ± 0,002 | -0,040 ± 0,003 | +0,085 ± 0,003 | -0,019 ± 0,003 | no |
| `fondo_rec` | +37 ± 29 | +530 ± 41 | -0,022 ± 0,001 | +0,004 ± 0,001 | -0,006 ± 0,002 | +0,019 ± 0,002 | no |
| `fondo_min` | -284 ± 46 | +875 ± 88 | -0,034 ± 0,002 | -0,005 ± 0,002 | -0,017 ± 0,002 | +0,006 ± 0,002 | no |
| `fondo_ancla` | -3 535 ± 73 | -2 920 ± 104 | -0,194 ± 0,003 | -0,124 ± 0,003 | -0,114 ± 0,003 | -0,069 ± 0,003 | sí |
| `rec_e` | +119 ± 30 | +656 ± 42 | -0,017 ± 0,001 | +0,011 ± 0,001 | +0,001 ± 0,002 | +0,028 ± 0,002 | no |
| `min_e` | -167 ± 46 | +1 040 ± 89 | -0,028 ± 0,002 | +0,004 ± 0,002 | +0,008 ± 0,002 | +0,031 ± 0,002 | no |
| `completo` | +99 ± 27 | +598 ± 41 | -0,014 ± 0,001 | +0,010 ± 0,001 | +0,002 ± 0,002 | +0,026 ± 0,002 | no |
| `completo_s` | +26 ± 27 | +494 ± 41 | -0,018 ± 0,001 | +0,004 ± 0,001 | -0,004 ± 0,002 | +0,018 ± 0,002 | no |
| `completo_esp` | +372 ± 31 | +328 ± 38 | -0,002 ± 0,001 | -0,007 ± 0,001 | +0,017 ± 0,002 | +0,001 ± 0,002 | sí |
| `completo_ap` | -93 ± 31 | +809 ± 62 | -0,026 ± 0,001 | +0,006 ± 0,002 | -0,012 ± 0,002 | +0,016 ± 0,002 | no |
| `completo_ancla` | -3 596 ± 74 | -2 972 ± 105 | -0,197 ± 0,003 | -0,129 ± 0,003 | -0,116 ± 0,003 | -0,073 ± 0,003 | sí |
| `completo_min` | -57 ± 33 | +635 ± 68 | -0,012 ± 0,002 | +0,007 ± 0,002 | +0,016 ± 0,002 | +0,030 ± 0,002 | no |

