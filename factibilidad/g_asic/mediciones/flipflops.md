## Flip-flops del netlist de síntesis, por registro del RTL

| corrida | flip-flops | del banco de registros | registros del banco que quedaron | registros eliminados |
|---|---|---|---|---|
| base_t40 | 872 | 480 | 15 de 15 | ninguno |
| seg_t40 | 774 | 352 | 11 de 15 | x10, x11, x12, x14 |
| base_jer | 875 | 480 | 15 de 15 | ninguno |
| seg_jer | 927 | 480 | 15 de 15 | ninguno |

| registro (net de la salida Q) | base_t40 | seg_t40 | base_jer | seg_jer |
|---|---|---|---|---|
| `regs[N]` | 480 | 352 | 480 | 480 |
| `ram[N]` | 128 | 128 | 128 | 128 |
| `a_rdata_o` | 0 | 0 | 32 | 0 |
| `b_rdata_o` | 0 | 0 | 32 | 32 |
| `bank_a` | 0 | 32 | 0 | 32 |
| `bank_b` | 0 | 32 | 0 | 32 |
| `imm_operand_q` | 0 | 29 | 0 | 32 |
| `instr_addr` | 32 | 11 | 0 | 0 |
| `instr_addr_o` | 0 | 0 | 32 | 11 |
| `instr_ex_o` | 0 | 0 | 0 | 32 |
| `pc_id` | 32 | 11 | 0 | 0 |
| `pc_id_o` | 0 | 0 | 32 | 11 |
| `ram_b_rdata` | 32 | 32 | 0 | 0 |
| `rdata_a_o` | 0 | 0 | 32 | 0 |
| `rdata_b_o` | 0 | 0 | 32 | 0 |
| `rf_rdata_a` | 32 | 0 | 0 | 0 |
| `wdata_q` | 0 | 32 | 0 | 32 |
| `instr_rdata` | 29 | 0 | 0 | 0 |
| `lsu_wdata` | 24 | 0 | 0 | 0 |
| `alu_operator_q` | 0 | 12 | 0 | 0 |
| `rdata_o` | 0 | 0 | 12 | 12 |
| `imm_target_q` | 0 | 9 | 0 | 11 |
| `data_wdata` | 8 | 0 | 0 | 0 |
| `digit_q` | 8 | 8 | 8 | 8 |
| `price_q` | 8 | 8 | 8 | 8 |
| `spi_rdata` | 8 | 8 | 0 | 0 |
| `tx_hold` | 8 | 8 | 8 | 8 |
| `tx_shift` | 8 | 8 | 8 | 8 |
| `rx_shift` | 7 | 7 | 7 | 7 |
| `alu_operator` | 0 | 0 | 0 | 4 |
| `bit_cnt` | 4 | 4 | 4 | 4 |
| `instr_ex` | 0 | 4 | 0 | 0 |
| `led` | 4 | 4 | 0 | 0 |
| `leds_o` | 0 | 0 | 4 | 4 |
| `per_rdata` | 4 | 4 | 0 | 0 |
| `cs_sync` | 3 | 3 | 3 | 3 |
| `sclk_sync` | 3 | 3 | 3 | 3 |
| `alu_op_a_sel` | 0 | 0 | 0 | 2 |
| `alu_op_a_sel_q` | 0 | 2 | 0 | 0 |
| `lsu_type_dec_q` | 0 | 2 | 0 | 0 |
| `lsu_type_o` | 0 | 0 | 0 | 2 |
| `rf_wd_sel_q` | 0 | 2 | 0 | 2 |
| `rst_sync_q` | 2 | 2 | 2 | 2 |
| `alu_op_b_sel` | 0 | 1 | 0 | 1 |
| `busy_q` | 1 | 1 | 1 | 1 |
| `fwd_a_q` | 0 | 1 | 0 | 1 |
| `fwd_b_q` | 0 | 1 | 0 | 1 |
| `instr_valid_id` | 1 | 1 | 0 | 0 |
| `instr_valid_id_o` | 0 | 0 | 1 | 1 |
| `is_branch_q` | 0 | 1 | 0 | 1 |
| `is_jal_q` | 0 | 1 | 0 | 1 |
| `is_jalr_q` | 0 | 1 | 0 | 1 |
| `lsu_req_dec_q` | 0 | 1 | 0 | 1 |
| `lsu_sign` | 0 | 1 | 0 | 0 |
| `lsu_sign_o` | 0 | 0 | 0 | 1 |
| `lsu_we` | 0 | 1 | 0 | 0 |
| `lsu_we_o` | 0 | 0 | 0 | 1 |
| `mosi` | 1 | 1 | 1 | 1 |
| `mosi_sync` | 1 | 1 | 1 | 1 |
| `new_price_q` | 1 | 1 | 1 | 1 |
| `rd_is_per` | 1 | 1 | 1 | 1 |
| `rd_is_spi` | 1 | 1 | 1 | 1 |
| `rf_ready` | 1 | 0 | 0 | 0 |
| `rf_ready_o` | 0 | 0 | 1 | 0 |
| `rf_we_dec_q` | 0 | 1 | 0 | 1 |

Las corridas completas se sintetizan aplanadas. Con la jerarquía conservada (corridas *_jer) el banco de registros mantiene sus 15 registros en las dos variantes (mediciones/sintesis.md).
