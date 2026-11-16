// xd_alu.v: ALU del Espino con cuatro carriles de 8 bits en su propio sumador.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Reemplaza a espino_alu cuando los carriles se integran compartiendo el
// sumador en vez de agregar una unidad aparte (xd_simd8). Con lane_op_i = 0
// entrega lo mismo que espino_alu: cmp_result_o en las 16 operaciones y
// result_o en todas las que escriben un registro o direccionan la memoria
// (formal/xd_alu_base.sby lo prueba para todas las entradas). La única
// diferencia está en las seis comparaciones de los branches (operadores 10 a
// 15), donde espino_alu deja en result_o la suma y esta ALU la resta: en un
// branch nadie usa result_o. Con lane_op_i distinto de cero, el acarreo se
// corta en los bits 8, 16 y 24 y cada carril de 8 bits suma o resta por
// separado:
//
//   lane_op_i  operator_i  resultado por carril                instrucción
//   1          ALU_ADD     (a + b) mod 256                     padd8
//   1          ALU_SUB     (a - b) mod 256                     psub8
//   2          ALU_SUB     0xFF si a < b sin signo, 0x00 si no pcmpltu8
//   3          ALU_ADD     min(a + b, 255)                     paddus8
//   4          ALU_SUB     max(a - b, 0)                       psubus8
//
// Hay un solo sumador con inversión del operando B, que se usa para sumar,
// restar y comparar. La comparación y las saturaciones salen del acarreo de
// cada carril. Es combinacional y no tiene estado. Modelo de referencia de
// los carriles: ref/xd.py, función simd8.
//
// MUTA_XD_ALU es una mutación de prueba (tools/tb_modulos.sh): el acarreo no
// se corta entre los carriles 1 y 2. Solo se activa desde la línea de comandos.

module xd_alu (
  input  wire [3:0]  operator_i,
  input  wire [31:0] operand_a_i,
  input  wire [31:0] operand_b_i,
  input  wire [2:0]  lane_op_i,
  output reg  [31:0] result_o,
  output reg         cmp_result_o
);

  localparam [3:0] ALU_ADD  = 4'd0,
                   ALU_SUB  = 4'd1,
                   ALU_XOR  = 4'd2,
                   ALU_OR   = 4'd3,
                   ALU_AND  = 4'd4,
                   ALU_SLT  = 4'd8,
                   ALU_SLTU = 4'd9,
                   ALU_EQ   = 4'd10,
                   ALU_NE   = 4'd11,
                   ALU_LT   = 4'd12,
                   ALU_GE   = 4'd13,
                   ALU_LTU  = 4'd14,
                   ALU_GEU  = 4'd15;

  localparam [2:0] L_NO = 3'd0, L_LTU = 3'd2, L_ADDUS = 3'd3, L_SUBUS = 3'd4;

  // Restan: sub, slt, sltu y las seis comparaciones de los branches
  wire resta    = operator_i[3] | (operator_i == ALU_SUB);
  wire carriles = (lane_op_i != L_NO);

  wire [31:0] bx = operand_b_i ^ {32{resta}};
  wire [4:0]  c;
  wire [31:0] r;
  assign c[0] = resta;

  genvar i;
  generate
    for (i = 0; i < 4; i = i + 1) begin : g_carril
      // Acarreo de entrada: el del carril anterior, o el de una resta nueva
      // (a + ~b + 1) cuando los carriles van separados
`ifdef MUTA_XD_ALU
      wire       cin = (i == 0 || (carriles && i != 2)) ? resta : c[i];
`else
      wire       cin = (i == 0 || carriles) ? resta : c[i];
`endif
      wire [8:0] t = {1'b0, operand_a_i[8*i +: 8]} + {1'b0, bx[8*i +: 8]} + {8'b0, cin};
      assign c[i+1] = t[8];           // en una resta vale 1 cuando a >= b
      wire pone  = ((lane_op_i == L_LTU)   & ~t[8]) | ((lane_op_i == L_ADDUS) &  t[8]);
      wire quita = ((lane_op_i == L_LTU)   &  t[8]) | ((lane_op_i == L_SUBUS) & ~t[8]);
      assign r[8*i +: 8] = (t[7:0] | {8{pone}}) & ~{8{quita}};
    end
  endgenerate

  // Comparaciones de 32 bits, con el acarreo final de la resta
  wire cmp_eq  = (operand_a_i == operand_b_i);
  wire cmp_ltu = ~c[4];
  wire cmp_lt  = (operand_a_i[31] ^ operand_b_i[31]) ? operand_a_i[31] : ~c[4];

  always @* begin
    case (operator_i)
      ALU_EQ:  cmp_result_o =  cmp_eq;
      ALU_NE:  cmp_result_o = ~cmp_eq;
      ALU_LT:  cmp_result_o =  cmp_lt;
      ALU_GE:  cmp_result_o = ~cmp_lt;
      ALU_LTU: cmp_result_o =  cmp_ltu;
      ALU_GEU: cmp_result_o = ~cmp_ltu;
      default: cmp_result_o = 1'b0;
    endcase
  end

  // Resultado. Igual que en espino_alu, los shifts (5, 6 y 7) y las
  // comparaciones de los branches entregan la suma o la resta.
  always @* begin
    case (operator_i)
      ALU_XOR:  result_o = operand_a_i ^ operand_b_i;
      ALU_OR:   result_o = operand_a_i | operand_b_i;
      ALU_AND:  result_o = operand_a_i & operand_b_i;
      ALU_SLT:  result_o = {31'b0, cmp_lt};
      ALU_SLTU: result_o = {31'b0, cmp_ltu};
      default:  result_o = r;
    endcase
  end

endmodule
