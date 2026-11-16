// pochoco_tabla.v: tabla de parámetros de solo lectura para el programa.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Una BRAM de 256 palabras de 16 bits que el core solo puede leer. Es memoria
// y nada más: no calcula, no mira precios y no decide. Guarda las constantes
// del algoritmo de sw/fondo.s (umbrales, pesos, ventana y plazo), para poder
// cambiarlas en un bitstream ya construido con icebram, sin sintetizar ni
// ensamblar de nuevo (docs/tabla_vigilante.md).
//
// En el SoC queda en 0x8002_0000 y la palabra i está en el desplazamiento 4 i.
// Se lee con lw: la palabra de 16 bits llega con extensión de signo a 32, así
// que un umbral negativo se guarda en 16 bits y se usa tal cual. La lectura es
// registrada, como la de la memoria de datos y la de los periféricos: se pide
// en la etapa de ejecución y llega en el ciclo siguiente.
//
// No tiene puerto de escritura. Un store a esta dirección no hace nada, y el
// programa no tiene cómo cambiar su contenido.
//
// MemFile es el contenido, un valor hexadecimal de 16 bits por línea. Tiene
// que traer las 256 líneas. Lo genera ref/fondo.py --tabla-hex.

module pochoco_tabla #(
  parameter MemFile = ""
) (
  input  wire        clk_i,
  input  wire        rd_i,       // lectura de la tabla en este ciclo
  input  wire [7:0]  idx_i,      // palabra
  output wire [31:0] rdata_o
);

  reg [15:0] mem [0:255];
  reg [15:0] q;

  // Solo el $readmemh, igual que en pochoco_ram. Con un lazo que primero deja
  // la memoria en cero, Yosys se queda con los ceros y descarta el archivo: la
  // BRAM sale vacía en el bitstream aunque la simulación del RTL lea bien.
  initial begin
    if (MemFile != "") $readmemh(MemFile, mem);
  end

  always @(posedge clk_i) begin
    if (rd_i) q <= mem[idx_i];
  end

  assign rdata_o = {{16{q[15]}}, q};

endmodule
