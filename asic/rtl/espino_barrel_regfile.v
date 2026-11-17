// espino_barrel_regfile.v: banco de registros de cuatro contextos en flip-flops,
// para la edición ASIC (asic/README.md).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Reemplaza a rtl/espino_core/espino_barrel_regfile.v, que instancia SB_RAM40_4K:
// en celdas estándar no hay BRAM. Misma interfaz y misma temporización: la
// lectura es registrada (el dato sale un flanco después de presentar la
// dirección), como la BRAM con READ_MODE 0, y la escritura ocurre en el flanco.
// Sin adelantamiento, igual que el original: la lectura es de la etapa R y la
// escritura de la etapa M, que son de hilos distintos (rtl/espino_core/
// espino_barrel_regfile.v, encabezado).
//
// x0 de cada contexto no se guarda: se lee como 0. Son 4 x 15 registros de 32
// bits, 1920 flip-flops, sin reset (la BRAM tampoco tiene). Un registro que el
// programa lee antes de escribirlo daría un valor indefinido en simulación;
// sw/fondo.s no lo hace (la tabla de arranque escribe lo que cada hilo usa).
module espino_barrel_regfile (
  input  wire        clk_i,
  input  wire [5:0]  raddr_a_i,    // {hilo, rs1}
  output reg  [31:0] rdata_a_o,
  input  wire [5:0]  raddr_b_i,    // {hilo, rs2}
  output reg  [31:0] rdata_b_o,
  input  wire [5:0]  waddr_i,      // {hilo, rd}
  input  wire [31:0] wdata_i,
  input  wire        we_i
);
  reg [31:0] r [0:63];
  always @(posedge clk_i) begin
    if (we_i && waddr_i[3:0] != 4'd0) r[waddr_i] <= wdata_i;
    rdata_a_o <= (raddr_a_i[3:0] == 4'd0) ? 32'd0 : r[raddr_a_i];
    rdata_b_o <= (raddr_b_i[3:0] == 4'd0) ? 32'd0 : r[raddr_b_i];
  end
endmodule
