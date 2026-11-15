// espino_barrel_core.v: Espino multihilo tipo barrel (docs/espino_barrel.md).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Cuatro hilos rotan por un pipeline uniforme de cuatro etapas. En cada ciclo
// hay una instrucción de cada hilo en cada etapa, así que cada hilo completa
// una instrucción cada 4 ciclos y el core completa una por ciclo.
//
//   F  búsqueda          el contador de programa del hilo direcciona la
//                        memoria de instrucciones (BRAM, lee en el flanco).
//   R  registros         la instrucción sale de la BRAM. Se decodifica y sus
//                        rs1 y rs2 direccionan el banco de registros con
//                        {hilo, registro}. En el flanco se registran la
//                        decodificación y los operandos.
//   X  ejecución         ALU, comparación del salto, próximo contador de
//                        programa y petición al bus de datos (el store se
//                        escribe en el flanco, el load se pide).
//   M  memoria y         llega el dato del load, se alinea y se escribe el
//      escritura         registro destino en el banco, en {hilo, rd}.
//
// La instrucción siguiente del mismo hilo entra a F cuando la anterior salió
// de M. Por eso no hay adelantamiento, ni burbujas, ni instrucciones que se
// anulen: cuando un hilo lee el banco, su instrucción anterior ya escribió, y
// cuando busca, su salto anterior ya se resolvió.
//
// Qué se reutiliza del Espino sin modificar (rtl/espino_core/):
//   espino_decoder.v          el decodificador, completo.
//   espino_alu.v              la ALU, completa.
//   espino_load_store_unit.v  dos instancias. u_lsu_x arma la petición en la
//                             etapa X (bytes habilitados, dato y dirección
//                             alineados). u_lsu_m alinea el dato leído en la
//                             etapa M. No se usa su máquina de espera
//                             (busy_o, data_req_o): la espera del load es la
//                             etapa M, y la petición sale directo de la
//                             decodificación.
// El camino de datos de la etapa X (multiplexores de operandos, destino del
// salto, enlace) es el de espino_id_stage.v, copiado.
//
// Arranque: el hilo t parte en BootAddr + BootPaso t. Con BootPaso = 4 (el
// valor por defecto) el programa empieza con una tabla de cuatro saltos, uno
// por hilo. Con BootPaso = 0 los cuatro hilos parten en BootAddr y el programa
// tiene que averiguar qué hilo es (alternativa que se midió en el prototipo y
// se descartó: un registro HILO en el SoC, que usaría la salida hilo_x_o). El pipeline sale del reset como si tuviera
// burbujas (instrucciones que no hacen nada) en R y en X.
//
// Señales tb_*: solo las miran los testbenches. La síntesis las elimina.
//
// Los bloques `ifdef MUTA_* son errores puestos a propósito, que solo se
// activan desde la línea de comandos para comprobar que las pruebas los
// detectan (tools/barrel/humo.sh y tools/barrel/mutaciones.sh). No se sintetizan
// nunca.

