Criterios de cierre de `factibilidad/g_asic/runs/seg_t30`

| criterio | valor | cumple |
|---|---|---|
| flujo completo (final/metrics.json) | sí | sí |
| DRC Magic (magic__drc_error__count) | 0 | sí |
| DRC KLayout (klayout__drc_error__count) | no corrido en el flujo | sí |
| LVS (design__lvs_error__count) | 0 | sí |
| antena (antenna__violating__nets) | 0 | sí |
| setup WNS peor esquina (ns) | 2.466 | sí |
| setup TNS peor esquina (ns) | 0.000 | sí |
|   setup max_ff_n40C_5v50: WNS / TNS | 20.183 / 0.000 | sí |
|   setup max_ss_125C_4v50: WNS / TNS | 2.466 / 0.000 | sí |
|   setup max_tt_025C_5v00: WNS / TNS | 14.778 / 0.000 | sí |
|   setup min_ff_n40C_5v50: WNS / TNS | 20.318 / 0.000 | sí |
|   setup min_ss_125C_4v50: WNS / TNS | 3.025 / 0.000 | sí |
|   setup min_tt_025C_5v00: WNS / TNS | 15.094 / 0.000 | sí |
|   setup nom_ff_n40C_5v50: WNS / TNS | 20.261 / 0.000 | sí |
|   setup nom_ss_125C_4v50: WNS / TNS | 2.775 / 0.000 | sí |
|   setup nom_tt_025C_5v00: WNS / TNS | 14.949 / 0.000 | sí |
| hold WNS peor esquina (ns) | 0.113 | sí |
| hold TNS peor esquina (ns) | 0.000 | sí |
|   hold max_ff_n40C_5v50: WNS / TNS | 0.113 / 0.000 | sí |
|   hold max_ss_125C_4v50: WNS / TNS | 0.898 / 0.000 | sí |
|   hold max_tt_025C_5v00: WNS / TNS | 0.349 / 0.000 | sí |
|   hold min_ff_n40C_5v50: WNS / TNS | 0.116 / 0.000 | sí |
|   hold min_ss_125C_4v50: WNS / TNS | 0.905 / 0.000 | sí |
|   hold min_tt_025C_5v00: WNS / TNS | 0.353 / 0.000 | sí |
|   hold nom_ff_n40C_5v50: WNS / TNS | 0.114 / 0.000 | sí |
|   hold nom_ss_125C_4v50: WNS / TNS | 0.902 / 0.000 | sí |
|   hold nom_tt_025C_5v00: WNS / TNS | 0.351 / 0.000 | sí |

| dato informativo | valor |
|---|---|
| max slew (design__max_slew_violation__count, peor esquina) | 10 |
| max capacitancia (design__max_cap_violation__count, peor esquina) | 1 |
| área del die (µm²) | 304298 |
| utilización | 0.575 |

**Resultado: CIERRA**
