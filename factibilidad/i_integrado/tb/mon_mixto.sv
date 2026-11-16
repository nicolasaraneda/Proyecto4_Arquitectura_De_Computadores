// mon_mixto.sv: monitor de los hilos de estrategia para el testbench oficial.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// El testbench oficial no se modifica. Este módulo se compila junto a él como
// otro módulo raíz (iverilog -s tb_proyecto_4 -s mon_mixto), igual que
// tb/mon_vigilante.sv de factibilidad/e_warmboot, y mira por jerarquía el bus
// de datos del core.
//
// En la prueba mixta (tools/mixto.sh) el hilo 0 corre la regla base y atiende
// a la maestra del testbench oficial, y los hilos 1, 2 y 3 corren
// sw/kernel_media.s o sw/kernel_carriles.s: en cada vuelta publican una suma
// S en KRES + 8 (t - 1) y el número de vuelta n en la palabra siguiente. El
// monitor toma cada pareja (S, n) del bus y exige que n avance de a uno y que
// S sea la que predice tools/modelo_kernel.py (archivo PREFIJO.hT.esp, la
// vuelta n en la línea n).
//
// El testbench oficial termina con $finish, así que el resumen se escribe en
// un archivo cada 1024 vueltas del hilo 1 y en cada error.
//
// Definiciones: ESP_PREFIJO (prefijo de los tres archivos), VUELTAS_MAX
// (líneas de cada archivo) y SALIDA_MIXTO (archivo de resumen).

`timescale 1ns/1ps

`ifndef SALIDA_MIXTO
  `define SALIDA_MIXTO "mon_mixto.txt"
`endif
`ifndef VUELTAS_MAX
  `define VUELTAS_MAX 200000
`endif

module mon_mixto;
  localparam int KRES = 'h6C0;
  localparam int MAXV = `VUELTAS_MAX;

  logic [31:0] esp1 [0:MAXV-1], esp2 [0:MAXV-1], esp3 [0:MAXV-1];
  logic [31:0] s_ult [1:3];
  int          n_ult [1:3];
  int          vueltas [1:3];
  int          errores = 0, fd, t;
  logic [31:0] e, dir;

  initial begin
    $readmemh({`ESP_PREFIJO, ".h1.esp"}, esp1);
    $readmemh({`ESP_PREFIJO, ".h2.esp"}, esp2);
    $readmemh({`ESP_PREFIJO, ".h3.esp"}, esp3);
    for (int k = 1; k <= 3; k++) begin n_ult[k] = 0; vueltas[k] = 0; s_ult[k] = 32'hx; end
  end

  task automatic resumen;
    fd = $fopen(`SALIDA_MIXTO, "w");
    $fdisplay(fd, "vueltas_h1=%0d vueltas_h2=%0d vueltas_h3=%0d errores=%0d", vueltas[1], vueltas[2], vueltas[3], errores);
    $fclose(fd);
  endtask

  always @(posedge tb_proyecto_4.clk) begin
    if (tb_proyecto_4.dut.u_core.data_req_o === 1'b1 && tb_proyecto_4.dut.u_core.data_we_o === 1'b1) begin
      dir = tb_proyecto_4.dut.u_core.data_addr_o;
      if (dir >= KRES && dir < KRES + 24) begin
        t = (dir - KRES) / 8 + 1;
        if (dir[2] == 1'b0) begin
          s_ult[t] = tb_proyecto_4.dut.u_core.data_wdata_o;        // la suma S
        end else begin                                             // el número de vuelta n
          n_ult[t] = n_ult[t] + 1;
          case (t)
            1:       e = esp1[n_ult[t] - 1];
            2:       e = esp2[n_ult[t] - 1];
            default: e = esp3[n_ult[t] - 1];
          endcase
          if (n_ult[t] > MAXV) begin
            // más vueltas que las del archivo: no se comparan
          end else if (tb_proyecto_4.dut.u_core.data_wdata_o !== n_ult[t] || s_ult[t] !== e) begin
            errores++;
            if (errores <= 10)
              $display("mon_mixto: hilo %0d, vuelta %0d: n = %0d, S = %08x, esperado S = %08x",
                       t, n_ult[t], tb_proyecto_4.dut.u_core.data_wdata_o, s_ult[t], e);
            resumen();
          end else begin
            vueltas[t]++;
          end
          if (t == 1 && (n_ult[t] % 1024) == 0) resumen();
        end
      end
    end
  end
endmodule
