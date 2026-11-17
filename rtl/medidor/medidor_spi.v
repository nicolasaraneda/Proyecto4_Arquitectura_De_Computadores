// medidor_spi.v: mide en la placa los tiempos reales de la maestra SPI.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Bitstream de diagnóstico para el 26/11 (docs/checklist_26nov.md). No tiene
// el SoC ni el Espino: solo escucha SCLK, MOSI y CS_n de la maestra del curso
// y muestra en los 7 segmentos lo que midió. Por MISO responde siempre 0x00,
// que es "mantener 0": la maestra ve un grupo que no opera.
//
// Para qué sirve: R1 necesita hasta 444 ciclos entre el fin de una transacción
// y el comienzo de la siguiente. Con SCLK de 1 MHz y período de 0,1 ms hay
// 2262; con SCLK de 100 kHz, solo 237. El árbol de decisión del 1/12
// (docs/arbol_decision.md) usa este medidor: si en la ronda 3 el SCLK real es
// menor que 115 kHz, compite R0.
//
// Todo se mide en ciclos del reloj de 25 MHz (40 ns), después de sincronizar
// las tres entradas con dos flip-flops, igual que pochoco_spi_slave. La
// resolución es de un ciclo.
//
// Uso en la placa:
//   SW1   pasa a la medida siguiente (0 a 7, vuelve a 0)
//   SW2   pasa a la medida anterior
//   SW3   borra los mínimos, los máximos, la cuenta y la alarma (entre rondas)
//   SW4   mientras se mantiene apretado, los 7 segmentos muestran el byte alto
//   LED1 a LED3   número de la medida en binario (LED1 es el bit 0)
//   LED4  alarma: alguna transacción no tuvo exactamente 8 flancos de subida
//         de SCLK, hubo un flanco de subida de SCLK con CS_n en alto (bus
//         compartido con otro esclavo), o SCLK estaba en alto al bajar CS_n
//         (maestra de modo 2 o 3). El esclavo del SoC toma cada flanco con
//         CS_n en alto como un precio si su contador de bits quedó en 7, y con
//         una maestra de modo 3 la decisión se lee corrida un bit (revisión
//         P10, docs/revision_p10.md, hallazgo 1 y observación 4)
//
// Medidas, en hexadecimal (16 bits; byte bajo sin SW4 y alto con SW4):
//   0  período mínimo de SCLK, en ciclos. kHz = 25 000 / valor
//   1  período máximo de SCLK, en ciclos
//   2  período entre precios de la última transacción, en unidades de 16
//      ciclos (0,64 us). 0,1 ms = 0x009C, 1 ms = 0x061A, 10 ms = 0x3D09
//   3  período mínimo entre precios, en unidades de 16 ciclos
//   4  duración de CS_n en bajo de la última transacción, en ciclos
//      (9,5 us = 0x00ED)
//   5  de la bajada de CS_n al primer flanco de subida de SCLK, última
//      transacción, en ciclos (1,5 us = 0x0025 en el testbench oficial)
//   6  tiempo libre mínimo: de la subida de CS_n a la bajada siguiente, en
//      ciclos. Es el presupuesto de la respuesta (0x08D6 = 2262 en la ronda
//      3 del testbench oficial). Satura en 0xFFFF (más de 2,6 ms)
//   7  transacciones contadas desde la última vez que se borró
//
// Un período que no cabe en 16 bits queda en 0xFFFF. Los mínimos parten en
// 0xFFFF y los máximos en 0 hasta la primera medida.

