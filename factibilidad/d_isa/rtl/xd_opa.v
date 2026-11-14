// xd_opa.v: operando A desplazado para el sumador de la ALU.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Es la forma barata de integrar las instrucciones que son "un
// desplazamiento por una constante y una suma": no agregan un sumador ni una
// entrada al multiplexor de escritura. El core entrega rs1 y los campos
// funct3 y funct7 de la instrucción en ejecución, este módulo entrega el
// operando A que entra a la ALU, y el decodificador pide a la ALU una suma o
// una resta con rs2. Combinacional, sin estado.
//
//   funct3  instrucción  operando A      la ALU hace     parámetro
//   001     pbcast8      rs1[7:0] x 4    A + rs2 (rs2 = x0)        BCAST
//   010     mulstep      rs1 << 1        A + (rs1[31] ? rs2 : 0)   MULSTEP
//   100     emad         rs1 >>> k       A + rs2         EMAD_KB >= 0
//   101     devk         rs1 << k        A - rs2         DEVK_KB >= 0
//
// pbcast8 solo pasa por aquí cuando los carriles están en la ALU (xd_alu.v).
// Con la unidad de carriles aparte (xd_simd8) lo hace esa unidad.
//
// En mulstep el operando B vale cero cuando el bit que sale del multiplicador
// (rs1[31]) es 0: b_cero_o lo indica y el core anula el operando B.
//
// EMAD_KB y DEVK_KB eligen qué valores de k se implementan, igual que en
// xd_srak.v: 0 un solo k cableado (K0), 2 k entre 4 y 7, 3 k entre 0 y 7,
// 5 k entre 0 y 31. Con -1 la instrucción no está.
// Modelo de referencia: ref/xd.py, funciones mulstep, emad y devk.
//
// MUTA_XD_OPA es una mutación de prueba (tools/tb_modulos.sh): el
// desplazamiento a la derecha pasa a ser lógico. Solo se activa desde la línea
// de comandos.

module xd_opa #(
  parameter integer MULSTEP = 0,
  parameter integer EMAD_KB = -1,
  parameter integer DEVK_KB = -1,
  parameter integer BCAST   = 0,
  parameter integer K0      = 5
) (
  input  wire [31:0] rs1_i,
  input  wire [2:0]  funct3_i,
  input  wire [6:0]  funct7_i,
  output reg  [31:0] a_o,        // operando A de la ALU
  output wire        b_cero_o    // el operando B debe valer cero
);

  wire [4:0] k = funct7_i[4:0];

  // rs1 >>> k
  wire signed [31:0] s  = rs1_i;
  wire signed [31:0] s4 = s >>> 4;
  reg  signed [31:0] der;
  always @* begin
    case (EMAD_KB)
      0:       der = s >>> K0;
      2:       der = s4 >>> k[1:0];
      3:       der = s >>> k[2:0];
      default: der = s >>> k;
    endcase
  end

  // rs1 << k
  wire [31:0] i4 = rs1_i << 4;
  reg  [31:0] izq;
  always @* begin
    case (DEVK_KB)
      0:       izq = rs1_i << K0;
      2:       izq = i4 << k[1:0];
      3:       izq = rs1_i << k[2:0];
      default: izq = rs1_i << k;
    endcase
  end

  // Solo se multiplexa entre lo que existe
  wire es_emad = (EMAD_KB >= 0) && (funct3_i == 3'b100 || (MULSTEP == 0 && DEVK_KB < 0 && BCAST == 0));
  wire es_devk = (DEVK_KB >= 0) && (funct3_i == 3'b101 || (MULSTEP == 0 && EMAD_KB < 0 && BCAST == 0));
  wire es_bcast = (BCAST != 0) && (funct3_i == 3'b001 || (MULSTEP == 0 && EMAD_KB < 0 && DEVK_KB < 0));

  always @* begin
    a_o = {rs1_i[30:0], 1'b0};                         // mulstep
`ifdef MUTA_XD_OPA
    if (es_emad) a_o = (EMAD_KB == 0) ? ($unsigned(s) >> K0) : (der & 32'h7FFFFFFF);
`else
    if (es_emad) a_o = der;
`endif
    if (es_devk) a_o = izq;
    if (es_bcast) a_o = {4{rs1_i[7:0]}};
  end

  assign b_cero_o = (MULSTEP != 0) && (funct3_i == 3'b010) && ~rs1_i[31];

  wire _unused = &{1'b0, funct7_i[6:5], k, s4, i4};

endmodule
