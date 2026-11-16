// xd_simd8.v: cuatro carriles de 8 bits empaquetados en un registro de 32.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Combinacional, sin estado. El carril i ocupa los bits 8i+7:8i. Ningún
// acarreo pasa de un carril al siguiente. Modelo de referencia: ref/xd.py,
// función simd8.
//
//   op_i  nombre     resultado por carril                       parámetro
//   0     padd8      (a + b) mod 256                            siempre
//   1     psub8      (a - b) mod 256                            siempre
//   2     pcmpltu8   0xFF si a < b sin signo, 0x00 si no        siempre
//   3     pcmplt8    0xFF si a < b con signo, 0x00 si no        CON_SIGNO
//   4     pminu8     el menor, sin signo                        MINMAX
//   5     pmaxu8     el mayor, sin signo                        MINMAX
//   6     paddus8    min(a + b, 255)                            SATURA
//   7     psubus8    max(a - b, 0)                              SATURA
//   8     pbcast8    a_i[7:0] en los cuatro carriles            BCAST
//   9     pmovmsk8   bits 3:0 = bit 7 de cada carril de a_i     MOVMSK
//
// Cada carril tiene un solo sumador de 9 bits, que hace a + b o a - b. La
// comparación, el mínimo, el máximo y la saturación salen de su acarreo.
// Una operación cuyo parámetro vale 0 queda reservada (entrega la suma o la
// resta, sin garantía).
//
// CMP_BIT = 1 es la alternativa que se evaluó y no se eligió: las dos
// comparaciones entregan un bit por carril en los bits 3:0 en vez de una
// máscara por carril.
//
// MUTA_XD_SIMD es una mutación de prueba (tools/tb_modulos.sh): el acarreo de
// cada carril entra al siguiente. Solo se activa desde la línea de comandos.

module xd_simd8 #(
  parameter CON_SIGNO = 1,
  parameter MINMAX    = 1,
  parameter SATURA    = 1,
  parameter BCAST     = 1,
  parameter MOVMSK    = 1,
  parameter CMP_BIT   = 0
) (
  input  wire [31:0] a_i,     // rs1
  input  wire [31:0] b_i,     // rs2
  input  wire [3:0]  op_i,    // funct7[3:0]
  output reg  [31:0] r_o
);

  localparam [3:0] OP_ADD = 4'd0, OP_SUB = 4'd1, OP_LTU = 4'd2, OP_LT = 4'd3,
                   OP_MIN = 4'd4, OP_MAX = 4'd5, OP_ADDUS = 4'd6, OP_SUBUS = 4'd7,
                   OP_BCAST = 4'd8, OP_MOVMSK = 4'd9;

  // Todo menos las dos sumas usa a - b
  wire resta = (op_i != OP_ADD) & (op_i != OP_ADDUS);

  wire [31:0] carriles;
  wire [3:0]  menor_u, menor_s;
  wire [4:0]  acarreo;
  assign acarreo[0] = 1'b0;

  genvar i;
  generate
    for (i = 0; i < 4; i = i + 1) begin : g_carril
      wire [7:0] a = a_i[8*i +: 8];
      wire [7:0] b = b_i[8*i +: 8];
      // a + b, o a + ~b + 1. El bit 8 es el acarreo: en la resta vale 1
      // cuando a >= b.
`ifdef MUTA_XD_SIMD
      wire [8:0] s = {1'b0, a} + {1'b0, b ^ {8{resta}}} + {8'b0, resta} + {8'b0, acarreo[i] & ~resta};
`else
      wire [8:0] s = {1'b0, a} + {1'b0, b ^ {8{resta}}} + {8'b0, resta};
`endif
      assign acarreo[i+1] = s[8];
      wire       ltu = resta & ~s[8];
      wire       lt  = (a[7] ^ b[7]) ? a[7] : ltu;
      reg  [7:0] r;
      always @* begin
        r = s[7:0];
        case (op_i)
          OP_LTU:   r = {8{ltu}};
          OP_LT:    if (CON_SIGNO) r = {8{lt}};
          OP_MIN:   if (MINMAX)    r = ltu ? a : b;
          OP_MAX:   if (MINMAX)    r = ltu ? b : a;
          OP_ADDUS: if (SATURA)    r = s[8] ? 8'hFF : s[7:0];
          OP_SUBUS: if (SATURA)    r = ltu ? 8'h00 : s[7:0];
          OP_BCAST: if (BCAST)     r = a_i[7:0];
          default: ;
        endcase
      end
      assign carriles[8*i +: 8] = r;
      assign menor_u[i] = ltu;
      assign menor_s[i] = lt;
    end
  endgenerate

  always @* begin
    r_o = carriles;
    if (MOVMSK && op_i == OP_MOVMSK)
      r_o = {28'b0, a_i[31], a_i[23], a_i[15], a_i[7]};
    if (CMP_BIT && op_i == OP_LTU)
      r_o = {28'b0, menor_u};
    if (CMP_BIT && CON_SIGNO && op_i == OP_LT)
      r_o = {28'b0, menor_s};
  end

  wire _unused = &{1'b0, acarreo};

endmodule
