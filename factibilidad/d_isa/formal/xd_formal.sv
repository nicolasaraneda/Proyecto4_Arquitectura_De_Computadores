// xd_formal.sv: propiedades formales de la extensión de la ISA (pieza D).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Cada módulo de este archivo es el tope de una tarea de formal/xd.sby. Sus
// entradas quedan libres, así que cada aserción se prueba para todos los
// valores de los operandos (son circuitos combinacionales: basta un paso).
// La especificación de cada instrucción se escribe aquí de nuevo, de la forma
// más directa posible y sin reutilizar el RTL que se prueba.
//
//   f_ema           xd_ema contra rd = rs2 + ((rs1 - rs2) >>> k), para cada
//                   conjunto de k (KB = 0, 2, 3 y 5)
//   f_caminos       las tres formas de integrar el paso de la media dan lo
//                   mismo (xd_ema, la resta de la ALU más xd_unit, y sub más
//                   emad por xd_opa y el sumador de espino_alu); devk y
//                   mulstep por el sumador de la ALU contra su especificación
//   f_alu_base      xd_alu con lane_op = 0 es espino_alu
//   f_alu_carriles  los carriles de xd_alu contra la especificación por carril
//   f_simd          xd_simd8 (las diez operaciones) contra la especificación
//   f_mul8          8 pasos de mulstep dan el producto (multiplicando de 12 bits)
//   f_div8          8 pasos de divstep dan cociente y resto cuando N < 256 D
//                   (divisor de 8 bits, el precio)
//   f_divpaso       un paso de divstep, para cualquier divisor de 24 bits

`ifndef KB
  `define KB 0
