// tb_registrador.sv: testbench de rtl/registrador/registrador.v.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Una maestra SPI de modo 0 con los tiempos del testbench oficial (configurables)
// manda precios de tb/practica.csv al registrador. Un receptor UART a 1 Mbaud lee lo
// que sale por o_UART_TX, arma los registros de 5 bytes y los compara con lo enviado:
// un registro por transacción, en orden, con el precio, MISO = 0x00, la marca de error
// y el período entre transacciones. Entre caso y caso se aprieta SW3 (borra la cuenta y
// la secuencia). Todos los bytes recibidos quedan en +BYTES=archivo, para probar
// tools/registrador.py con lo mismo que saldría por el cable.
//
// Casos:
//   1. 0,1 ms (ronda 3), 2000 precios, SCLK 1 MHz: ninguno perdido.
//   2. 1 ms (ronda 2), 200 precios, SCLK 100 kHz.
//   3. 10 ms (ronda 1), 12 precios: el período queda en 1953 unidades.
//   4. 0,1 ms, 100 precios, con una transacción de 7 bits: ese registro con error.
//   5. 60 us, 1000 precios: más rápido que la ronda 3, ninguno perdido.
//   6. Control: 30 us, 200 precios. La UART no alcanza (50 us por registro): se
//      tienen que perder registros, la secuencia lo tiene que mostrar y LED4 encenderse.
//
// Con -DCHIP corre sobre el bitstream ruteado (tools/registrador.sh, paso 5).
// Uso: tools/registrador.sh   (iverilog -g2012)
`timescale 1ns/1ps
module tb_registrador;
  reg        clk = 1'b0;
  reg [3:0]  sw = 4'b0000;
  reg        sclk = 1'b0, mosi = 1'b0, cs_n = 1'b1;
  wire [3:0] led;
  wire       a1, b1, c1, d1, e1, f1, g1, a2, b2, c2, d2, e2, f2, g2;
  wire       miso, tx;
  always #20 clk = ~clk;                 // 25 MHz
`ifdef CHIP
  chip dut (
    .i_Clk(clk), .\i_Switch (sw), .\o_LED (led),
    .i_UART_RX(1'b1), .o_UART_TX(tx),
    .o_Segment1_A(a1), .o_Segment1_B(b1), .o_Segment1_C(c1), .o_Segment1_D(d1),
    .o_Segment1_E(e1), .o_Segment1_F(f1), .o_Segment1_G(g1),
    .o_Segment2_A(a2), .o_Segment2_B(b2), .o_Segment2_C(c2), .o_Segment2_D(d2),
    .o_Segment2_E(e2), .o_Segment2_F(f2), .o_Segment2_G(g2),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));
