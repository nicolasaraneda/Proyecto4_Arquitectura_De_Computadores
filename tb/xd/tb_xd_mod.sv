// tb_xd_mod.sv: testbench de los dos módulos de la extensión de la ISA
// (rtl/espino_core/espino_xd.v), solos, contra el modelo ref/xd.py.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Para cada uno de los 8 valores del parámetro Xd instancia:
//   espino_xd_dec   y lo recorre con las 1024 combinaciones de funct3 y funct7
//                   en el opcode custom-0 y en otros opcodes, con los campos
//                   de registros al azar. Solo las tres codificaciones de la
//                   especificación se reconocen, y solo si están en Xd.
//   espino_xd_opa   más la ALU del Espino (espino_alu, sin modificar),
//                   conectados como en la etapa X del core: operando A
//                   desplazado, operando B anulado en mulstep cuando rs1[31]
//                   vale 0, suma o resta. El resultado se compara con el que
//                   calculó ref/xd.py para cada vector del archivo +vectores
//                   (tools/xd/tb_modulos.sh los genera).
//
// Uso (tools/xd/tb_modulos.sh): vvp tb_xd_mod.vvp +vectores=archivo.hex +n=N

`timescale 1ns/1ps

module tb_xd_mod;

  localparam int MAXV = 400000;

  logic [31:0] instr;
  logic [31:0] rs1, rs2;
  logic [2:0]  funct3;
  logic        resta;

  wire [7:0]  emad_o, devk_o, mulstep_o;
  wire [31:0] a_o [8];
  wire [7:0]  b_cero;
  wire [31:0] res [8];
  wire [7:0]  cmp_nc;

  genvar g;
  generate
    for (g = 0; g < 8; g++) begin : m
      espino_xd_dec #(.Xd(g[2:0])) u_dec (
        .instr_i(instr), .emad_o(emad_o[g]), .devk_o(devk_o[g]), .mulstep_o(mulstep_o[g]));
      espino_xd_opa #(.Xd(g[2:0])) u_opa (
        .rs1_i(rs1), .funct3_i(funct3), .a_o(a_o[g]), .b_cero_o(b_cero[g]));
      espino_alu u_alu (
        .operator_i   (resta ? 4'd1 : 4'd0),
        .operand_a_i  (a_o[g]),
        .operand_b_i  (b_cero[g] ? 32'b0 : rs2),
        .result_o     (res[g]),
        .cmp_result_o (cmp_nc[g]));
    end
  endgenerate

  logic [31:0] vec [4 * MAXV];
  string       arch;
  int          n = 0, errores = 0;
  longint      n_dec = 0, n_op = 0;

  // Las tres codificaciones de la especificación (docs/extension_isa.md)
  function automatic int cual(input logic [31:0] i);
    if (i[6:0] != 7'h0b) return -1;
    if (i[14:12] == 3'b100 && i[31:25] == 7'b0000101) return 0;
    if (i[14:12] == 3'b101 && i[31:25] == 7'b0000101) return 1;
    if (i[14:12] == 3'b010 && i[31:25] == 7'b0000000) return 2;
    return -1;
  endfunction

  initial begin
    int c;
    logic [6:0] opc;
    if (!$value$plusargs("vectores=%s", arch)) begin $display("falta +vectores=ARCHIVO"); $fatal(1); end
    void'($value$plusargs("n=%d", n));
    if (n > MAXV) begin $display("demasiados vectores"); $fatal(1); end
    $readmemh(arch, vec, 0, 4 * n - 1);
    rs1 = 0; rs2 = 0; funct3 = 0; resta = 0;

    // --- Decodificador: todas las combinaciones de funct3 y funct7 -----------
    for (int o = 0; o < 6; o++) begin
      case (o)
        0, 1, 2: opc = 7'h0b;      // custom-0, tres veces con otros registros
        3:       opc = 7'h33;      // OP: add, sub, ...
        4:       opc = 7'h2b;      // custom-1
        default: opc = 7'h0a;      // casi custom-0
      endcase
      for (int f3 = 0; f3 < 8; f3++)
        for (int f7 = 0; f7 < 128; f7++) begin
          instr = {f7[6:0], 5'($urandom), 5'($urandom), f3[2:0], 5'($urandom), opc};
          #1;
          c = cual(instr);
          for (int x = 0; x < 8; x++) begin
            if (emad_o[x]    !== (c == 0 && x[0]) ||
                devk_o[x]    !== (c == 1 && x[1]) ||
                mulstep_o[x] !== (c == 2 && x[2])) begin
              errores++;
              if (errores <= 10) $display("FAIL decodificador: Xd=%0d instr=%08x emad=%b devk=%b mulstep=%b", x, instr, emad_o[x], devk_o[x], mulstep_o[x]);
            end
            n_dec++;
          end
        end
    end

    // --- Operando A y sumador de la ALU contra el modelo -------------------------
    for (int k = 0; k < n; k++) begin
      c   = int'(vec[4 * k]);            // 0 emad, 1 devk, 2 mulstep
      rs1 = vec[4 * k + 1];
      rs2 = vec[4 * k + 2];
      funct3 = (c == 0) ? 3'b100 : (c == 1) ? 3'b101 : 3'b010;
      resta  = (c == 1);
      #1;
      // Todos los subconjuntos que tienen la instrucción deben dar lo mismo
      for (int x = 1; x < 8; x++) begin
        if (!x[c]) continue;
        if (res[x] !== vec[4 * k + 3]) begin
          errores++;
          if (errores <= 10) $display("FAIL operando: Xd=%0d instruccion %0d rs1=%08x rs2=%08x: %08x, el modelo dice %08x", x, c, rs1, rs2, res[x], vec[4 * k + 3]);
        end
        n_op++;
      end
    end

    if (errores == 0) $display("PASS tb_xd_mod: %0d comprobaciones del decodificador y %0d resultados iguales al modelo (%0d vectores por 4 subconjuntos cada uno)", n_dec, n_op, n);
    else              $display("FAIL tb_xd_mod: %0d errores", errores);
    $finish;
  end

endmodule
