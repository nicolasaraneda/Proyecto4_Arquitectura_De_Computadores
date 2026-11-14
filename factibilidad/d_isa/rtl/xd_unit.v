// xd_unit.v: unidad de ejecución de la extensión en custom-0 (pieza D).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Junta las instrucciones nuevas detrás de una sola interfaz: los dos
// operandos (rs1 y rs2), los campos funct3 y funct7 de la instrucción y el
// resultado que va a rd. Es combinacional y no tiene estado, así que en un
// pipeline sin detenciones ocupa exactamente el ciclo de ejecución. Quien la
// integra solo tiene que escribir result_o en rd cuando la instrucción es de
// custom-0 (opcode 0001011) y funct3 es uno de los grupos presentes.
//
//   funct3  grupo       parámetro que lo incluye
//   000     ema         EMA_KB >= 0 (ver xd_ema.v: 0, 2, 3 o 5), y EMA_ALU
//   001     carriles    SIMD >= 0   (máscara de opciones, ver abajo)
//   010     producto    MULSTEP, DIVSTEP, MULC_AW > 0 (funct7[1:0] = 0, 1, 2)
//   011     srak        SRAK_KB >= 0 (ver xd_srak.v: 0, 2, 3 o 5)
//
// SIMD es -1 (sin carriles) o una máscara de bits con las opciones de
// xd_simd8: bit 0 CON_SIGNO, bit 1 MINMAX, bit 2 SATURA, bit 3 BCAST,
// bit 4 MOVMSK, bit 5 CMP_BIT. Con 0 quedan padd8, psub8 y pcmpltu8.
//
// En ema, rs1 es la muestra y rs2 el estado: rd = rs2 + ((rs1 - rs2) >>> k).
// EMA_ALU = 1 es la integración que comparte la resta: la unidad no resta,
// espera en alu_i la resta rs1 - rs2 que ya hace la ALU del core y entrega
// rs2 + (alu_i >>> k). Con EMA_ALU = 0 la unidad es autónoma (xd_ema, con su
// propio restador) y alu_i no se usa. Las dos calculan lo mismo con la misma
// codificación (formal/xd_ema_alu.sby lo prueba).
//
// mulstep, emad y devk tienen además una integración que no pasa por esta
// unidad: usan el sumador de la ALU con el operando A desplazado (xd_opa.v).

module xd_unit #(
  parameter integer EMA_KB  = -1,
  parameter integer EMA_K0  = 5,
  parameter integer EMA_ALU = 0,
  parameter integer SIMD    = -1,
  parameter integer MULSTEP = 0,
  parameter integer DIVSTEP = 0,
  parameter integer MULC_AW = 0,
  parameter integer SRAK_KB = -1,
  parameter integer SRAK_K0 = 5
) (
  input  wire [31:0] rs1_i,
  input  wire [31:0] rs2_i,
  input  wire [31:0] alu_i,      // resultado de la ALU del core (solo con EMA_ALU = 1)
  input  wire [2:0]  funct3_i,
  input  wire [6:0]  funct7_i,
  output reg  [31:0] result_o
);

  wire [31:0] r_ema, r_simd, r_mulstep, r_divstep, r_mulc, r_srak;

  generate
    if (EMA_KB >= 0 && EMA_ALU != 0) begin : g_ema_alu
      wire [31:0] desplazado;
      xd_srak #(.KB(EMA_KB), .K0(EMA_K0)) u_sra (
        .a_i(alu_i), .k_i(funct7_i[4:0]), .r_o(desplazado));
      assign r_ema = rs2_i + desplazado;
    end else if (EMA_KB >= 0) begin : g_ema
      xd_ema #(.KB(EMA_KB), .K0(EMA_K0)) u_ema (
        .a_i(rs1_i), .b_i(rs2_i), .k_i(funct7_i[4:0]), .r_o(r_ema));
    end else begin : g_sin_ema
      assign r_ema = 32'b0;
    end

    if (SIMD >= 0) begin : g_simd
      xd_simd8 #(.CON_SIGNO((SIMD >> 0) & 1), .MINMAX((SIMD >> 1) & 1), .SATURA((SIMD >> 2) & 1),
                 .BCAST((SIMD >> 3) & 1), .MOVMSK((SIMD >> 4) & 1), .CMP_BIT((SIMD >> 5) & 1)) u_simd (
        .a_i(rs1_i), .b_i(rs2_i), .op_i(funct7_i[3:0]), .r_o(r_simd));
    end else begin : g_sin_simd
      assign r_simd = 32'b0;
    end

    if (MULSTEP != 0) begin : g_mulstep
      xd_mulstep u_mulstep (.a_i(rs1_i), .b_i(rs2_i), .r_o(r_mulstep));
    end else begin : g_sin_mulstep
      assign r_mulstep = 32'b0;
    end

    if (DIVSTEP != 0) begin : g_divstep
      xd_divstep u_divstep (.a_i(rs1_i), .b_i(rs2_i), .r_o(r_divstep));
    end else begin : g_sin_divstep
      assign r_divstep = 32'b0;
    end

    if (SRAK_KB >= 0) begin : g_srak
      xd_srak #(.KB(SRAK_KB), .K0(SRAK_K0)) u_srak (
        .a_i(rs1_i), .k_i(funct7_i[4:0]), .r_o(r_srak));
    end else begin : g_sin_srak
      assign r_srak = 32'b0;
    end

    if (MULC_AW != 0) begin : g_mulc
      xd_mulc #(.AW(MULC_AW), .BW(8)) u_mulc (.a_i(rs1_i), .b_i(rs2_i), .r_o(r_mulc));
    end else begin : g_sin_mulc
      assign r_mulc = 32'b0;
    end
  endgenerate

  // Dentro del grupo de producto solo se multiplexa entre lo que existe
  localparam integer N_PROD = (MULSTEP != 0) + (DIVSTEP != 0) + (MULC_AW != 0);
  reg [31:0] r_prod;
  always @* begin
    if (N_PROD <= 1)
      r_prod = r_mulstep | r_divstep | r_mulc;      // los ausentes valen cero
    else begin
      case (funct7_i[1:0])
        2'd0:    r_prod = r_mulstep;
        2'd1:    r_prod = r_divstep;
        default: r_prod = r_mulc;
      endcase
    end
  end

  localparam integer N_GRUPOS = (EMA_KB >= 0) + (SIMD >= 0) + (N_PROD != 0) + (SRAK_KB >= 0);
  always @* begin
    if (N_GRUPOS <= 1)
      result_o = r_ema | r_simd | r_prod | r_srak;
    else begin
      case (funct3_i[1:0])
        2'd0:    result_o = r_ema;
        2'd1:    result_o = r_simd;
        2'd2:    result_o = r_prod;
        default: result_o = r_srak;
      endcase
    end
  end

  wire _unused = &{1'b0, funct3_i[2], funct7_i[6:5], alu_i};

endmodule
