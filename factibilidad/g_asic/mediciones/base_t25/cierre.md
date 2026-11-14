Criterios de cierre de `factibilidad/g_asic/runs/base_t25`

| criterio | valor | cumple |
|---|---|---|
| flujo completo (final/metrics.json) | sí | sí |
| DRC Magic (magic__drc_error__count) | 0 | sí |
| DRC KLayout (klayout__drc_error__count) | no corrido en el flujo | sí |
| LVS (design__lvs_error__count) | 0 | sí |
| antena (antenna__violating__nets) | 0 | sí |
| setup WNS peor esquina (ns) | 1.402 | sí |
| setup TNS peor esquina (ns) | 0.000 | sí |
|   setup max_ff_n40C_5v50: WNS / TNS | 16.341 / 0.000 | sí |
|   setup max_ss_125C_4v50: WNS / TNS | 1.402 / 0.000 | sí |
|   setup max_tt_025C_5v00: WNS / TNS | 12.042 / 0.000 | sí |
|   setup min_ff_n40C_5v50: WNS / TNS | 16.448 / 0.000 | sí |
|   setup min_ss_125C_4v50: WNS / TNS | 2.118 / 0.000 | sí |
|   setup min_tt_025C_5v00: WNS / TNS | 12.452 / 0.000 | sí |
|   setup nom_ff_n40C_5v50: WNS / TNS | 16.400 / 0.000 | sí |
|   setup nom_ss_125C_4v50: WNS / TNS | 1.794 / 0.000 | sí |
|   setup nom_tt_025C_5v00: WNS / TNS | 12.269 / 0.000 | sí |
| hold WNS peor esquina (ns) | 0.100 | sí |
| hold TNS peor esquina (ns) | 0.000 | sí |
|   hold max_ff_n40C_5v50: WNS / TNS | 0.100 / 0.000 | sí |
|   hold max_ss_125C_4v50: WNS / TNS | 0.870 / 0.000 | sí |
|   hold max_tt_025C_5v00: WNS / TNS | 0.331 / 0.000 | sí |
|   hold min_ff_n40C_5v50: WNS / TNS | 0.108 / 0.000 | sí |
|   hold min_ss_125C_4v50: WNS / TNS | 0.887 / 0.000 | sí |
|   hold min_tt_025C_5v00: WNS / TNS | 0.343 / 0.000 | sí |
|   hold nom_ff_n40C_5v50: WNS / TNS | 0.105 / 0.000 | sí |
|   hold nom_ss_125C_4v50: WNS / TNS | 0.881 / 0.000 | sí |
|   hold nom_tt_025C_5v00: WNS / TNS | 0.338 / 0.000 | sí |

| dato informativo | valor |
|---|---|
| max slew (design__max_slew_violation__count, peor esquina) | 0 |
| max capacitancia (design__max_cap_violation__count, peor esquina) | 1 |
| área del die (µm²) | 359332 |
| utilización | 0.568 |

**Resultado: CIERRA**
