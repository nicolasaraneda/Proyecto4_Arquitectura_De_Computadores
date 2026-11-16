// autoprueba_top.v: bitstream de autoprueba en placa (docs/autoprueba.md).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Es el mismo pochoco_soc que compite, sin cambios, con una maestra SPI
// adentro de la FPGA en vez de la externa. La maestra hace lo mismo que la del
// testbench oficial: cada período manda un precio y lee la decisión que el
// programa dejó en DECISION. Los precios salen de una caminata aleatoria
// generada con un registro de desplazamiento realimentado (LFSR), así que la
// secuencia es siempre la misma y se puede calcular afuera. Cada bit leído por
// MISO entra a una firma CRC-16. Al terminar los NTICKS precios la firma se
// compara con FIRMA_ESPERADA, que calcula el gemelo digital con la misma
// secuencia (tools/autoprueba.py).
//
// Uso en la placa (Nandland Go Board):
//   SW1  parte con período de 10 ms (ronda 1)
//   SW2  parte con período de 1 ms (ronda 2)
//   SW3  parte con período de 0,1 ms (ronda 3)
//   SW4  mientras se mantiene apretado, los 7 segmentos muestran el byte alto
//        de la firma en vez del bajo
//   LED1 parpadea mientras corre (cambia cada 64 precios)
//   LED2 terminó
//   LED3 terminó y la firma coincide con la esperada
//   LED4 terminó y la firma NO coincide
// Los 7 segmentos muestran, en hexadecimal, un byte de la firma: mientras
// corre, la firma parcial; al terminar, la final. Para repetir con otro
// período hay que reiniciar la placa (desconectar y conectar el USB): el SoC
// solo se reinicia al configurarse la FPGA, y la firma supone que el programa
// parte de cero.
//
// Las salidas de LED y 7 segmentos del SoC quedan sin conectar (la síntesis
// elimina los registros que las manejan): la telemetría de sw/fondo.s no se
// ve en esta versión. Los botones del SoC se leen en 0, como en el testbench.
//
// La maestra está hecha para costar lo menos posible, porque R0 ocupa el 85 %
// de la FPGA: un contador t de 9 bits desde el inicio de cada tick da la
// transacción completa, sin contadores de fase ni de bit. SCLK tiene un medio
// período de 16 ciclos (640 ns, 781 kHz, dentro del rango de 100 kHz a 1 MHz
// que pide la puerta), así que t[4] es SCLK y t[8:5] el número de bit. Con la
// numeración del gemelo (los pines cambian justo después del flanco en que t
// vale lo indicado):
//   t = 0                   baja CS_n
//   t = 32 (i + 1)          MOSI toma el bit 7 - i, y baja SCLK si i > 0
//   t = 32 (i + 1) + 16     sube SCLK y se lee MISO              (i = 0 .. 7)
//   t = 288                 última bajada de SCLK
//   t = 304                 sube CS_n
// En el gemelo: --cs-setup-ns 1280 --sclk-medio-ns 640 --cs-hold-ns 640.

module autoprueba_top #(
  parameter        MemFile        = "sw/trade.hex",
  parameter integer NTICKS        = 2000,
  parameter [15:0] FIRMA_ESPERADA = 16'h0000,
  parameter integer P1            = 250000,     // 10 ms en ciclos de 40 ns
  parameter integer P2            = 25000,      // 1 ms
  parameter integer P3            = 2500        // 0,1 ms
) (
  input  wire       i_Clk,
  input  wire [3:0] i_Switch,
  output wire [3:0] o_LED,
  output wire       o_Segment1_A, o_Segment1_B, o_Segment1_C, o_Segment1_D,
  output wire       o_Segment1_E, o_Segment1_F, o_Segment1_G,
  output wire       o_Segment2_A, o_Segment2_B, o_Segment2_C, o_Segment2_D,
  output wire       o_Segment2_E, o_Segment2_F, o_Segment2_G
);

  wire clk = i_Clk;

  // --- El SoC que compite, sin cambios ------------------------------------------
  wire sclk, mosi, cs_n, miso;

  pochoco_soc #(.MemFile(MemFile)) u_soc (
    .i_Clk(clk), .o_LED(), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(sclk), .i_SPI_MOSI(mosi), .i_SPI_CS_n(cs_n), .o_SPI_MISO(miso));

  // --- Maestra interna ------------------------------------------------------------
  wire        corre, listo;
  wire [15:0] firma;
  wire [10:0] ticks;

  autoprueba_maestra #(.NTICKS(NTICKS), .P1(P1), .P2(P2), .P3(P3)) u_maestra (
    .clk_i   (clk),
    .elige_i (i_Switch[2:0]),
    .sclk_o  (sclk),
    .mosi_o  (mosi),
    .cs_n_o  (cs_n),
    .miso_i  (miso),
    .corre_o (corre),
    .listo_o (listo),
    .firma_o (firma),
    .ticks_o (ticks)
  );

  // --- Indicadores ------------------------------------------------------------------
  wire coincide = (firma == FIRMA_ESPERADA);
  assign o_LED[0] = corre & ticks[6];
  assign o_LED[1] = listo;
  assign o_LED[2] = listo & coincide;
  assign o_LED[3] = listo & ~coincide;

  wire [7:0] muestra = i_Switch[3] ? firma[15:8] : firma[7:0];

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


