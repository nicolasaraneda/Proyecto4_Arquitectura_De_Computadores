## Extremos de la ruta crítica, esquina lenta (max_ss_125C_4v50)

| corrida | sale del registro | llega al registro | celdas en la ruta | retardo de llegada (ns) | holgura (ns) |
|---|---|---|---|---|---|
| base_t40 | `u_soc.instr_rdata[3]` | `u_soc.u_core.u_rf.regs[13][13]` | 46 | 32.428 | 9.142 |
| base_t30 | `u_soc.instr_rdata[0]` | `u_soc.u_core.u_rf.regs[3][22]` | 49 | 27.088 | 4.626 |
| base_t25 | `u_soc.instr_rdata[0]` | `u_soc.u_core.u_rf.regs[4][8]` | 44 | 25.318 | 1.402 |
| base_t23p5 | `u_soc.instr_rdata[3]` | `u_soc.u_core.u_rf.regs[2][9]` | 45 | 24.885 | 0.245 |
| base_t22 | `u_soc.instr_rdata[0]` | `u_soc.u_core.u_rf.regs[8][24]` | 43 | 24.223 | -0.479 |
| seg_t40 | `u_soc.u_core.u_id.g_pipe.alu_op_a_sel_q[2]` | `u_soc.u_core.u_rf.regs[4][16]` | 60 | 36.946 | 4.709 |
| seg_t30 | `u_soc.u_core.u_rf.g_bypass.fwd_a_q` | `u_soc.u_core.u_rf.regs[5][24]` | 56 | 29.200 | 2.466 |
| seg_t25 | `u_soc.u_core.u_rf.g_bypass.fwd_b_q` | `u_soc.per_rdata[2]` | 42 | 24.892 | 1.702 |
| seg_t23p5 | `u_soc.u_core.u_rf.g_bypass.fwd_b_q` | `u_soc.u_core.u_rf.regs[2][30]` | 39 | 23.718 | 1.435 |
| seg_t22 | `u_soc.u_core.u_rf.g_bypass.fwd_b_q` | `u_soc.u_core.u_rf.regs[7][12]` | 55 | 28.970 | -5.414 |

El nombre es el del net de la salida Q del flip-flop en el netlist final. La cuenta de celdas incluye el flip-flop de partida y los buffers.
