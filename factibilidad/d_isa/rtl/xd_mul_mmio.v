// xd_mul_mmio.v: periférico MMIO con un multiplicador serial de 24 x 8 bits.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Es la alternativa al paso de multiplicación como instrucción: el programa
// escribe los operandos y lee el producto unos ciclos después. Por dentro es
// el mismo xd_mulstep con un registro y un contador.
//
//   palabra 0  MULA  escritura: multiplicando, bits 23:0
//   palabra 1  MULB  escritura: multiplicador, bits 7:0. Parte el producto.
//   palabra 2  MULP  lectura: producto de 32 bits
//   palabra 3  MULS  lectura: bit 0 = ocupado
//
// Tiempos: el producto queda en el registro 8 flancos después del flanco en
// que se escribe MULB. La lectura es registrada, igual que en pochoco_periph,
// y captura el registro antes del flanco: una lectura de MULP cuya petición
// llega al bus 9 ciclos o más después de la de esa escritura entrega el
// producto, y una pedida a los 8 ciclos todavía no tiene el último paso.
// Escribir MULB mientras está ocupado parte de nuevo.
//
// Tiene estado (un producto en curso): si varios hilos lo comparten, solo uno
// puede usarlo o hay que guardar un contexto por hilo.
// Modelo de referencia: ref/xd.py, clase MulMMIO.
//
// MUTA_XD_MMIO es una mutación de prueba (tools/tb_modulos.sh): hace 7 pasos
// en vez de 8. Solo se activa desde la línea de comandos.

module xd_mul_mmio (
  input  wire        clk_i,
  input  wire        rst_ni,
  input  wire        req_i,     // acceso a este periférico en este ciclo
  input  wire        we_i,
  input  wire [1:0]  off_i,     // número de palabra
  input  wire [31:0] wdata_i,
  output reg  [31:0] rdata_o
);

  reg  [23:0] a_q;
  reg  [31:0] x_q;
  reg  [3:0]  cnt_q;
  wire [31:0] paso;
  wire        ocupado = (cnt_q != 4'd0);

  xd_mulstep u_paso (.a_i(x_q), .b_i({8'b0, a_q}), .r_o(paso));

  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      a_q   <= 24'b0;
      x_q   <= 32'b0;
      cnt_q <= 4'd0;
    end else begin
      if (req_i && we_i && off_i == 2'd0) a_q <= wdata_i[23:0];
      if (req_i && we_i && off_i == 2'd1) begin
        x_q   <= {wdata_i[7:0], 24'b0};
`ifdef MUTA_XD_MMIO
        cnt_q <= 4'd7;
`else
        cnt_q <= 4'd8;
`endif
      end else if (ocupado) begin
        x_q   <= paso;
        cnt_q <= cnt_q - 4'd1;
      end
    end
  end

  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) rdata_o <= 32'b0;
    else if (req_i && !we_i) rdata_o <= off_i[0] ? {31'b0, ocupado} : x_q;
  end

endmodule
