// tb_wb_demo.v: testbench de las imágenes de la prueba de placa.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Sirve para dos cosas con el mismo código:
//
//   RTL        instancia rtl/wb_demo.v con esperas cortas (parámetros chicos)
//              para que la simulación dure poco.
//   bitstream  con -DBITSTREAM instancia el módulo chip que icebox_vlog
//              reconstruye desde el .asc, con las esperas reales. Es lo mismo
//              que queda en el .bin que se graba en la placa.
//
// En los dos casos la primitiva SB_WARMBOOT se reemplaza por el modelo de
// más abajo, que solo deja mirar sus entradas. La reconfiguración misma no se
// puede simular: lo que se comprueba es que BOOT, S1 y S0 salen cuando
// corresponde y con el destino correcto.
//
// Escenarios (+escenario=N):
//   0  nadie toca nada: BOOT no sube, la letra y los LED son los de la imagen,
//      MISO en 0 y por la UART sale la letra una sola vez
//   1  SW1 apretado desde antes de arrancar: no salta (no está armado)
//   2  SW1 suelto, después apretado con rebotes: salta
//   3  SW2 mantenido: salta al cumplir 2^WLento ciclos
//   4  SW3 mantenido: salta al cumplir 2^WRapido ciclos
//   5  SW3 apretado tarde: salta apenas pasa el antirrebote
//
// Macros: IMG (0 o 1), WLENTO, WRAPIDO, WANTIRREB, y BITSTREAM.

`timescale 1ns/1ps

`ifndef IMG
  `define IMG 0
`endif
`ifndef WLENTO
  `define WLENTO 16
`endif
`ifndef WRAPIDO
  `define WRAPIDO 14
`endif
`ifndef WANTIRREB
  `define WANTIRREB 8
