Criterios de cierre de `factibilidad/g_asic/runs/seg_t25`

| criterio | valor | cumple |
|---|---|---|
| flujo completo (final/metrics.json) | sí | sí |
| DRC Magic (magic__drc_error__count) | 0 | sí |
| DRC KLayout (klayout__drc_error__count) | no corrido en el flujo | sí |
| LVS (design__lvs_error__count) | 0 | sí |
| antena (antenna__violating__nets) | 1 | NO |
| setup WNS peor esquina (ns) | 1.702 | sí |
| setup TNS peor esquina (ns) | 0.000 | sí |
|   setup max_ff_n40C_5v50: WNS / TNS | 16.139 / 0.000 | sí |
|   setup max_ss_125C_4v50: WNS / TNS | 1.702 / 0.000 | sí |
|   setup max_tt_025C_5v00: WNS / TNS | 12.116 / 0.000 | sí |
|   setup min_ff_n40C_5v50: WNS / TNS | 16.294 / 0.000 | sí |
|   setup min_ss_125C_4v50: WNS / TNS | 2.403 / 0.000 | sí |
|   setup min_tt_025C_5v00: WNS / TNS | 12.515 / 0.000 | sí |
|   setup nom_ff_n40C_5v50: WNS / TNS | 16.226 / 0.000 | sí |
|   setup nom_ss_125C_4v50: WNS / TNS | 2.084 / 0.000 | sí |
|   setup nom_tt_025C_5v00: WNS / TNS | 12.333 / 0.000 | sí |
| hold WNS peor esquina (ns) | 0.118 | sí |
| hold TNS peor esquina (ns) | 0.000 | sí |
|   hold max_ff_n40C_5v50: WNS / TNS | 0.118 / 0.000 | sí |
|   hold max_ss_125C_4v50: WNS / TNS | 0.922 / 0.000 | sí |
|   hold max_tt_025C_5v00: WNS / TNS | 0.361 / 0.000 | sí |
|   hold min_ff_n40C_5v50: WNS / TNS | 0.119 / 0.000 | sí |
|   hold min_ss_125C_4v50: WNS / TNS | 0.921 / 0.000 | sí |
|   hold min_tt_025C_5v00: WNS / TNS | 0.360 / 0.000 | sí |
|   hold nom_ff_n40C_5v50: WNS / TNS | 0.119 / 0.000 | sí |
|   hold nom_ss_125C_4v50: WNS / TNS | 0.921 / 0.000 | sí |
|   hold nom_tt_025C_5v00: WNS / TNS | 0.361 / 0.000 | sí |

| dato informativo | valor |
|---|---|
| max slew (design__max_slew_violation__count, peor esquina) | 4 |
| max capacitancia (design__max_cap_violation__count, peor esquina) | 1 |
| área del die (µm²) | 304298 |
| utilización | 0.577 |

**Resultado: NO CIERRA**
