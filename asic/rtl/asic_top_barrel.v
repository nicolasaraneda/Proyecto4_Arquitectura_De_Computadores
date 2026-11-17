// asic_top_barrel.v: el macro ASIC del fondo en un chip (R1), edición de exhibición.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Copia de factibilidad/g_asic/rtl/asic_top.v (mismos puertos, mismo sincronizador
// del reset) que instancia pochoco_soc_asic_barrel. Xd elige la extensión: 3 es la
// de R1 (emad y devk) y 7 agrega mulstep.
module asic_top_barrel #(
  parameter integer Xd        = 3,    // 3: emad y devk (R1). 7: agrega mulstep
  parameter integer DataWords = 16    // palabras de datos en flip-flops
) (
  input  wire       clk,
  input  wire       rst_n,      // reset externo, activo en bajo, asíncrono

  output wire [3:0] led,
  input  wire [3:0] btn,        // interruptores, activos en alto, asíncronos

  output wire [6:0] seg1,       // dígito izquierdo, {G,F,E,D,C,B,A}, activo en bajo
  output wire [6:0] seg2,       // dígito derecho,   {G,F,E,D,C,B,A}, activo en bajo

  input  wire       spi_sclk,
  input  wire       spi_mosi,
  input  wire       spi_cs_n,
  output wire       spi_miso
);

  // Sincronizador de reset: aserción asíncrona, liberación sincrónica.
  reg [1:0] rst_sync_q;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) rst_sync_q <= 2'b00;
    else        rst_sync_q <= {rst_sync_q[0], 1'b1};
  end

  pochoco_soc_asic_barrel #(
    .Xd        (Xd),
    .DataWords (DataWords)
  ) u_soc (
    .i_Clk        (clk),
    .rst_ni       (rst_sync_q[1]),

    .o_LED        (led),
    .i_Switch     (btn),

    .o_Segment1_A (seg1[0]), .o_Segment1_B (seg1[1]),
    .o_Segment1_C (seg1[2]), .o_Segment1_D (seg1[3]),
    .o_Segment1_E (seg1[4]), .o_Segment1_F (seg1[5]),
    .o_Segment1_G (seg1[6]),
    .o_Segment2_A (seg2[0]), .o_Segment2_B (seg2[1]),
    .o_Segment2_C (seg2[2]), .o_Segment2_D (seg2[3]),
    .o_Segment2_E (seg2[4]), .o_Segment2_F (seg2[5]),
    .o_Segment2_G (seg2[6]),

    .i_SPI_SCLK   (spi_sclk),
    .i_SPI_MOSI   (spi_mosi),
    .i_SPI_CS_n   (spi_cs_n),
    .o_SPI_MISO   (spi_miso)
  );

endmodule
