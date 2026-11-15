// espino_barrel_regfile.v: banco de registros con cuatro contextos en BRAM.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Es el banco del Espino (rtl/espino_core/espino_register_file.v, dos copias
// de 32 bits, una por puerto de lectura, cada una en dos SB_RAM40_4K de 256
// palabras de 16 bits) con la dirección ampliada de 4 a 6 bits: {hilo,
// registro}. Los cuatro contextos ocupan 64 de las 256 palabras que ya
// tenían esos bloques, así que no cuesta BRAM adicionales.
//
// No hay adelantamiento. La lectura la hace la instrucción que está en la
// etapa R y la escritura la que está en M, que son de hilos distintos: nunca
// se lee y se escribe la misma dirección en el mismo flanco.
//
// x0 de cada contexto vale 0 porque es el contenido inicial de la BRAM y el
// core nunca habilita una escritura con registro destino 0.

module espino_barrel_regbank32 (
  input  wire        clk_i,
  input  wire [5:0]  raddr_i,
  output wire [31:0] rdata_o,
  input  wire [5:0]  waddr_i,
  input  wire [31:0] wdata_i,
  input  wire        we_i
);
  wire [10:0] ra = {5'b0, raddr_i};
  wire [10:0] wa = {5'b0, waddr_i};

  SB_RAM40_4K #(
    .READ_MODE(0), .WRITE_MODE(0),
    .INIT_0(256'h0), .INIT_1(256'h0), .INIT_2(256'h0), .INIT_3(256'h0)
  ) u_lo (
    .RDATA (rdata_o[15:0]),
    .RADDR (ra), .RCLK (clk_i), .RCLKE (1'b1), .RE (1'b1),
    .WDATA (wdata_i[15:0]),
    .WADDR (wa), .WCLK (clk_i), .WCLKE (1'b1), .WE (we_i),
    .MASK  (16'h0000)
  );

  SB_RAM40_4K #(
    .READ_MODE(0), .WRITE_MODE(0),
    .INIT_0(256'h0), .INIT_1(256'h0), .INIT_2(256'h0), .INIT_3(256'h0)
  ) u_hi (
    .RDATA (rdata_o[31:16]),
    .RADDR (ra), .RCLK (clk_i), .RCLKE (1'b1), .RE (1'b1),
    .WDATA (wdata_i[31:16]),
    .WADDR (wa), .WCLK (clk_i), .WCLKE (1'b1), .WE (we_i),
    .MASK  (16'h0000)
  );
endmodule

module espino_barrel_regfile (
  input  wire        clk_i,
  input  wire [5:0]  raddr_a_i,    // {hilo, rs1}
  output wire [31:0] rdata_a_o,
  input  wire [5:0]  raddr_b_i,    // {hilo, rs2}
  output wire [31:0] rdata_b_o,
  input  wire [5:0]  waddr_i,      // {hilo, rd}
  input  wire [31:0] wdata_i,
  input  wire        we_i
);
  espino_barrel_regbank32 u_bankA (   // puerto de lectura A
    .clk_i (clk_i),
    .raddr_i (raddr_a_i), .rdata_o (rdata_a_o),
    .waddr_i (waddr_i), .wdata_i (wdata_i), .we_i (we_i)
  );

  espino_barrel_regbank32 u_bankB (   // puerto de lectura B
    .clk_i (clk_i),
    .raddr_i (raddr_b_i), .rdata_o (rdata_b_o),
    .waddr_i (waddr_i), .wdata_i (wdata_i), .we_i (we_i)
  );
endmodule
