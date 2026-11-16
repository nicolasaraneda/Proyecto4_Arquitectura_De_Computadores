// tb_xd_barrel.sv: las instrucciones nuevas ejecutadas por los cuatro hilos
// del barrel, dentro del SoC integrado.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Es tb/tb_xd_core.sv de factibilidad/d_isa llevado a cuatro hilos. Corre un
// programa generado por tools/gen_prog_hilos.py y compara, en orden y por
// hilo, cada escritura al banco de registros con la lista que predice el
// modelo ref/xd.py de d_isa para ese hilo. El hilo de cada escritura es el
// que el core dice que está en la etapa M. Exige además que ningún hilo
// escriba de más: después de la última escritura esperada el programa queda en
// un lazo vacío y se siguen mirando 200 ciclos.
//
// Sirve para cualquier combinación de las definiciones XD_*, I_VIGILANTE e
// I_TABLA. Se compila una vez por variante y el programa se elige al correr:
//   vvp sim +hex=p.hex +esp=p +n0=N0 +n1=N1 +n2=N2 +n3=N3
// (tools/tb_xd.sh).

`timescale 1ns/1ps

module tb_xd_barrel;
  localparam int MAXN = 512;

  logic clk = 0;
  always #20 clk = ~clk;

  pochoco_soc #(.MemFile(""), .PorBits(4)) dut (
    .i_Clk(clk), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO());

  logic [35:0] esp0 [0:MAXN-1], esp1 [0:MAXN-1], esp2 [0:MAXN-1], esp3 [0:MAXN-1];
  int          n [4], i [4];
  int          errores = 0, ciclos = 0, cola = 0;
  int          na = 0, nb = 0, nc = 0, nd = 0;
  string       hex, pref;

  function automatic logic [35:0] esperado(input int t, input int k);
    case (t)
      0:       return esp0[k];
      1:       return esp1[k];
      2:       return esp2[k];
      default: return esp3[k];
    endcase
  endfunction

  initial begin
    if (!$value$plusargs("hex=%s", hex) || !$value$plusargs("esp=%s", pref)) begin
      $display("faltan +hex=ARCHIVO y +esp=PREFIJO"); $fatal(1);
    end
    for (int t = 0; t < 4; t++) begin n[t] = 0; i[t] = 0; end
    void'($value$plusargs("n0=%d", na));
    void'($value$plusargs("n1=%d", nb));
    void'($value$plusargs("n2=%d", nc));
    void'($value$plusargs("n3=%d", nd));
    n[0] = na; n[1] = nb; n[2] = nc; n[3] = nd;
    $readmemh(hex, dut.u_ram.mem);
    if (n[0] > 0) $readmemh({pref, ".h0.esp"}, esp0, 0, n[0] - 1);
    if (n[1] > 0) $readmemh({pref, ".h1.esp"}, esp1, 0, n[1] - 1);
    if (n[2] > 0) $readmemh({pref, ".h2.esp"}, esp2, 0, n[2] - 1);
    if (n[3] > 0) $readmemh({pref, ".h3.esp"}, esp3, 0, n[3] - 1);
  end

  wire        rf_we = dut.u_core.tb_rf_we;
  wire [1:0]  rf_t  = dut.u_core.tb_tid_m;
  wire [3:0]  rf_wa = dut.u_core.tb_rf_wa;
  wire [31:0] rf_wd = dut.u_core.tb_rf_wd;

  wire todos = (i[0] == n[0]) && (i[1] == n[1]) && (i[2] == n[2]) && (i[3] == n[3]);

  int          th;
  logic [35:0] e;
  always @(posedge clk) begin
    ciclos++;
    if (rf_we === 1'b1) begin
      th = int'(rf_t);
      if (i[th] >= n[th]) begin
        errores++;
        if (errores <= 10)
          $display("  el hilo %0d escribe de mas: x%0d = %08x", th, rf_wa, rf_wd);
      end else begin
        e = esperado(th, i[th]);
        if ({rf_wa, rf_wd} !== e) begin
          errores++;
          if (errores <= 10)
            $display("  diferencia en el hilo %0d, escritura %0d: x%0d = %08x, esperado x%0d = %08x",
                     th, i[th], rf_wa, rf_wd, e[35:32], e[31:0]);
        end
        i[th]++;
      end
    end else if (rf_we !== 1'b0 && dut.rst_ni === 1'b1) begin
      errores++;
      if (errores <= 10) $display("  la habilitacion de escritura del banco vale X en el ciclo %0d", ciclos);
    end
    if (todos) cola++;
    if (cola > 200 || ciclos > 8 * MAXN + 4000) begin
      if (errores == 0 && todos)
        $display("PASS tb_xd_barrel: %0d %0d %0d %0d escrituras identicas al modelo en los hilos 0 a 3", i[0], i[1], i[2], i[3]);
      else begin
        $display("FAIL tb_xd_barrel: %0d diferencias; escrituras %0d de %0d, %0d de %0d, %0d de %0d, %0d de %0d",
                 errores, i[0], n[0], i[1], n[1], i[2], n[2], i[3], n[3]);
        $fatal(1);
      end
      $finish;
    end
  end
endmodule