module medidor_spi #(
  parameter integer REBOTE = 250000      // ciclos de estabilidad de un botón (10 ms)
) (
  input  wire       i_Clk,
  input  wire [3:0] i_Switch,
  output wire [3:0] o_LED,
  output wire       o_Segment1_A, o_Segment1_B, o_Segment1_C, o_Segment1_D,
  output wire       o_Segment1_E, o_Segment1_F, o_Segment1_G,
  output wire       o_Segment2_A, o_Segment2_B, o_Segment2_C, o_Segment2_D,
  output wire       o_Segment2_E, o_Segment2_F, o_Segment2_G,
  input  wire       i_SPI_SCLK,
  input  wire       i_SPI_MOSI,
  input  wire       i_SPI_CS_n,
  output wire       o_SPI_MISO
);

  wire clk = i_Clk;
  assign o_SPI_MISO = 1'b0;

  // --- Sincronización y flancos ------------------------------------------------
  reg [2:0] sclk_s = 3'b000;
  reg [2:0] cs_s   = 3'b111;
  always @(posedge clk) begin
    sclk_s <= {sclk_s[1:0], i_SPI_SCLK};
    cs_s   <= {cs_s[1:0], i_SPI_CS_n};
  end
  wire sclk_sube = (sclk_s[2:1] == 2'b01);
  wire cs_baja   = (cs_s[2:1] == 2'b10);
  wire cs_sube   = (cs_s[2:1] == 2'b01);
  wire cs_activo = ~cs_s[1];

  // --- Botones con antirrebote ---------------------------------------------------
  wire [3:0] apretado;
  wire [3:0] pulso;
  genvar b;
  generate
    for (b = 0; b < 4; b = b + 1) begin : g_boton
      medidor_boton #(.REBOTE(REBOTE)) u_b (
        .clk_i(clk), .boton_i(i_Switch[b]), .estable_o(apretado[b]), .pulso_o(pulso[b]));
    end
  endgenerate
  wire borrar = pulso[2];

  // --- Contadores de tiempo (saturan) --------------------------------------------
  reg [15:0] t_sclk  = 16'hFFFF;    // ciclos desde la última subida de SCLK
  reg [15:0] t_cs    = 16'd0;       // ciclos desde la última bajada de CS_n
  reg [19:0] t_per   = 20'hFFFFF;   // ciclos desde la bajada anterior de CS_n
  reg [15:0] t_libre = 16'hFFFF;    // ciclos desde la última subida de CS_n
  reg [3:0]  bits    = 4'd0;        // subidas de SCLK en la transacción
  reg        primera = 1'b1;        // primera subida de SCLK de la transacción

  // --- Resultados ---------------------------------------------------------------
  reg [15:0] sclk_min  = 16'hFFFF;
  reg [15:0] sclk_max  = 16'd0;
  reg [15:0] per_ult   = 16'hFFFF;
  reg [15:0] per_min   = 16'hFFFF;
  reg [15:0] dur_ult   = 16'd0;
  reg [15:0] setup_ult = 16'd0;
  reg [15:0] libre_min = 16'hFFFF;
  reg [15:0] cuenta    = 16'd0;
  reg        alarma    = 1'b0;
  reg        hubo      = 1'b0;      // hubo una transacción antes (period y libre valen)

  wire [15:0] per16 = t_per[19:4];   // unidades de 16 ciclos; satura en 0xFFFF con t_per

  always @(posedge clk) begin
    t_sclk  <= (t_sclk  == 16'hFFFF)  ? t_sclk  : t_sclk  + 16'd1;
    t_cs    <= (t_cs    == 16'hFFFF)  ? t_cs    : t_cs    + 16'd1;
    t_per   <= (t_per   == 20'hFFFFF) ? t_per   : t_per   + 20'd1;
    t_libre <= (t_libre == 16'hFFFF)  ? t_libre : t_libre + 16'd1;

    if (cs_baja) begin
      t_cs    <= 16'd0;
      t_per   <= 20'd0;
      bits    <= 4'd0;
      primera <= 1'b1;
      cuenta  <= cuenta + 16'd1;
      if (hubo) begin
        per_ult <= per16;
        if (per16 < per_min)     per_min   <= per16;
        if (t_libre < libre_min) libre_min <= t_libre;
      end
      hubo <= 1'b1;
    end

    if (sclk_sube && cs_activo) begin
      t_sclk <= 16'd0;
      bits   <= (bits == 4'hF) ? bits : bits + 4'd1;
      if (primera) begin
        primera   <= 1'b0;
        setup_ult <= t_cs;
      end else begin
        if (t_sclk < sclk_min) sclk_min <= t_sclk;
        if (t_sclk > sclk_max) sclk_max <= t_sclk;
      end
    end

    if (cs_sube) begin
      t_libre <= 16'd0;
      dur_ult <= t_cs;
      if (bits != 4'd8) alarma <= 1'b1;
    end

    if (sclk_sube && !cs_activo) alarma <= 1'b1;
    if (cs_baja && sclk_s[1])    alarma <= 1'b1;

    if (borrar) begin
      sclk_min  <= 16'hFFFF;
      sclk_max  <= 16'd0;
      per_min   <= 16'hFFFF;
      libre_min <= 16'hFFFF;
      cuenta    <= 16'd0;
      alarma    <= 1'b0;
      hubo      <= 1'b0;
    end
  end

  // --- Selección de la medida y salida -------------------------------------------
  reg [2:0] modo = 3'd0;
  always @(posedge clk) begin
    if (pulso[0])      modo <= modo + 3'd1;
    else if (pulso[1]) modo <= modo - 3'd1;
  end

  reg [15:0] valor;
  always @(*) begin
    case (modo)
      3'd0: valor = sclk_min;
      3'd1: valor = sclk_max;
      3'd2: valor = per_ult;
      3'd3: valor = per_min;
      3'd4: valor = dur_ult;
      3'd5: valor = setup_ult;
      3'd6: valor = libre_min;
      default: valor = cuenta;
    endcase
  end

  assign o_LED = {alarma, modo[2], modo[1], modo[0]};

  wire [7:0] muestra = apretado[3] ? valor[15:8] : valor[7:0];

  function [6:0] hex2seg;                // el mismo decodificador de pochoco_periph.v
    input [3:0] hex;
    begin
      case (hex)
        4'h0: hex2seg = 7'b0111111;
        4'h1: hex2seg = 7'b0000110;
        4'h2: hex2seg = 7'b1011011;
        4'h3: hex2seg = 7'b1001111;
        4'h4: hex2seg = 7'b1100110;
        4'h5: hex2seg = 7'b1101101;
        4'h6: hex2seg = 7'b1111101;
        4'h7: hex2seg = 7'b0000111;
        4'h8: hex2seg = 7'b1111111;
        4'h9: hex2seg = 7'b1101111;
        4'hA: hex2seg = 7'b1110111;
        4'hB: hex2seg = 7'b1111100;
        4'hC: hex2seg = 7'b0111001;
        4'hD: hex2seg = 7'b1011110;
        4'hE: hex2seg = 7'b1111001;
        default: hex2seg = 7'b1110001;
      endcase
    end
  endfunction

  wire [6:0] seg1 = hex2seg(muestra[7:4]);
  wire [6:0] seg2 = hex2seg(muestra[3:0]);
  // Los 7 segmentos de la placa son activos en bajo
  assign {o_Segment1_G, o_Segment1_F, o_Segment1_E, o_Segment1_D,
          o_Segment1_C, o_Segment1_B, o_Segment1_A} = ~seg1;
  assign {o_Segment2_G, o_Segment2_F, o_Segment2_E, o_Segment2_D,
          o_Segment2_C, o_Segment2_B, o_Segment2_A} = ~seg2;

endmodule


// Botón con antirrebote: estable_o cambia cuando la entrada lleva REBOTE ciclos
// sin cambiar; pulso_o dura un ciclo al apretar.
module medidor_boton #(
  parameter integer REBOTE = 250000
) (
  input  wire clk_i,
  input  wire boton_i,
  output reg  estable_o = 1'b0,
  output wire pulso_o
);
  reg [1:0]  s = 2'b00;
  reg [17:0] n = 18'd0;
  reg        antes = 1'b0;
  always @(posedge clk_i) begin
    s     <= {s[0], boton_i};
    antes <= estable_o;
    if (s[1] == estable_o) n <= 18'd0;
    else if (n == REBOTE - 1) begin
      n         <= 18'd0;
      estable_o <= s[1];
    end else n <= n + 18'd1;
  end
  assign pulso_o = estable_o & ~antes;
endmodule