module espino_barrel_core #(
  parameter [31:0]  BootAddr = 32'h0000_0000,
  parameter integer BootPaso = 4,     // distancia entre las entradas de dos hilos
  parameter integer PcW      = 11
) (
  input  wire        clk_i,
  input  wire        rst_ni,

  // Hilo de la instrucción que está en la etapa X, que es la que usa el bus
  // de datos en este ciclo. Solo lo usa el registro HILO del SoC (opcional).
  output wire [1:0]  hilo_x_o,

  output wire        instr_req_o,
  output wire [31:0] instr_addr_o,
  input  wire [31:0] instr_rdata_i,

  output wire        data_req_o,
  output wire        data_we_o,
  output wire [3:0]  data_be_o,
  output wire [31:0] data_addr_o,
  output wire [31:0] data_wdata_o,
  input  wire [31:0] data_rdata_i
);

  localparam [1:0] OP_A_PC   = 2'd1;
  localparam [1:0] OP_A_ZERO = 2'd2;
  localparam       OP_B_IMM  = 1'b1;
  localparam [1:0] WD_LSU    = 2'd1;
  localparam [1:0] WD_PC4    = 2'd2;

  // ---------------------------------------------------------------------------
  // Qué hilo ocupa cada etapa. tid_f cuenta 0, 1, 2, 3 y los demás lo siguen.
  // ---------------------------------------------------------------------------
  reg  [1:0] tid_f;
  wire [1:0] tid_r = tid_f - 2'd1;
  wire [1:0] tid_x = tid_f - 2'd2;
  wire [1:0] tid_m = tid_f - 2'd3;
  assign hilo_x_o = tid_x;

  // ---------------------------------------------------------------------------
  // Anillo de contadores de programa. El bit 0 siempre vale 0 y no se guarda.
  //   pc_f  dirección que se busca (etapa F)
  //   pc_r  dirección de la instrucción en R
  //   pc_x  dirección de la instrucción en X
  //   pc_m  dirección de la PRÓXIMA instrucción del hilo que está en M
  // ---------------------------------------------------------------------------
  reg  [PcW-1:1] pc_f_q, pc_r_q, pc_x_q, pc_m_q;
  wire [PcW-1:0] pc_f = {pc_f_q, 1'b0};
  wire [PcW-1:0] pc_x = {pc_x_q, 1'b0};
  wire [PcW-1:0] pc_next;

  // Valores de reset del anillo (ver "Avance del pipeline"). Con BootPaso = 4
  // son BootAddr + 4, BootAddr + 4 y BootAddr + 8.
  localparam [31:0] BootM = BootAddr + BootPaso;            // próxima del hilo 1
  localparam [31:0] BootX = BootAddr + 2 * BootPaso - 4;    // burbuja del hilo 2
  localparam [31:0] BootR = BootAddr + 3 * BootPaso - 4;    // burbuja del hilo 3

  // valid_r: la etapa R tiene una instrucción buscada de verdad
  reg valid_r;

  // ---------------------------------------------------------------------------
  // F: búsqueda. La BRAM lee en cada flanco.
  // ---------------------------------------------------------------------------
  assign instr_req_o  = 1'b1;
  assign instr_addr_o = pc_f;            // con PcW < 32 extiende con ceros

  // ---------------------------------------------------------------------------
  // R: decodificación y lectura del banco
  // ---------------------------------------------------------------------------
  wire [3:0]  alu_operator_d;
  wire [1:0]  alu_op_a_sel_d;
  wire        alu_op_b_sel_d;
  wire [31:0] imm_operand_d, imm_target_d;
  wire        rf_we_d;
  wire [1:0]  rf_wd_sel_d;
  wire        is_branch_d, is_jal_d, is_jalr_d;
  wire        lsu_req_d, lsu_we_d;
  wire [1:0]  lsu_type_d;
  wire        lsu_sign_d;
  wire        illegal_insn_d;

  espino_decoder u_decoder (
    .instr_i        (instr_rdata_i),
    .illegal_insn_o (illegal_insn_d),
    .alu_operator_o (alu_operator_d),
    .alu_op_a_sel_o (alu_op_a_sel_d),
    .alu_op_b_sel_o (alu_op_b_sel_d),
    .imm_operand_o  (imm_operand_d),
    .imm_target_o   (imm_target_d),
    .rf_we_o        (rf_we_d),
    .rf_wd_sel_o    (rf_wd_sel_d),
    .is_branch_o    (is_branch_d),
    .is_jal_o       (is_jal_d),
    .is_jalr_o      (is_jalr_d),
    .lsu_req_o      (lsu_req_d),
    .lsu_we_o       (lsu_we_d),
    .lsu_type_o     (lsu_type_d),
    .lsu_sign_o     (lsu_sign_d)
  );

  wire [31:0] rf_rdata_a, rf_rdata_b;
  wire [31:0] rf_wdata;
  reg         rf_we_m;
  reg  [3:0]  rd_m;

  espino_barrel_regfile u_rf (
    .clk_i     (clk_i),
    .raddr_a_i ({tid_r, instr_rdata_i[18:15]}),
    .rdata_a_o (rf_rdata_a),
    .raddr_b_i ({tid_r, instr_rdata_i[23:20]}),
    .rdata_b_o (rf_rdata_b),
`ifdef MUTA_CONTEXTO
    // MUTACIÓN (solo para las pruebas): el resultado se escribe en el
    // contexto del hilo que está en X, no en el del que está en M.
    .waddr_i   ({tid_x, rd_m}),
`else
    .waddr_i   ({tid_m, rd_m}),
`endif
    .wdata_i   (rf_wdata),
    .we_i      (rf_we_m)
  );

  // Registros entre R y X. Los que provocan algún efecto (escribir el banco,
  // pedir el bus, saltar) tienen reset y se cargan en 0 si la instrucción no
  // es válida: así las burbujas del arranque no hacen nada.
  reg  [31:0]    instr_x;
  reg  [3:0]     alu_operator_x;
  reg  [1:0]     alu_op_a_sel_x;
  reg            alu_op_b_sel_x;
  reg  [31:0]    imm_operand_x;
  reg  [PcW-1:0] imm_target_x;
  reg  [1:0]     rf_wd_sel_x;
  reg  [1:0]     lsu_type_x;
  reg            lsu_sign_x, lsu_we_x;
  reg            rf_we_x, lsu_req_x, is_branch_x, is_jal_x, is_jalr_x;

  always @(posedge clk_i) begin
    instr_x        <= instr_rdata_i;
    alu_operator_x <= alu_operator_d;
    alu_op_a_sel_x <= alu_op_a_sel_d;
    alu_op_b_sel_x <= alu_op_b_sel_d;
    imm_operand_x  <= imm_operand_d;
    imm_target_x   <= imm_target_d[PcW-1:0];
    rf_wd_sel_x    <= rf_wd_sel_d;
    lsu_type_x     <= lsu_type_d;
    lsu_sign_x     <= lsu_sign_d;
    lsu_we_x       <= lsu_we_d;
  end

  // ---------------------------------------------------------------------------
  // X: ejecución
  // ---------------------------------------------------------------------------
  reg  [31:0] operand_a;
  wire [31:0] operand_b;
  always @* begin
    case (alu_op_a_sel_x)
      OP_A_PC:   operand_a = pc_x;       // extiende con ceros
      OP_A_ZERO: operand_a = 32'b0;
      default:   operand_a = rf_rdata_a;
    endcase
  end
  assign operand_b = (alu_op_b_sel_x == OP_B_IMM) ? imm_operand_x : rf_rdata_b;

  wire [31:0] alu_result;
  wire        alu_cmp_result;
  espino_alu u_alu (
    .operator_i   (alu_operator_x),
    .operand_a_i  (operand_a),
    .operand_b_i  (operand_b),
    .result_o     (alu_result),
    .cmp_result_o (alu_cmp_result)
  );

  // Petición al bus de datos. De esta instancia de la unidad de carga y
  // almacenamiento se usa la parte que arma la petición.
  wire        lsu_x_busy_nc, lsu_x_req_nc;
  wire [31:0] lsu_x_rdata_nc;
  espino_load_store_unit u_lsu_x (
    .clk_i        (clk_i),
    .rst_ni       (rst_ni),
    .req_i        (lsu_req_x),
    .we_i         (lsu_we_x),
    .type_i       (lsu_type_x),
    .sign_i       (lsu_sign_x),
    .addr_i       (alu_result),
    .wdata_i      (rf_rdata_b),
    .rdata_o      (lsu_x_rdata_nc),
    .busy_o       (lsu_x_busy_nc),
    .data_req_o   (lsu_x_req_nc),
    .data_we_o    (data_we_o),
    .data_be_o    (data_be_o),
    .data_addr_o  (data_addr_o),
    .data_wdata_o (data_wdata_o),
    .data_rdata_i (32'b0)
  );
  assign data_req_o = lsu_req_x;

  // Próximo contador de programa del hilo
  wire [PcW-1:0] pc_plus_imm = pc_x + imm_target_x;
  wire [PcW-1:0] pc_plus_4   = pc_x + 32'd4;
  wire           taken       = (is_branch_x & alu_cmp_result) | is_jal_x | is_jalr_x;
  wire [PcW-1:0] pc_target   = is_jalr_x ? {alu_result[PcW-1:1], 1'b0} : pc_plus_imm;
  assign pc_next = taken ? pc_target : pc_plus_4;

  // Registros entre X y M
  reg  [31:0] res_m;          // resultado de la ALU o enlace
  reg         ld_m;           // el registro destino recibe el dato del load
  reg  [1:0]  lsu_type_m;
  reg         lsu_sign_m;
  reg  [1:0]  boff_m;         // dos bits bajos de la dirección del load

  always @(posedge clk_i) begin
    res_m      <= (rf_wd_sel_x == WD_PC4) ? pc_plus_4 : alu_result;
    ld_m       <= (rf_wd_sel_x == WD_LSU);
    rd_m       <= instr_x[10:7];
    lsu_type_m <= lsu_type_x;
    lsu_sign_m <= lsu_sign_x;
    boff_m     <= alu_result[1:0];
  end

  // ---------------------------------------------------------------------------
  // M: dato del load y escritura al banco
  // ---------------------------------------------------------------------------
  wire [31:0] lsu_rdata;
  wire        lsu_m_busy_nc, lsu_m_req_nc, lsu_m_we_nc;
  wire [3:0]  lsu_m_be_nc;
  wire [31:0] lsu_m_addr_nc, lsu_m_wdata_nc;
  espino_load_store_unit u_lsu_m (
    .clk_i        (clk_i),
    .rst_ni       (rst_ni),
    .req_i        (1'b0),
    .we_i         (1'b0),
    .type_i       (lsu_type_m),
    .sign_i       (lsu_sign_m),
`ifdef MUTA_BOFF
    // MUTACIÓN (solo para las pruebas): el dato del load se alinea con la
    // dirección que calcula la instrucción que está ahora en X, que es de
    // otro hilo, en vez de la que se guardó al pedirlo.
    .addr_i       ({30'b0, alu_result[1:0]}),
`else
    .addr_i       ({30'b0, boff_m}),
`endif
    .wdata_i      (32'b0),
    .rdata_o      (lsu_rdata),
    .busy_o       (lsu_m_busy_nc),
    .data_req_o   (lsu_m_req_nc),
    .data_we_o    (lsu_m_we_nc),
    .data_be_o    (lsu_m_be_nc),
    .data_addr_o  (lsu_m_addr_nc),
    .data_wdata_o (lsu_m_wdata_nc),
    .data_rdata_i (data_rdata_i)
  );

  assign rf_wdata = ld_m ? lsu_rdata : res_m;

  // ---------------------------------------------------------------------------
  // Avance del pipeline
  // ---------------------------------------------------------------------------
  // Estado al salir del reset (primer ciclo), con BootPaso = 4: el hilo 0
  // está en F con BootAddr. El hilo 1 está en M y su próxima dirección es
  // BootAddr + 4. El hilo 2 está en X como una burbuja ubicada en BootAddr + 4,
  // de modo que su próxima dirección es BootAddr + 8. El hilo 3 está en R como
  // una burbuja en BootAddr + 8 y seguirá en BootAddr + 12. Una burbuja no
  // escribe, no pide el bus y no salta: solo avanza 4. En general la burbuja
  // del hilo t se ubica 4 antes de su entrada, BootAddr + BootPaso t.
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      tid_f       <= 2'd0;
      pc_f_q      <= BootAddr[PcW-1:1];
      pc_m_q      <= BootM[PcW-1:1];
      pc_x_q      <= BootX[PcW-1:1];
      pc_r_q      <= BootR[PcW-1:1];
      valid_r     <= 1'b0;
      rf_we_x     <= 1'b0;
      lsu_req_x   <= 1'b0;
      is_branch_x <= 1'b0;
      is_jal_x    <= 1'b0;
      is_jalr_x   <= 1'b0;
      rf_we_m     <= 1'b0;
    end else begin
      tid_f       <= tid_f + 2'd1;
      pc_f_q      <= pc_m_q;
      pc_r_q      <= pc_f_q;
      pc_x_q      <= pc_r_q;
      pc_m_q      <= pc_next[PcW-1:1];
      valid_r     <= 1'b1;
`ifdef MUTA_ARRANQUE
      // MUTACIÓN (solo para las pruebas): la burbuja del arranque no se
      // anula y el hilo 3 ejecuta la instrucción que la BRAM leyó en el reset.
      rf_we_x     <= rf_we_d;
      lsu_req_x   <= lsu_req_d;
      is_branch_x <= is_branch_d;
      is_jal_x    <= is_jal_d;
      is_jalr_x   <= is_jalr_d;
`else
      rf_we_x     <= rf_we_d     & valid_r;
      lsu_req_x   <= lsu_req_d   & valid_r;
      is_branch_x <= is_branch_d & valid_r;
      is_jal_x    <= is_jal_d    & valid_r;
      is_jalr_x   <= is_jalr_d   & valid_r;
`endif
      // Una escritura a x0 no se hace
      rf_we_m     <= rf_we_x & (instr_x[10:7] != 4'd0);
    end
  end

  // ---------------------------------------------------------------------------
  // Solo para testbenches
  // ---------------------------------------------------------------------------
  reg tb_valid_x;                           // la etapa X tiene una instrucción de verdad
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) tb_valid_x <= 1'b0;
    else         tb_valid_x <= valid_r;
  end
  wire [1:0]  tb_tid_x   = tid_x;           // hilo de la instrucción en X
  wire [1:0]  tb_tid_m   = tid_m;           // hilo de la instrucción en M
  wire [31:0] tb_pc_x    = pc_x;
  wire [31:0] tb_instr_x = instr_x;
  wire        tb_taken   = taken;
  wire        tb_rf_we   = rf_we_m;         // escritura al banco en este flanco
  wire [3:0]  tb_rf_wa   = rd_m;
  wire [31:0] tb_rf_wd   = rf_wdata;

  wire _unused = &{1'b0, illegal_insn_d, imm_target_d, instr_x, pc_r_q,
                   lsu_x_busy_nc, lsu_x_req_nc, lsu_x_rdata_nc,
                   lsu_m_busy_nc, lsu_m_req_nc, lsu_m_we_nc, lsu_m_be_nc,
                   lsu_m_addr_nc, lsu_m_wdata_nc,
                   tb_valid_x, tb_tid_x, tb_tid_m, tb_pc_x, tb_instr_x,
                   tb_taken, tb_rf_we, tb_rf_wa, tb_rf_wd};

endmodule
