// pochoco_tabla512.v: tabla de solo lectura de 512 palabras de 16 bits, para R3.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Es rtl/pochoco_tabla.v con el doble de palabras: dos BRAM en vez de una. Es
// memoria y nada más: no calcula, no mira precios y no decide. Guarda las
// constantes de sw/c1.s: los cuatro umbrales de la banda 40 en las mismas
// posiciones que en R2, el interruptor de la política y las celdas del modelo
// del paseo normalizado (ref/c1/tablas.py, docs/c1_plan.md).
//
// Solo existe en el SoC compilado con -DESPINO_TABLA_512. Sin esa definición
// el SoC usa pochoco_tabla, y R0, R1 y R2 no cambian.
//
// En el SoC queda en 0x8002_0000 y la palabra i está en el desplazamiento 4 i.
// Con lw llega la palabra de 16 bits con extensión de signo. Con lbu en 4 i
// llega su byte bajo y en 4 i + 1 su byte alto: así una celda guarda dos
// niveles. La lectura es registrada, como la de la memoria de datos.
//
// No tiene puerto de escritura. MemFile es el contenido: 512 líneas con un
// valor hexadecimal de 16 bits (tools/c1/generar.py).

module pochoco_tabla512 #(
  parameter MemFile = ""
) (
  input  wire        clk_i,
  input  wire        rd_i,       // lectura de la tabla en este ciclo
  input  wire [8:0]  idx_i,      // palabra
  output wire [31:0] rdata_o
);

  reg [15:0] mem [0:511];
  reg [15:0] q;

  // Solo el $readmemh, igual que en pochoco_tabla (docs/tabla_vigilante.md, 2.4).
  initial begin
    if (MemFile != "") $readmemh(MemFile, mem);
  end

  always @(posedge clk_i) begin
    if (rd_i) q <= mem[idx_i];
  end

  assign rdata_o = {{16{q[15]}}, q};

endmodule
