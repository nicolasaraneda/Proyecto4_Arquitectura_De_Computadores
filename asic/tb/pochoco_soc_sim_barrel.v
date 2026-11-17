// pochoco_soc_sim_barrel.v: el macro ASIC del barrel con la cara de pochoco_soc, para
// correr una copia del testbench oficial sobre el RTL del macro y sobre su netlist.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Copia de factibilidad/g_asic/tb/pochoco_soc_sim.v con asic_top_barrel. Genera el
// reset con el mismo contador de la FPGA y expone u_spi con los nombres que el
// testbench busca por jerarquía. ASIC_XD elige la extensión (3 por defecto).
`ifndef ASIC_XD
  `define ASIC_XD 3
`endif

module pochoco_soc #(
  parameter MemFile  = "",
  parameter PorBits  = 12,
  parameter Xd       = `ASIC_XD
) (
  input  wire       i_Clk,

  output wire [3:0] o_LED,
  input  wire [3:0] i_Switch,

  output wire       o_Segment1_A, o_Segment1_B, o_Segment1_C, o_Segment1_D,
  output wire       o_Segment1_E, o_Segment1_F, o_Segment1_G,
  output wire       o_Segment2_A, o_Segment2_B, o_Segment2_C, o_Segment2_D,
  output wire       o_Segment2_E, o_Segment2_F, o_Segment2_G,

  input  wire       i_SPI_SCLK,
  input  wire       i_SPI_MOSI,
  input  wire       i_SPI_CS_n,
  output wire       o_SPI_MISO
);

  // Power-on reset de la placa, solo para la simulación
  reg [PorBits-1:0] por_cnt = {PorBits{1'b0}};
  always @(posedge i_Clk) begin
    if (~&por_cnt) por_cnt <= por_cnt + 1'b1;
  end
  wire rst_n = &por_cnt;

  wire [6:0] seg1, seg2;

  asic_top_barrel #(.Xd(Xd)) u_asic (
    .clk      (i_Clk),
    .rst_n    (rst_n),
    .led      (o_LED),
    .btn      (i_Switch),
    .seg1     (seg1),
    .seg2     (seg2),
    .spi_sclk (i_SPI_SCLK),
    .spi_mosi (i_SPI_MOSI),
    .spi_cs_n (i_SPI_CS_n),
    .spi_miso (o_SPI_MISO)
  );

  assign {o_Segment1_G, o_Segment1_F, o_Segment1_E, o_Segment1_D,
          o_Segment1_C, o_Segment1_B, o_Segment1_A} = seg1;
  assign {o_Segment2_G, o_Segment2_F, o_Segment2_E, o_Segment2_D,
          o_Segment2_C, o_Segment2_B, o_Segment2_A} = seg2;

  // Las cuatro señales que el testbench oficial mira por jerarquía
  generate
    if (1) begin : u_spi
      wire       byte_done   = u_asic.u_soc.u_spi.byte_done;
      wire       new_price_q = u_asic.u_soc.u_spi.new_price_q;
      wire       wr          = u_asic.u_soc.u_spi.wr;
      wire [5:0] off         = u_asic.u_soc.u_spi.off;
    end
  endgenerate

  wire _unused = &{1'b0, MemFile[0]};

endmodule
