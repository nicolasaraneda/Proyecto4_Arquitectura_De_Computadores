// tabla_ram.v: memoria para la tabla de política, forma 2. Otras NumWords
// palabras de 32 bits de memoria de datos.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Con esta memoria el SoC tiene 1024 palabras: las 512 de pochoco_ram
// (programa y datos, direcciones 0x000 a 0x7FF) y estas 512 (direcciones
// 0x800 a 0xFFF), que son solo de datos. No tiene puerto de instrucciones: el
// contador de programa sigue teniendo 11 bits y lo que hay aquí no se puede
// ejecutar. Por eso cuesta 4 BRAM y no 8: pochoco_ram necesita dos copias de
// cada palabra para leer la instrucción y el dato en el mismo ciclo, y esta
// no. Con las 12 BRAM del SoC son las 16 de la FPGA.
//
// Es memoria y nada más. Se accede igual que la de datos: lw, lh, lb, sw, sh
// y sb, con habilitación por byte, y la lectura llega registrada en la etapa
// M.
//
// Un acceso es una lectura o una escritura, nunca las dos: la lectura solo se
// habilita cuando we_i vale 0. Por eso el arreglo lleva (* no_rw_check *) y
// Yosys no agrega la lógica con que emula "leer el dato viejo" en pochoco_ram
// (factibilidad/a_barrel/README.md, sección 7).
//
// MemFile es el contenido inicial, una palabra hexadecimal de 32 bits por
// línea. Vacío, parte en cero.

module tabla_ram #(
  parameter NumWords = 512,
  parameter MemFile  = ""
) (
  input  wire                        clk_i,
  input  wire                        req_i,      // acceso a esta memoria en este ciclo
  input  wire                        we_i,       // 1 escribe, 0 lee
  input  wire [3:0]                  be_i,       // bytes que se escriben
  input  wire [$clog2(NumWords)-1:0] idx_i,      // palabra
  input  wire [31:0]                 wdata_i,
  output reg  [31:0]                 rdata_o
);

  (* no_rw_check *) reg [31:0] mem [0:NumWords-1];

  integer i;
  initial begin
    for (i = 0; i < NumWords; i = i + 1) mem[i] = 32'b0;
    if (MemFile != "") $readmemh(MemFile, mem);
  end

  always @(posedge clk_i) begin
    if (req_i & we_i) begin
      if (be_i[0]) mem[idx_i][7:0]   <= wdata_i[7:0];
      if (be_i[1]) mem[idx_i][15:8]  <= wdata_i[15:8];
      if (be_i[2]) mem[idx_i][23:16] <= wdata_i[23:16];
      if (be_i[3]) mem[idx_i][31:24] <= wdata_i[31:24];
    end
    if (req_i & ~we_i) rdata_o <= mem[idx_i];
  end

endmodule