// Maestra SPI interna con la caminata aleatoria y la firma.
//
// Precio del tick 0: 128. Al cerrar cada tick el LFSR de 16 bits
// (x^16 + x^14 + x^13 + x^11 + 1, semilla 0xACE1) avanza un paso y su bit
// nuevo da el cambio de precio del tick siguiente: 1 sube 1 y 0 baja 1, sin
// pasar de 255 ni bajar de 1. Firma: CRC-16/CCITT (polinomio 0x1021, valor
// inicial 0xFFFF) de los NTICKS bytes leídos por MISO, en orden y con el bit
// más significativo primero. Se calcula bit a bit, al leer cada bit, que da lo
// mismo que byte a byte. tools/autoprueba.py implementa lo mismo en Python.
module autoprueba_maestra #(
  parameter integer NTICKS = 2000,
  parameter integer P1     = 250000,
  parameter integer P2     = 25000,
  parameter integer P3     = 2500
) (
  input  wire        clk_i,
  input  wire [2:0]  elige_i,     // botones SW1, SW2 y SW3
  output reg         sclk_o = 1'b0,
  output reg         mosi_o = 1'b0,
  output reg         cs_n_o = 1'b1,
  input  wire        miso_i,
  output reg         corre_o = 1'b0,
  output reg         listo_o = 1'b0,
  output reg  [15:0] firma_o = 16'hFFFF,
  output reg  [10:0] ticks_o = 11'd0
);

  reg  [1:0]  sel = 2'd0;          // período elegido: 0 10 ms, 1 1 ms, 2 0,1 ms
  reg  [17:0] resto = 18'd0;       // ciclos que faltan para el próximo tick
  reg  [8:0]  t = 9'd511;          // ciclos desde el inicio del tick (se detiene en 511)
  reg  [15:0] lfsr = 16'hACE1;
  reg  [7:0]  tx = 8'd128;         // precio del tick; rota durante la transacción

  wire        inicio = corre_o && (resto == 18'd0);
  wire [17:0] carga  = (sel == 2'd0) ? P1 - 1 : (sel == 2'd1) ? P2 - 1 : P3 - 1;
  wire [3:0]  bit_t  = t[8:5];     // 1 .. 8 durante los bits, 9 en la última bajada
  wire        en_bit = (bit_t >= 4'd1) && (bit_t <= 4'd8);
  wire        lfsr_n = lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10];
  wire        fb     = firma_o[15] ^ miso_i;

  always @(posedge clk_i) begin
    if (!corre_o && !listo_o) begin
      // Espera a que se elija un período
      if (elige_i != 3'b000) begin
        sel     <= elige_i[0] ? 2'd0 : elige_i[1] ? 2'd1 : 2'd2;
        corre_o <= 1'b1;
        resto   <= 18'd0;              // el primer tick parte en el ciclo siguiente
      end
    end else if (corre_o) begin
      resto <= inicio ? carga : resto - 18'd1;
      t     <= inicio ? 9'd0 : (t == 9'd511) ? t : t + 9'd1;

      if (t == 9'd0) cs_n_o <= 1'b0;
      if (t[4:0] == 5'd0 && (en_bit || bit_t == 4'd9)) begin
        sclk_o <= 1'b0;
        if (en_bit) begin
          mosi_o <= tx[7];
          tx     <= {tx[6:0], tx[7]};  // después de 8 bits vuelve a ser el precio
        end
      end
      if (t[4:0] == 5'd16 && en_bit) begin
        sclk_o  <= 1'b1;
        firma_o <= {firma_o[14:0], 1'b0} ^ (fb ? 16'h1021 : 16'h0000);
      end
      if (t == 9'd304) begin
        cs_n_o  <= 1'b1;
        ticks_o <= ticks_o + 11'd1;
        // precio del tick siguiente
        lfsr <= {lfsr[14:0], lfsr_n};
        if (lfsr_n) tx <= (tx == 8'd255) ? tx : tx + 8'd1;
        else        tx <= (tx == 8'd1)   ? tx : tx - 8'd1;
        if (ticks_o == NTICKS - 1) begin
          corre_o <= 1'b0;
          listo_o <= 1'b1;
        end
      end
    end
  end

endmodule