`endif

// Modelo de simulación de la primitiva: no hace nada, solo expone sus puertos.
module SB_WARMBOOT (input BOOT, input S1, input S0);
endmodule

module tb_wb_demo;

  localparam integer IMG       = `IMG;
  localparam integer WLENTO    = `WLENTO;
  localparam integer WRAPIDO   = `WRAPIDO;
  localparam integer WANTIRREB = `WANTIRREB;
  localparam [1:0]   DESTINO   = (IMG == 0) ? 2'b01 : 2'b00;

  reg clk = 0;
  always #20 clk = ~clk;

  reg  [3:0] sw = 4'b0000;
  wire [3:0] led;
  wire s1a, s1b, s1c, s1d, s1e, s1f, s1g;
  wire s2a, s2b, s2c, s2d, s2e, s2f, s2g;
  wire tx, miso;

`ifdef BITSTREAM
  chip dut (
    .i_Clk(clk), .\i_Switch (sw), .\o_LED (led),
    .i_UART_RX(1'b1), .o_UART_TX(tx),
    .o_Segment1_A(s1a), .o_Segment1_B(s1b), .o_Segment1_C(s1c), .o_Segment1_D(s1d),
    .o_Segment1_E(s1e), .o_Segment1_F(s1f), .o_Segment1_G(s1g),
    .o_Segment2_A(s2a), .o_Segment2_B(s2b), .o_Segment2_C(s2c), .o_Segment2_D(s2d),
    .o_Segment2_E(s2e), .o_Segment2_F(s2f), .o_Segment2_G(s2g),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO(miso));
  `define WB dut.u_warmboot
`else
  wb_demo #(.Img(IMG), .Destino(DESTINO), .WLento(WLENTO), .WRapido(WRAPIDO),
            .WAntirreb(WANTIRREB), .WSegundo(25'd20000)) dut (
    .i_Clk(clk), .i_Switch(sw), .o_LED(led),
    .o_UART_TX(tx),
    .o_Segment1_A(s1a), .o_Segment1_B(s1b), .o_Segment1_C(s1c), .o_Segment1_D(s1d),
    .o_Segment1_E(s1e), .o_Segment1_F(s1f), .o_Segment1_G(s1g),
    .o_Segment2_A(s2a), .o_Segment2_B(s2b), .o_Segment2_C(s2c), .o_Segment2_D(s2d),
    .o_Segment2_E(s2e), .o_Segment2_F(s2f), .o_Segment2_G(s2g),
    .o_SPI_MISO(miso));
  `define WB dut.u_wb
`endif

  wire boot = `WB.BOOT;
  wire [1:0] sel = {`WB.S1, `WB.S0};

  // Segmentos encendidos, en el orden {G,F,E,D,C,B,A} (los pines son activos en bajo)
  wire [6:0] seg1 = ~{s1g, s1f, s1e, s1d, s1c, s1b, s1a};
  wire [6:0] seg2 = ~{s2g, s2f, s2e, s2d, s2c, s2b, s2a};
  localparam [6:0] LETRA_SEG = (IMG == 0) ? 7'b1110111 : 7'b1111100;
  localparam [7:0] LETRA_ASC = (IMG == 0) ? 8'h41 : 8'h62;

  // Ciclos desde el arranque y ciclo en que subió BOOT
  integer ciclo = 0, ciclo_boot = -1;
  integer miso_alto = 0, sel_malo = 0, boot_bajo = 0, led_marca_mal = 0;
  always @(posedge clk) begin
    ciclo = ciclo + 1;
    // El LED 4 vale (IMG != 0) sin disparo y lo contrario con BOOT en alto
    if (led[3] !== ((IMG != 0) ^ (boot === 1'b1))) led_marca_mal = led_marca_mal + 1;
    if (miso !== 1'b0) miso_alto = miso_alto + 1;
    if (boot === 1'b1 && ciclo_boot < 0) ciclo_boot = ciclo;
    if (boot === 1'b1 && sel !== DESTINO) sel_malo = sel_malo + 1;
    if (ciclo_boot >= 0 && boot !== 1'b1) boot_bajo = boot_bajo + 1;   // BOOT no debe volver a bajar
  end

  // Receptor UART a 115200 baudios (8680 ns por bit)
  integer   uart_bytes = 0;
  reg [7:0] uart_dato  = 8'h00;
  integer   k;
  initial begin
    forever begin
      @(negedge tx);
      #(8680 + 4340);
      for (k = 0; k < 8; k = k + 1) begin uart_dato[k] = tx; #8680; end
      if (tx === 1'b1) uart_bytes = uart_bytes + 1;
    end
  end

  task esperar(input integer n);
    repeat (n) @(posedge clk);
  endtask

  integer escenario, fallas = 0;
  integer anti, lento, rapido;

  task comprobar(input cond, input [8*64-1:0] texto);
    begin
      if (cond) $display("  ok    %0s", texto);
      else begin $display("  FALLA %0s", texto); fallas = fallas + 1; end
    end
  endtask

  initial begin
    if (!$value$plusargs("escenario=%d", escenario)) escenario = 0;
    anti   = 1 << WANTIRREB;
    lento  = 1 << WLENTO;
    rapido = 1 << WRAPIDO;
    $display("imagen %0d, escenario %0d", IMG, escenario);

    case (escenario)
      0: begin
        esperar(2 * rapido + 4 * anti);
        comprobar(ciclo_boot < 0,          "BOOT no sube sin apretar nada");
        comprobar(seg1 === LETRA_SEG,      "el display izquierdo muestra la letra de la imagen");
        comprobar(led[0] === (IMG == 0) && led[3] === (IMG != 0), "LED 1 y LED 4 indican la imagen");
        comprobar(led[1] === 1'b1,         "LED 2: salto manual armado");
        comprobar(miso_alto == 0,          "MISO en 0 todo el tiempo");
        comprobar(uart_bytes == 1 && uart_dato === LETRA_ASC, "la UART envia la letra una sola vez");
        $display("  dato UART: 0x%02h, display derecho: %07b", uart_dato, seg2);
      end
      1: begin
        sw[0] = 1'b1;
        esperar(2 * rapido + 4 * anti);
        comprobar(ciclo_boot < 0,          "SW1 apretado desde el arranque no dispara");
        comprobar(led[1] === 1'b0,         "LED 2 apagado: no esta armado");
      end
      2: begin
        esperar(anti + 20);                                  // suelto: se arma
        comprobar(led[1] === 1'b1,         "armado despues de ver SW1 suelto");
        repeat (6) begin sw[0] = ~sw[0]; esperar(anti / 8); end   // rebotes
        comprobar(ciclo_boot < 0,          "los rebotes no disparan");
        sw[0] = 1'b1;
        esperar(anti + 20);
        comprobar(ciclo_boot >= 0,         "SW1 apretado dispara BOOT");
        esperar(4 * anti);
      end
      3: begin
        sw[1] = 1'b1;
        esperar(lento - 2);
        comprobar(ciclo_boot < 0,          "SW2 mantenido no dispara antes de 2^WLento ciclos");
        esperar(12);
        comprobar(ciclo_boot >= 0,         "SW2 mantenido dispara al cumplir 2^WLento ciclos");
        $display("  BOOT sube en el ciclo %0d (2^WLento = %0d, diferencia %0d)", ciclo_boot, lento, ciclo_boot - lento);
        esperar(4 * anti);
      end
      4: begin
        sw[2] = 1'b1;
        esperar(rapido - 2);
        comprobar(ciclo_boot < 0,          "SW3 mantenido no dispara antes de 2^WRapido ciclos");
        esperar(12);
        comprobar(ciclo_boot >= 0,         "SW3 mantenido dispara al cumplir 2^WRapido ciclos");
        $display("  BOOT sube en el ciclo %0d (2^WRapido = %0d, diferencia %0d)", ciclo_boot, rapido, ciclo_boot - rapido);
        esperar(4 * anti);
      end
      default: begin
        esperar(rapido + 100);
        comprobar(ciclo_boot < 0,          "sin SW3 no dispara");
        sw[2] = 1'b1;
        esperar(anti + 20);
        comprobar(ciclo_boot >= 0,         "SW3 apretado tarde dispara al pasar el antirrebote");
        esperar(4 * anti);
      end
    endcase

    if (ciclo_boot >= 0) begin
      comprobar(sel_malo == 0,             "S1 S0 apuntan a la otra imagen mientras BOOT esta en alto");
      comprobar(boot_bajo == 0,            "BOOT queda en alto");
      comprobar(led[3] === (IMG == 0) && led_marca_mal == 0, "el LED 4 se invierte junto con BOOT");
      $display("  S1 S0 = %02b", sel);
    end

    if (fallas == 0) $display("PASS imagen %0d escenario %0d", IMG, escenario);
    else             $display("FAIL imagen %0d escenario %0d: %0d fallas", IMG, escenario, fallas);
    $finish;
  end

endmodule
