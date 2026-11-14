// tb_xd_kernel.sv: ciclos e instrucciones de un kernel entre dos marcas.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Corre un programa de sw/bandas_*.s en la copia del SoC (core/). El programa
// escribe en MARCA (0x7FC) al empezar y al terminar el lazo, y en RES (0x7F8)
// el resultado de cada vuelta. El testbench cuenta los ciclos y las
// instrucciones completadas entre las dos marcas y deja los resultados en un
// archivo, uno por línea, para compararlos con el modelo
// (tools/kernel_bandas.py). Sirve para el Espino base y para el segmentado
// (-DESPINO_SEGMENTADO). Lo corre tools/medir_kernel.sh.
//
// Definiciones: PROGRAMA (hex) y RESULTADOS (archivo de salida).

`timescale 1ns/1ps

module tb_xd_kernel;
  logic clk = 0;
  always #20 clk = ~clk;

  pochoco_soc #(.MemFile(`PROGRAMA), .PorBits(4)) dut (
    .i_Clk(clk), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO());

  wire        commit = dut.u_core.u_id.commit;
  wire        d_wr   = dut.u_core.data_req_o && dut.u_core.data_we_o;
  wire [31:0] d_addr = dut.u_core.data_addr_o;
  wire [31:0] d_wd   = dut.u_core.data_wdata_o;

  int ciclo = 0, instr = 0, marcas = 0, c0, i0, n_res = 0, fd;

  initial fd = $fopen(`RESULTADOS, "w");

  always @(posedge clk) begin
    ciclo++;
    if (commit) instr++;
    if (d_wr && d_addr == 32'h0000_07F8 && marcas == 1) begin
      $fdisplay(fd, "%08x", d_wd);
      n_res++;
    end
    if (d_wr && d_addr == 32'h0000_07FC) begin
      marcas++;
      if (marcas == 1) begin
        c0 = ciclo; i0 = instr;
      end else begin
        $display("MEDIDO ciclos=%0d instrucciones=%0d resultados=%0d", ciclo - c0, instr - i0, n_res);
        $fclose(fd);
        $finish;
      end
    end
    if (ciclo > 200000) begin
      $display("FAIL tb_xd_kernel: el programa no llego a la segunda marca");
      $fatal(1);
    end
  end
endmodule
