// tabla_mmio.v: memoria para la tabla de política, forma 1. Una BRAM de 256
// palabras de 16 bits que el core lee y escribe por MMIO.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Es memoria y nada más: no calcula, no mira precios y no decide. El programa
// la usa como una tabla que él mismo consulta y ajusta. En el SoC queda en
// 0x8002_0000 y la palabra i está en el desplazamiento 4 i:
//
//   lw  / lhu   lee la palabra con ceros en los 16 bits altos
//   lh          lee la palabra con extensión de signo
//   sw  / sh    escribe los 16 bits bajos del registro
//   sb          escribe el byte bajo (desplazamiento 4 i) o el alto (4 i + 1)
//
// La lectura es registrada, como la de la memoria y la de los periféricos: el
// dato se pide en la etapa X y llega en la etapa M. Ocupa una SB_RAM40_4K en
// su modo nativo de 256 x 16, con la máscara de escritura por bit haciendo de
// habilitación por byte.
//
// Un acceso es una lectura o una escritura, nunca las dos: la lectura solo se
// habilita cuando we_i vale 0. Por eso el arreglo lleva (* no_rw_check *), que
// le dice a Yosys que no agregue la lógica con que emula "leer el dato viejo"
// cuando se lee y se escribe la misma palabra en el mismo flanco. Aquí ese
// caso no existe.
//
// MemFile es el contenido inicial, un valor hexadecimal de 16 bits por línea.
// Vacío, la tabla parte en cero.

module tabla_mmio #(
  parameter MemFile = ""
) (
  input  wire        clk_i,
  input  wire        req_i,      // acceso a la tabla en este ciclo
  input  wire        we_i,       // 1 escribe, 0 lee
  input  wire [1:0]  be_i,       // bytes que se escriben
  input  wire [7:0]  idx_i,      // palabra
  input  wire [15:0] wdata_i,
  output reg  [15:0] rdata_o
);

  (* no_rw_check *) reg [15:0] mem [0:255];

  integer i;
  initial begin
    for (i = 0; i < 256; i = i + 1) mem[i] = 16'b0;
    if (MemFile != "") $readmemh(MemFile, mem);
  end

  always @(posedge clk_i) begin
    if (req_i & we_i) begin
      if (be_i[0]) mem[idx_i][7:0]  <= wdata_i[7:0];
      if (be_i[1]) mem[idx_i][15:8] <= wdata_i[15:8];
    end
    if (req_i & ~we_i) rdata_o <= mem[idx_i];
  end

endmodule
