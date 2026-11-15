// propiedades_xd.vh: cada instrucción de la extensión contra su especificación,
// sobre el core barrel.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// tools/xd/formal.sh copia este texto dentro de espino_barrel_core, a
// continuación de formal/barrel/propiedades.vh (usa sus registros auxiliares),
// y lo prueba con SymbiYosys por inducción para cada subconjunto Xd. La
// instrucción que entrega la memoria, el dato del bus y lo que entrega el
// banco de registros quedan libres: las propiedades valen para cualquier
// programa, cualquier valor de rs1 y rs2 y cualquier combinación de
// instrucciones de los otros tres hilos en las demás etapas.
//
// La especificación (docs/extension_isa.md) está escrita aquí otra vez, sobre
// la instrucción registrada en X y con operadores de Verilog (>>>, <<, +, -),
// sin usar ninguna señal de espino_xd.v:
//
//   emad     custom-0, funct3 100, funct7 0000101   rd = rs2 + (rs1 >>> 5)
//   devk     custom-0, funct3 101, funct7 0000101   rd = (rs1 << 5) - rs2
//   mulstep  custom-0, funct3 010, funct7 0000000   rd = (rs1 << 1) + (rs1[31] ? rs2 : 0)
//
//   X1  Una instrucción de la extensión presente en el core (bit de Xd) deja
//       en el registro de resultado exactamente el valor de la fórmula, con
//       los rs1 y rs2 que el banco entregó para ella.
//   X2  Escribe rd, y solo si rd no es x0. El registro que escribe es el rd de
//       esa instrucción, en el contexto de su hilo (con P6 y P11 del barrel).
//   X3  No pide el bus de datos, no salta y el hilo sigue en pc + 4.
//   X4  Una palabra de custom-0 que no es una instrucción presente (otro
//       funct3, otro funct7, k distinto de 5, o una instrucción que no está en
//       Xd) no escribe, no pide el bus y no salta: sigue siendo una
//       instrucción ilegal sin efecto, como en el Espino base.
//   X5  Una instrucción que no es de custom-0 no usa nada de la extensión: la
//       decodificación que se registra es la del decodificador del Espino sin
//       cambios, la selección 3 del operando A no aparece y el operando B no
//       se anula.
//   X6  El resultado no depende de la instrucción que sale de la memoria en
//       ese ciclo, que es de otro hilo. No hace falta una afirmación aparte:
//       instr_rdata_i queda libre en el ciclo en que se comprueba X1.

  // --- Especificación ---------------------------------------------------------
  wire        fx_custom0 = (instr_x[6:0] == 7'b0001011);
  wire        fx_emad    = Xd[0] && fx_custom0 && instr_x[14:12] == 3'b100 && instr_x[31:25] == 7'b0000101;
  wire        fx_devk    = Xd[1] && fx_custom0 && instr_x[14:12] == 3'b101 && instr_x[31:25] == 7'b0000101;
  wire        fx_mulstep = Xd[2] && fx_custom0 && instr_x[14:12] == 3'b010 && instr_x[31:25] == 7'b0000000;
  wire        fx_xd      = fx_emad || fx_devk || fx_mulstep;
  wire signed [31:0] fx_rs1s = rf_rdata_a;
  // El desplazamiento aritmético va en un cable propio con signo. Escrito
  // dentro de la suma, Verilog lo evalúa sin signo (un operando sin signo
  // vuelve sin signo toda la expresión) y pasa a ser un desplazamiento lógico:
  // así estuvo en la primera versión de este archivo, y lo delató que la
  // mutación MUTA_XD_SRL pasara la prueba.
  wire signed [31:0] fx_sra = fx_rs1s >>> 5;
  wire [31:0] fx_spec    = fx_emad ? rf_rdata_b + fx_sra :
                           fx_devk ? (rf_rdata_a << 5) - rf_rdata_b :
                                     (rf_rdata_a << 1) + (rf_rdata_a[31] ? rf_rdata_b : 32'b0);

  reg         fx_xd_q, fx_c0_q;
  reg  [31:0] fx_spec_q;
  reg  [3:0]  fx_rd_q;
  reg  [31:0] fx_instr_r_q;
  always @(posedge clk_i) begin
    fx_xd_q      <= fx_xd && tb_valid_x;
    fx_c0_q      <= fx_custom0 && !fx_xd && tb_valid_x;
    fx_spec_q    <= fx_spec;
    fx_rd_q      <= instr_x[10:7];
    fx_instr_r_q <= instr_rdata_i;
  end

  always @(posedge clk_i) begin
    // Las que miran el ciclo anterior valen desde el segundo ciclo sin reset
    if (rst_ni && f_ciclo >= 4'd1) begin
      // La instrucción en X es la que entregó la memoria en el ciclo anterior
      assert (instr_x == fx_instr_r_q);

      if (tb_valid_x && fx_xd) begin
        // X1, en la etapa X: el sumador entrega la fórmula
        assert (alu_result == fx_spec);
        // X2, en la etapa X
        assert (rf_we_x);
        assert (rf_wd_sel_x == 2'd0);
        // X3
        assert (!data_req_o && !data_we_o);
        assert (!taken);
        assert (pc_next == pc_plus_4);
      end

      // X4
      if (tb_valid_x && fx_custom0 && !fx_xd) begin
        assert (!rf_we_x);
        assert (!data_req_o && !data_we_o);
        assert (!taken);
        assert (pc_next == pc_plus_4);
      end

      // X5, en la etapa X
      if (!fx_custom0 || !fx_xd) begin
        assert (alu_op_a_sel_x != 2'd3);
        assert (operand_b == ((alu_op_b_sel_x == 1'b1) ? imm_operand_x : rf_rdata_b));
      end
    end

    if (rst_ni && f_ciclo >= 4'd2) begin
      // X1 y X2, en la etapa M: lo que llega al puerto de escritura del banco
      if (fx_xd_q) begin
        assert (rf_wdata == fx_spec_q);
        assert (rf_we_m == (fx_rd_q != 4'd0));
        assert (rd_m == fx_rd_q);
        assert (!ld_m);
      end
      if (fx_c0_q) assert (!rf_we_m);
    end
  end

  // X5, en la etapa R: para una palabra que no es de custom-0, lo que se
  // registra hacia X es lo que dice el decodificador del Espino
  always @* begin
    if (instr_rdata_i[6:0] != 7'b0001011) begin
      assert (!xd_d);
      assert (alu_operator_r == alu_operator_d);
      assert (alu_op_a_sel_r == alu_op_a_sel_d);
      assert (alu_op_b_sel_r == alu_op_b_sel_d);
      assert (rf_we_r == rf_we_d);
    end
    // El decodificador del Espino nunca pide la selección 3 del operando A
    assert (alu_op_a_sel_d != 2'd3);
  end

`ifdef FORMAL_XD_COBERTURA
  // Que las pruebas no sean vacías: cada instrucción presente se ejecuta con
  // un resultado que no es trivial y llega a escribir el banco
  always @(posedge clk_i) begin
    if (Xd[0]) cover (rst_ni && tb_valid_x && fx_emad && fx_rs1s < 0 && rf_rdata_b != 0 && instr_x[10:7] != 0);
    if (Xd[1]) cover (rst_ni && tb_valid_x && fx_devk && rf_rdata_a != 0 && rf_rdata_b != 0 && instr_x[10:7] != 0);
    if (Xd[2]) cover (rst_ni && tb_valid_x && fx_mulstep && rf_rdata_a[31] && rf_rdata_b != 0 && instr_x[10:7] != 0);
    if (Xd[2]) cover (rst_ni && tb_valid_x && fx_mulstep && !rf_rdata_a[31] && rf_rdata_b != 0);
    cover (rst_ni && f_ciclo >= 4'd2 && fx_xd_q && rf_we_m);
    cover (rst_ni && tb_valid_x && fx_custom0 && !fx_xd);
  end
`endif