`endif

// --- Especificación --------------------------------------------------------------

// x >>> k escrito bit a bit, sin el operador de desplazamiento
module spec_sra (input wire [31:0] x, input wire [4:0] k, output reg [31:0] y);
  integer i;
  always @* begin
    for (i = 0; i < 32; i = i + 1)
      y[i] = (i + k < 32) ? x[(i + k) % 32] : x[31];
  end
endmodule

// Un carril de 8 bits. op es funct7[3:0].
module spec_carril (input wire [3:0] op, input wire [7:0] a, input wire [7:0] b,
                    input wire [7:0] a0, output reg [7:0] r);
  wire [8:0] suma = {1'b0, a} + {1'b0, b};
  always @* begin
    case (op)
      4'd0:    r = a + b;
      4'd1:    r = a - b;
      4'd2:    r = (a < b) ? 8'hFF : 8'h00;
      4'd3:    r = ($signed(a) < $signed(b)) ? 8'hFF : 8'h00;
      4'd4:    r = (a < b) ? a : b;
      4'd5:    r = (a < b) ? b : a;
      4'd6:    r = (suma > 9'd255) ? 8'hFF : suma[7:0];
      4'd7:    r = (a < b) ? 8'h00 : a - b;
      default: r = a0;                 // pbcast8: el byte bajo de rs1
    endcase
  end
endmodule

// --- xd_ema ----------------------------------------------------------------------
module f_ema (input wire [31:0] a, input wire [31:0] b, input wire [4:0] k);
  localparam integer KB = `KB;
  wire [31:0] r, d_sra;
  xd_ema #(.KB(KB)) dut (.a_i(a), .b_i(b), .k_i(k), .r_o(r));

  wire [4:0]  kk   = (KB == 0) ? 5'd5 : k;
  wire        k_ok = (KB == 0) || (KB == 2 && k >= 5'd4 && k <= 5'd7) || (KB == 3 && k <= 5'd7) || (KB == 5);
  spec_sra u_sra (.x(a - b), .k(kk), .y(d_sra));
  always @* if (k_ok) assert (r == b + d_sra);
endmodule

// --- Las integraciones que comparten la ALU --------------------------------------
module f_caminos (input wire [31:0] a, input wire [31:0] b, input wire [4:0] k);
  localparam integer KB = `KB;
  wire [4:0] kk   = (KB == 0) ? 5'd5 : k;
  wire       k_ok = (KB == 0) || (KB == 2 && k >= 5'd4 && k <= 5'd7) || (KB == 3 && k <= 5'd7) || (KB == 5);

  // 1. ema autónoma
  wire [31:0] r_ema;
  xd_ema #(.KB(KB)) u_ema (.a_i(a), .b_i(b), .k_i(k), .r_o(r_ema));

  // 2. ema con la resta de la ALU (XD_EMAALU): la ALU resta y xd_unit desplaza y suma
  wire [31:0] resta, r_emaalu;
  espino_alu u_sub (.operator_i(4'd1), .operand_a_i(a), .operand_b_i(b), .result_o(resta), .cmp_result_o());
  xd_unit #(.EMA_KB(KB), .EMA_ALU(1)) u_unit (
    .rs1_i(a), .rs2_i(b), .alu_i(resta), .funct3_i(3'b000), .funct7_i({2'b00, k}), .result_o(r_emaalu));

  // 3. sub y después emad: xd_opa entrega dev >>> k y la ALU suma el estado
  wire [31:0] opa_emad, r_emad;
  xd_opa #(.MULSTEP(1), .EMAD_KB(KB), .DEVK_KB(KB), .BCAST(1)) u_opa_emad (
    .rs1_i(resta), .funct3_i(3'b100), .funct7_i({2'b00, k}), .a_o(opa_emad), .b_cero_o());
  espino_alu u_add (.operator_i(4'd0), .operand_a_i(opa_emad), .operand_b_i(b), .result_o(r_emad), .cmp_result_o());

  // devk: xd_opa entrega rs1 << k y la ALU resta rs2
  wire [31:0] opa_devk, r_devk;
  xd_opa #(.MULSTEP(1), .EMAD_KB(KB), .DEVK_KB(KB), .BCAST(1)) u_opa_devk (
    .rs1_i(a), .funct3_i(3'b101), .funct7_i({2'b00, k}), .a_o(opa_devk), .b_cero_o());
  espino_alu u_sub2 (.operator_i(4'd1), .operand_a_i(opa_devk), .operand_b_i(b), .result_o(r_devk), .cmp_result_o());
  reg [31:0] izq;
  integer i;
  always @* begin
    for (i = 0; i < 32; i = i + 1)
      izq[i] = (i >= kk) ? a[(i + 32 - kk) % 32] : 1'b0;
  end

  // mulstep: xd_opa entrega rs1 << 1, anula B si rs1[31] = 0, y la ALU suma
  wire [31:0] opa_mul, r_mulalu, r_mul;
  wire        b_cero;
  xd_opa #(.MULSTEP(1), .EMAD_KB(KB), .DEVK_KB(KB), .BCAST(1)) u_opa_mul (
    .rs1_i(a), .funct3_i(3'b010), .funct7_i(7'b0), .a_o(opa_mul), .b_cero_o(b_cero));
  espino_alu u_add2 (.operator_i(4'd0), .operand_a_i(opa_mul), .operand_b_i(b_cero ? 32'b0 : b),
                     .result_o(r_mulalu), .cmp_result_o());
  xd_mulstep u_mul (.a_i(a), .b_i(b), .r_o(r_mul));

  // pbcast8 por el operando A: la ALU suma x0
  wire [31:0] opa_bc;
  xd_opa #(.MULSTEP(1), .EMAD_KB(KB), .DEVK_KB(KB), .BCAST(1)) u_opa_bc (
    .rs1_i(a), .funct3_i(3'b001), .funct7_i(7'b0001000), .a_o(opa_bc), .b_cero_o());

  always @* begin
    if (k_ok) begin
      assert (r_emaalu == r_ema);
      assert (r_emad == r_ema);
      assert (r_devk == izq - b);
    end
    assert (r_mulalu == r_mul);
    assert (r_mul == {a[30:0], 1'b0} + (a[31] ? b : 32'b0));
    assert (opa_bc == {4{a[7:0]}});
  end
endmodule

// --- xd_alu ----------------------------------------------------------------------
module f_alu_base (input wire [3:0] op, input wire [31:0] a, input wire [31:0] b);
  wire [31:0] r_base, r_xd;
  wire        c_base, c_xd;
  espino_alu u_base (.operator_i(op), .operand_a_i(a), .operand_b_i(b), .result_o(r_base), .cmp_result_o(c_base));
  xd_alu     u_xd   (.operator_i(op), .operand_a_i(a), .operand_b_i(b), .lane_op_i(3'd0),
                     .result_o(r_xd), .cmp_result_o(c_xd));
  always @* begin
    assert (c_xd == c_base);
    // En los branches (operadores 10 a 15) nadie usa result_o
    if (op < 4'd10) assert (r_xd == r_base);
  end
endmodule

module f_alu_carriles (input wire [2:0] lane, input wire resta, input wire [31:0] a, input wire [31:0] b);
  wire [31:0] r, spec;
  xd_alu u_xd (.operator_i(resta ? 4'd1 : 4'd0), .operand_a_i(a), .operand_b_i(b), .lane_op_i(lane),
               .result_o(r), .cmp_result_o());
  // (lane_op, operador) -> operación del grupo de carriles
  reg [3:0] op;
  reg       valido;
  always @* begin
    valido = 1'b1;
    case ({lane, resta})
      {3'd1, 1'b0}: op = 4'd0;      // padd8
      {3'd1, 1'b1}: op = 4'd1;      // psub8
      {3'd2, 1'b1}: op = 4'd2;      // pcmpltu8
      {3'd3, 1'b0}: op = 4'd6;      // paddus8
      {3'd4, 1'b1}: op = 4'd7;      // psubus8
      default: begin op = 4'd0; valido = 1'b0; end
    endcase
  end
  genvar g;
  generate
    for (g = 0; g < 4; g = g + 1) begin : g_c
      spec_carril u_s (.op(op), .a(a[8*g +: 8]), .b(b[8*g +: 8]), .a0(a[7:0]), .r(spec[8*g +: 8]));
    end
  endgenerate
  always @* if (valido) assert (r == spec);
endmodule

// --- xd_simd8 --------------------------------------------------------------------
module f_simd (input wire [3:0] op, input wire [31:0] a, input wire [31:0] b);
  wire [31:0] r, spec;
  xd_simd8 #(.CON_SIGNO(1), .MINMAX(1), .SATURA(1), .BCAST(1), .MOVMSK(1), .CMP_BIT(0)) dut (
    .a_i(a), .b_i(b), .op_i(op), .r_o(r));
  genvar g;
  generate
    for (g = 0; g < 4; g = g + 1) begin : g_c
      spec_carril u_s (.op(op), .a(a[8*g +: 8]), .b(b[8*g +: 8]), .a0(a[7:0]), .r(spec[8*g +: 8]));
    end
  endgenerate
  always @* begin
    if (op <= 4'd8) assert (r == spec);
    if (op == 4'd9) assert (r == {28'b0, a[31], a[23], a[15], a[7]});   // pmovmsk8
  end
endmodule

// --- mulstep y divstep: la secuencia completa ------------------------------------
// El producto se prueba con el multiplicando de MUL_W bits y separado en 16
// casos, uno por cada valor de los 4 bits altos del multiplicador (entre los
// 16 cubren los 256 multiplicadores). Con 12 bits termina en medio minuto. Con
// 16 y con 24 bits (el ancho que acepta mulstep con 8 pasos) no terminó en
// 200 a 300 s: quedan como tareas mul8_16 y mul8_24, fuera de make formal.
`ifndef MUL_W
  `define MUL_W 12
`endif
module f_mul8 (input wire [3:0] q_bajo, input wire [`MUL_W-1:0] m_i);
  wire [23:0] m = m_i;
  genvar h, g;
  generate
    for (h = 0; h < 16; h = h + 1) begin : g_caso
      localparam [3:0] Q_ALTO = h;
      wire [7:0]  q = {Q_ALTO, q_bajo};
      wire [31:0] x [0:8];
      assign x[0] = {q, 24'b0};
      for (g = 0; g < 8; g = g + 1) begin : g_paso
        xd_mulstep u_p (.a_i(x[g]), .b_i({8'b0, m}), .r_o(x[g+1]));
      end
      always @* assert (x[8] == q * m);
    end
  endgenerate
endmodule

// El cociente se prueba con el divisor de DIV_W bits. Con 8 bits es el caso
// de la contabilidad (el divisor es el precio) y termina en segundos. Con 24
// bits, que es todo lo que acepta divstep, ningún resolvedor terminó en 300 s.
`ifndef DIV_W
  `define DIV_W 8
`endif
module f_div8 (input wire [31:0] n, input wire [`DIV_W-1:0] d_i);
  wire [23:0] d = d_i;
  wire [31:0] x [0:8];
  assign x[0] = n;
  genvar g;
  generate
    for (g = 0; g < 8; g = g + 1) begin : g_paso
      xd_divstep u_p (.a_i(x[g]), .b_i({8'b0, d}), .r_o(x[g+1]));
    end
  endgenerate
  wire [7:0]  cociente = x[8][7:0];
  wire [23:0] resto    = x[8][31:8];
  wire [32:0] vuelta   = cociente * d + resto;     // 8 x 24 bits más 24 bits: cabe en 33
  always @* begin
    if (d != 24'b0 && {1'b0, n} < {1'b0, d, 8'b0}) begin    // N < 256 D
      assert (resto < d);
      assert (vuelta == {1'b0, n});
    end
  end
endmodule

// Un paso de divstep, para cualquier divisor de 24 bits: si el resto parcial
// es menor que D, el paso deja {2 R + bit que entra} = bit de cociente * D +
// R nuevo, con R nuevo < D. Los 8 pasos del cociente completo son 8
// aplicaciones de este lema.
module f_divpaso (input wire [31:0] x, input wire [23:0] d);
  wire [31:0] y;
  xd_divstep u_p (.a_i(x), .b_i({8'b0, d}), .r_o(y));
  wire [24:0] entra = x[31:7];                     // 2 R + bit alto de Q
  wire [24:0] sale  = (y[0] ? {1'b0, d} : 25'b0) + {1'b0, y[31:8]};
  always @* begin
    if (x[31:8] < d) begin
      assert (y[31:8] < d);
      assert (sale == entra);
      assert (y[7:1] == x[6:0]);
    end
  end
endmodule
