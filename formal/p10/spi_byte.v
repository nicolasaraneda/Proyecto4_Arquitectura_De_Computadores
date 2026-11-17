// spi_byte.v: envoltorio formal del esclavo SPI (revisión P10,
// docs/revision_p10.md, hallazgo 1).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Instancia rtl/pochoco_spi_slave.v sin cambios, con todas las entradas
// libres (SCLK, MOSI, CS_n y el bus del core) y un solo reset al comienzo, y
// afirma:
//
//   1. Un precio (byte_done) solo se completa si CS_n estaba en bajo en el
//      ciclo anterior. Es lo que necesita el vigilante: fuera de una
//      transacción no llegan precios.
//   2. Mientras CS_n está en alto, MISO vale 0 (lo que ya hace el esclavo).
//
// Con el esclavo de main la afirmación 1 falla: SymbiYosys entrega el
// contraejemplo (7 flancos de SCLK con CS_n en bajo, CS_n sube, otro flanco).
// Con el arreglo de la rama p10-arreglo-1 se prueba por inducción.
//
// Se corre con tools/p10/formal_spi.sh (make p10-formal-spi).

module spi_byte (
  input wire        clk,
  input wire        sclk,
  input wire        mosi,
  input wire        cs_n,
  input wire        sel,
  input wire        req,
  input wire        we,
  input wire [7:0]  addr,
  input wire [31:0] wdata
);

  reg rst_n = 1'b0;
  always @(posedge clk) rst_n <= 1'b1;

  wire [31:0] rdata;
  wire        miso, byte_done, decision_wr, cs_activo;

  pochoco_spi_slave dut (
    .clk_i (clk), .rst_ni (rst_n),
    .sel_i (sel), .req_i (req), .we_i (we), .addr_i (addr), .wdata_i (wdata), .rdata_o (rdata),
    .spi_sclk_i (sclk), .spi_mosi_i (mosi), .spi_cs_n_i (cs_n), .spi_miso_o (miso),
    .byte_done_o (byte_done), .decision_wr_o (decision_wr), .cs_active_o (cs_activo)
  );

  reg pasado = 1'b0;
  reg cs_activo_ant = 1'b0;
  always @(posedge clk) begin
    pasado        <= rst_n;
    cs_activo_ant <= cs_activo;
  end

  always @(*) begin
    if (pasado) begin
      assert (!byte_done || cs_activo_ant);
      assert (cs_activo || !miso);
    end
  end

  // Alcanzable: un precio normal dentro de una transacción
  always @(*) if (pasado) cover (byte_done && cs_activo);

  wire _unused = &{1'b0, rdata, decision_wr};

endmodule
