Criterios de cierre de `factibilidad/g_asic/runs/base_t22`

| criterio | valor | cumple |
|---|---|---|
| flujo completo (final/metrics.json) | sí | sí |
| DRC Magic (magic__drc_error__count) | 0 | sí |
| DRC KLayout (klayout__drc_error__count) | no corrido en el flujo | sí |
| LVS (design__lvs_error__count) | 0 | sí |
| antena (antenna__violating__nets) | 0 | sí |
| setup WNS peor esquina (ns) | -0.479 | NO |
| setup TNS peor esquina (ns) | -39.483 | NO |
|   setup max_ff_n40C_5v50: WNS / TNS | 13.900 / 0.000 | sí |
|   setup max_ss_125C_4v50: WNS / TNS | -0.479 / -39.483 | NO |
|   setup max_tt_025C_5v00: WNS / TNS | 9.671 / 0.000 | sí |
|   setup min_ff_n40C_5v50: WNS / TNS | 14.019 / 0.000 | sí |
|   setup min_ss_125C_4v50: WNS / TNS | 0.072 / 0.000 | sí |
|   setup min_tt_025C_5v00: WNS / TNS | 9.990 / 0.000 | sí |
|   setup nom_ff_n40C_5v50: WNS / TNS | 13.964 / 0.000 | sí |
|   setup nom_ss_125C_4v50: WNS / TNS | -0.165 / -2.695 | NO |
|   setup nom_tt_025C_5v00: WNS / TNS | 9.864 / 0.000 | sí |
| hold WNS peor esquina (ns) | 0.107 | sí |
| hold TNS peor esquina (ns) | 0.000 | sí |
|   hold max_ff_n40C_5v50: WNS / TNS | 0.107 / 0.000 | sí |
|   hold max_ss_125C_4v50: WNS / TNS | 0.883 / 0.000 | sí |
|   hold max_tt_025C_5v00: WNS / TNS | 0.340 / 0.000 | sí |
|   hold min_ff_n40C_5v50: WNS / TNS | 0.111 / 0.000 | sí |
|   hold min_ss_125C_4v50: WNS / TNS | 0.894 / 0.000 | sí |
|   hold min_tt_025C_5v00: WNS / TNS | 0.346 / 0.000 | sí |
|   hold nom_ff_n40C_5v50: WNS / TNS | 0.109 / 0.000 | sí |
|   hold nom_ss_125C_4v50: WNS / TNS | 0.888 / 0.000 | sí |
|   hold nom_tt_025C_5v00: WNS / TNS | 0.343 / 0.000 | sí |

| dato informativo | valor |
|---|---|
| max slew (design__max_slew_violation__count, peor esquina) | 0 |
| max capacitancia (design__max_cap_violation__count, peor esquina) | 1 |
| área del die (µm²) | 359332 |
| utilización | 0.589 |

**Resultado: NO CIERRA**