`else
  registrador_top #(.REBOTE(8)) dut (
    .i_Clk(clk), .i_Switch(sw), .o_LED(led),
    .o_Segment1_A(a1), .o_Segment1_B(b1), .o_Segment1_C(c1), .o_Segment1_D(d1),
    .o_Segment1_E(e1), .o_Segment1_F(f1), .o_Segment1_G(g1),
    .o_Segment2_A(a2), .o_Segment2_B(b2), .o_Segment2_C(c2), .o_Segment2_D(d2),
    .o_Segment2_E(e2), .o_Segment2_F(f2), .o_Segment2_G(g2),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso),
    .i_UART_RX(1'b1), .o_UART_TX(tx));
`endif

  integer fallas = 0, pruebas = 0;
  task automatic comprobar(input bit ok, input string texto);
    pruebas++;
    if (ok) $display("PASS %s", texto);
    else begin fallas++; $display("FAIL %s", texto); end
  endtask

  // --- La serie ---------------------------------------------------------------------
  int precio[0:19999];
  string linea_cabecera;
  initial begin
    int fd, r, t;
    fd = $fopen("tb/practica.csv", "r");
    r = $fgets(linea_cabecera, fd);
    for (int n = 0; n < 20000; n++) r = $fscanf(fd, "%d,%d\n", t, precio[n]);
    $fclose(fd);
  end

  // --- Receptor UART a 1 Mbaud ---------------------------------------------------------
  byte unsigned rx_q[$];
  integer fbytes = 0;
  bit guardar = 1'b0;                     // solo el caso 1 va al archivo de +BYTES
  initial begin
    string ruta;
    if ($value$plusargs("BYTES=%s", ruta)) fbytes = $fopen(ruta, "wb");
  end
  initial begin : receptor
    byte unsigned b;
    forever begin
      @(negedge tx);
      #1500;
      for (int i = 0; i < 8; i++) begin b[i] = tx; #1000; end
      if (tx !== 1'b1) $display("FAIL UART: falta el bit de parada");
      rx_q.push_back(b);
      if (fbytes && guardar) $fwrite(fbytes, "%c", b);
    end
  end

  // --- Maestra SPI ---------------------------------------------------------------------
  task automatic transaccion(input [7:0] dato, input int setup_ns, input int medio_ns, input int hold_ns, input int nbits);
    cs_n = 1'b0;
    #(setup_ns);
    for (int i = 7; i > 7 - nbits; i--) begin
      mosi = dato[i];
      #(medio_ns) sclk = 1'b1;
      #(medio_ns) sclk = 1'b0;
    end
    #(hold_ns) cs_n = 1'b1;
  endtask

  // --- Registros recibidos ---------------------------------------------------------------
  // Un registro por índice, en cinco colas paralelas (Icarus no admite colas de estructuras)
  int r_sec[$], r_pre[$], r_mis[$], r_err[$], r_dt[$];
  int basura = 0;
  task automatic armar_registros();
    int i = 0;
    byte unsigned b0, b1, b2, b3, b4;
    r_sec.delete(); r_pre.delete(); r_mis.delete(); r_err.delete(); r_dt.delete();
    basura = 0;
    while (i + 5 <= rx_q.size()) begin
      b0 = rx_q[i]; b1 = rx_q[i+1]; b2 = rx_q[i+2]; b3 = rx_q[i+3]; b4 = rx_q[i+4];
      if (!b0[7] || b1[7] || b2[7] || b3[7] || b4[7]) begin basura++; i++; continue; end
      r_sec.push_back(b0[6:0]);
      r_pre.push_back({b1[6:0], b3[6]});
      r_mis.push_back({b2[6:0], b3[5]});
      r_err.push_back(b3[4]);
      r_dt.push_back({b3[3:0], b4[6:0]});
      i += 5;
    end
    basura += rx_q.size() - i;
  endtask

  task automatic borrar();
    sw[2] = 1'b1; repeat (40) @(posedge clk); sw[2] = 1'b0; repeat (40) @(posedge clk);
  endtask

  // Corre un caso: n precios desde el índice ini, período per_ns. corto: índice de una
  // transacción de 7 bits (-1 ninguna). perdida_esperada: el caso de control.
  task automatic caso(input string nombre, input int ini, input int n, input int per_ns, input int medio_ns,
                      input int corto, input bit perdida_esperada);
    int esperado_dt, malos, saltos, ultimo, dt_malos;
    longint t0;
    borrar();
    rx_q.delete();
    guardar = (ini == 0);
    for (int k = 0; k < n; k++) begin
      t0 = $time;
      transaccion(precio[ini + k][7:0], 1000, medio_ns, 500, k == corto ? 7 : 8);
      #(per_ns - ($time - t0));
    end
    #(per_ns + 400000);                  // que salga lo que quedó en la cola
    armar_registros();
    esperado_dt = (per_ns / 40) >> 7;
    if (esperado_dt > 2047) esperado_dt = 2047;
    if (!perdida_esperada) begin
      malos = 0; dt_malos = 0;
      for (int k = 0; k < r_sec.size() && k < n; k++) begin
        if (r_sec[k] != (k & 127) || (k != corto && r_pre[k] != precio[ini + k]) ||
            r_mis[k] != 0 || r_err[k] != (k == corto))
          malos++;
        if (k > 0 && r_dt[k] != esperado_dt) dt_malos++;
        if (k == 0 && r_dt[k] != 2047) dt_malos++;
      end
      comprobar(r_sec.size() == n, $sformatf("%s: %0d registros de %0d precios", nombre, r_sec.size(), n));
      comprobar(basura == 0, $sformatf("%s: %0d bytes fuera de un registro", nombre, basura));
      comprobar(malos == 0, $sformatf("%s: secuencia, precio, MISO y marca de error iguales a lo enviado (%0d distintos)", nombre, malos));
      comprobar(dt_malos == 0, $sformatf("%s: periodo de %0d unidades de 5,12 us en todos (%0d distintos)", nombre, esperado_dt, dt_malos));
      comprobar(led[3] == 1'b0, $sformatf("%s: LED4 (registro perdido) apagado", nombre));
      if (corto >= 0) comprobar(led[2] == 1'b1, $sformatf("%s: LED3 (transaccion con error) encendido", nombre));
      else comprobar(led[2] == 1'b0, $sformatf("%s: LED3 (transaccion con error) apagado", nombre));
    end else begin
      // Control: tiene que faltar algún registro, y la secuencia lo tiene que mostrar.
      saltos = 0; malos = 0; ultimo = -1;
      for (int k = 0; k < r_sec.size(); k++) begin
        if (ultimo >= 0 && r_sec[k] != ((ultimo + 1) & 127)) saltos++;
        ultimo = r_sec[k];
      end
      // Los que llegaron tienen que estar enteros: con la secuencia se reconstruye a qué
      // transacción corresponde cada uno y su precio tiene que ser el enviado.
      begin
        int idx = 0, corruptos = 0;
        for (int k = 0; k < r_sec.size(); k++) begin
          if (k > 0) idx += (r_sec[k] - r_sec[k-1]) & 127;
          if (idx >= n || r_pre[k] != precio[ini + idx]) corruptos++;
        end
        comprobar(corruptos == 0, $sformatf("%s: los %0d registros que llegaron tienen el precio de su transaccion (%0d distintos)",
                                            nombre, r_sec.size(), corruptos));
      end
      comprobar(r_sec.size() < n, $sformatf("%s: se perdieron registros (%0d de %0d)", nombre, n - r_sec.size(), n));
      comprobar(saltos > 0, $sformatf("%s: la secuencia salta %0d veces", nombre, saltos));
      comprobar(led[3] == 1'b1, $sformatf("%s: LED4 (registro perdido) encendido", nombre));
    end
  endtask

  initial begin
    #2000;
    if ($test$plusargs("RAPIDO")) begin  // para el bitstream ruteado (paso 5 de tools/registrador.sh)
      caso("ronda 3 (0,1 ms, SCLK 1 MHz)", 0, 300, 100000, 500, -1, 0);
      caso("ronda 2 (1 ms, SCLK 100 kHz)", 5000, 20, 1000000, 5000, -1, 0);
      caso("0,1 ms con una transaccion de 7 bits", 12000, 50, 100000, 500, 17, 0);
      caso("60 us", 13000, 200, 60000, 500, -1, 0);
      caso("control: 30 us", 15000, 100, 30000, 500, -1, 1);
    end else begin
      caso("ronda 3 (0,1 ms, SCLK 1 MHz)", 0, 2000, 100000, 500, -1, 0);
      caso("ronda 2 (1 ms, SCLK 100 kHz)", 5000, 200, 1000000, 5000, -1, 0);
      caso("ronda 1 (10 ms)", 9000, 12, 10000000, 500, -1, 0);
      caso("0,1 ms con una transaccion de 7 bits", 12000, 100, 100000, 500, 37, 0);
      caso("60 us", 13000, 1000, 60000, 500, -1, 0);
      caso("control: 30 us", 15000, 200, 30000, 500, -1, 1);
    end
    if (fbytes) $fclose(fbytes);
    $display("RESUMEN: %0d comprobaciones, %0d fallas", pruebas, fallas);
    if (fallas == 0) $display("PASS: registrador");
    $finish;
  end
endmodule
