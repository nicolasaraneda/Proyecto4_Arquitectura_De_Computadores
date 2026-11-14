## Síntesis jerárquica: área por módulo

### base_jer (Pipeline=0, DataWords=4)

| módulo | celdas propias | flip-flops propios | área con submódulos (um2) | de eso, flip-flops (um2) | % del total |
|---|---|---|---|---|---|
| asic_top | 3 | 2 | 143647 | 57242 | 100.0 |
| pochoco_soc_asic | 90 | 2 | 143489 | 57093 | 99.9 |
| espino_core | 0 | 0 | 108487 | 39632 | 75.5 |
| espino_register_file | 1849 | 544 | 75605 | 34631 | 52.6 |
| pochoco_mem_asic | 512 | 192 | 23045 | 12223 | 16.0 |
| espino_id_stage | 577 | 1 | 21559 | 75 | 15.0 |
| espino_alu | 589 | 0 | 10153 | 0 | 7.1 |
| espino_if_stage | 249 | 65 | 8511 | 4851 | 5.9 |
| pochoco_spi_slave | 190 | 52 | 6276 | 3894 | 4.4 |
| pochoco_periph | 144 | 16 | 3122 | 1194 | 2.2 |
| pochoco_rom | 167 | 0 | 2755 | 0 | 1.9 |
| espino_load_store_unit | 218 | 1 | 2742 | 75 | 1.9 |
| espino_decoder | 156 | 0 | 1956 | 0 | 1.4 |
| espino_controller | 5 | 0 | 70 | 0 | 0.0 |

Total: 4749 celdas, 875 flip-flops, 143647 um2, de los cuales 57242 um2 (39.8 %) son flip-flops.

### seg_jer (Pipeline=2, DataWords=4)

| módulo | celdas propias | flip-flops propios | área con submódulos (um2) | de eso, flip-flops (um2) | % del total |
|---|---|---|---|---|---|
| asic_top | 3 | 2 | 145735 | 60080 | 100.0 |
| pochoco_soc_asic | 90 | 2 | 145577 | 59931 | 99.9 |
| espino_core | 0 | 0 | 113650 | 44508 | 78.0 |
| espino_register_file | 2074 | 578 | 81132 | 36796 | 55.7 |
| espino_id_stage | 527 | 93 | 26435 | 5920 | 18.1 |
| pochoco_mem_asic | 432 | 160 | 19970 | 10186 | 13.7 |
| espino_alu | 589 | 0 | 10153 | 0 | 7.0 |
| pochoco_spi_slave | 190 | 52 | 6276 | 3894 | 4.3 |
| espino_if_stage | 134 | 23 | 3271 | 1717 | 2.2 |
| pochoco_periph | 144 | 16 | 3122 | 1194 | 2.1 |
| pochoco_rom | 167 | 0 | 2755 | 0 | 1.9 |
| espino_load_store_unit | 218 | 1 | 2742 | 75 | 1.9 |
| espino_decoder | 156 | 0 | 1956 | 0 | 1.3 |
| espino_controller | 5 | 0 | 70 | 0 | 0.0 |

Total: 4729 celdas, 927 flip-flops, 145735 um2, de los cuales 60080 um2 (41.2 %) son flip-flops.
