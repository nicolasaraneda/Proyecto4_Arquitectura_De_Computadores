// tb_xd_core.sv: las instrucciones nuevas ejecutadas por el core, dentro del SoC.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Corre un programa generado por tools/gen_prog.py en la copia del SoC
// (factibilidad/d_isa/core) y compara, en orden, cada escritura al banco de
// registros con la lista que predice el modelo ref/xd.py. Sirve para el
// Espino base y para el segmentado (-DESPINO_SEGMENTADO), y para cualquier
// combinación de las definiciones XD_*. Se corre con `make tb-core` desde
// factibilidad/d_isa.
//
// Definiciones: PROGRAMA (hex), ESPERADO (una línea por escritura: un dígito
// con el registro y ocho con el valor) y N_ESP (cuántas escrituras).

`timescale 1ns/1ps

module tb_xd_core;
  logic clk = 0;
  always #20 clk = ~clk;

  pochoco_soc #(.MemFile(`PROGRAMA), .PorBits(4)) dut (
    .i_Clk(clk), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO());

  logic [35:0] esperado [0:`N_ESP];
  int          i = 0, errores = 0, ciclos = 0;

  initial $readmemh(`ESPERADO, esperado, 0, `N_ESP - 1);

  wire        rf_we = dut.u_core.rf_we;
  wire [3:0]  rf_wa = dut.u_core.rf_waddr;
  wire [31:0] rf_wd = dut.u_core.rf_wdata;

  always @(posedge clk) begin
    ciclos++;
    if (rf_we && rf_wa != 0 && i < `N_ESP) begin
      if ({rf_wa, rf_wd} !== esperado[i]) begin
        errores++;
        if (errores <= 10)
          $display("  diferencia en la escritura %0d (pc %08x): x%0d = %08x, esperado x%0d = %08x",
                   i, dut.u_core.pc_id, rf_wa, rf_wd, esperado[i][35:32], esperado[i][31:0]);
      end
      i++;
    end
    if (i == `N_ESP || ciclos > 20 * `N_ESP + 2000) begin
      if (errores == 0 && i == `N_ESP)
        $display("PASS tb_xd_core: %0d escrituras identicas al modelo", i);
      else begin
        $display("FAIL tb_xd_core: %0d diferencias, %0d escrituras de %0d", errores, i, `N_ESP);
        $fatal(1);
      end
      $finish;
    end
  end
endmodule
