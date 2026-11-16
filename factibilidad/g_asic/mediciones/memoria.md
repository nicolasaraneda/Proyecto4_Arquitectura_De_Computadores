## Memoria de datos: flip-flops contra macros SRAM

RAM de datos en flip-flops, medida con síntesis jerárquica del macro (Espino base, 40 ns). El área de la RAM es la del módulo `pochoco_mem_asic` menos la de `pochoco_rom`; incluye el registro de lectura y, en el Espino base, el registro de instrucción (32 flip-flops).

| corrida | palabras de 32 bits | flip-flops del módulo | área de la RAM (um2) | um2 por palabra | área total del macro (um2) |
|---|---|---|---|---|---|
| base_dw4 | 4 | 192 | 20290 | 5073 | 143647 |
| base_dw16 | 16 | 576 | 66681 | 4168 | 189891 |
| base_dw64 | 64 | 2112 | 236118 | 3689 | 359405 |
| base_dw128 | 128 | 4160 | 467971 | 3656 | 591104 |
| base_dw256 | 256 | 8256 | 1003072 | 3918 | 1126171 |
| base_dw512 | 512 | 16448 | 1979429 | 3866 | 2102527 |

Macros SRAM del PDK instalado (`.ciel/ciel/gf180mcu/versions/54435919abffb937387ec956209f9cf5fd2dfbee/gf180mcuD/libs.ref/gf180mcu_fd_ip_sram`, tamaño de la línea SIZE del LEF). Son de 8 bits y un solo puerto, con lectura sincrónica: una memoria de 32 bits usa 4.

| macro | palabras | ancho (bits) | tamaño (um) | área de una (um2) | área de 4, para 32 bits (um2) | um2 por palabra de 32 bits |
|---|---|---|---|---|---|---|
| gf180mcu_fd_ip_sram__sram64x8m8wm1 | 64 | 8 | 431.86 x 232.88 | 100572 | 402286 | 6286 |
| gf180mcu_fd_ip_sram__sram128x8m8wm1 | 128 | 8 | 431.86 x 268.88 | 116119 | 464474 | 3629 |
| gf180mcu_fd_ip_sram__sram256x8m8wm1 | 256 | 8 | 431.86 x 340.88 | 147212 | 588850 | 2300 |
| gf180mcu_fd_ip_sram__sram512x8m8wm1 | 512 | 8 | 431.86 x 484.88 | 209400 | 837601 | 1636 |

Comparación con el mismo número de palabras (flip-flops medidos contra 4 macros):

| palabras | flip-flops (um2) | 4 macros SRAM (um2) | más chico |
|---|---|---|---|
| 64 | 236118 | 402286 | flip-flops |
| 128 | 467971 | 464474 | macros SRAM |
| 256 | 1003072 | 588850 | macros SRAM |
| 512 | 1979429 | 837601 | macros SRAM |
