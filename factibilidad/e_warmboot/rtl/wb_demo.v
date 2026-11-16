// wb_demo.v: imagen mínima para probar SB_WARMBOOT en la Go Board.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// De este módulo salen las dos imágenes de la prueba de placa. Lo único que
// cambia entre ellas son los parámetros Img y Destino:
//
//   Img = 0   display izquierdo "A", LED 1 encendido, salta a la imagen 1
//   Img = 1   display izquierdo "b", LED 4 encendido, salta a la imagen 0
//
// Además, el LED 4 se invierte en el ciclo en que sube BOOT y queda así hasta
// que la FPGA suelta los pines. Con un osciloscopio en ese pin se ve el
// instante exacto del disparo (ver "Salidas para medir").
//
// El display derecho cuenta los segundos desde que la FPGA terminó de
// configurarse (0 a 9 y vuelve a 0). Cada vez que la imagen se recarga, la
// cuenta parte de cero: así se ve que hubo una reconfiguración aunque la
// letra no cambie.
//
// Interruptores (se suponen activos en alto, como los lee pochoco_periph):
//
//   SW1  salto manual. Hay que soltarlo y volver a apretarlo: la imagen recién
//        cargada no salta mientras no haya visto el botón suelto. Sin eso,
//        dejar el dedo puesto haría rebotar entre las dos imágenes.
//   SW2  mientras se mantiene apretado, ping-pong lento: cada imagen espera
//        2^WLento ciclos desde que arrancó (0,671 s con WLento = 24) y salta.
//   SW3  mientras se mantiene apretado, ping-pong rápido: espera 2^WRapido
//        ciclos (41,9 ms con WRapido = 20).
//
// En los dos modos de ping-pong el tiempo entre dos arranques seguidos es
//   2^W / 25 MHz + tiempo de reconfiguración
// y el primer sumando se conoce con la exactitud del cristal. Ese es el
// principio de la medición sin instrumentos.
//
// Salidas para medir:
//
//   o_UART_TX   un byte a 115200 baudios cada vez que la imagen arranca: "A"
//               o "b". El computador les pone hora (scripts/medir_uart.py).
//   o_SPI_MISO  en 0 mientras la imagen corre, igual que el SoC cuando CS_n
//               está en alto. Durante la reconfiguración el pin queda en alta
//               impedancia: con un osciloscopio en el PMOD se ve lo mismo que
//               vería la maestra.
//   o_LED[3]    (LED 4) marca el disparo: cambia de nivel junto con BOOT.
//               Después el pin queda suelto, a un voltaje intermedio (el
//               pull-up interno a través del LED), y al final lo maneja la
//               imagen nueva. En el osciloscopio se ven los tres tramos: del
//               disparo a que se sueltan los pines, y de ahí a que la imagen
//               nueva arranca.
//
// La salida BOOT queda en alto hasta que la FPGA se reconfigura: no se baja.

module wb_demo #(
  parameter       Img         = 0,
  parameter [1:0] Destino     = 2'b01,
  parameter       WLento      = 24,
  parameter       WRapido     = 20,
  parameter       WAntirreb   = 18,     // 2^18 ciclos = 10,5 ms
  parameter       WSegundo    = 25'd25_000_000,
  parameter       DivBaudios  = 217     // 25 MHz / 115200
) (
  input  wire       i_Clk,

  output wire [3:0] o_LED,
  input  wire [3:0] i_Switch,

  output wire       o_Segment1_A, o_Segment1_B, o_Segment1_C, o_Segment1_D,
  output wire       o_Segment1_E, o_Segment1_F, o_Segment1_G,
  output wire       o_Segment2_A, o_Segment2_B, o_Segment2_C, o_Segment2_D,
  output wire       o_Segment2_E, o_Segment2_F, o_Segment2_G,

  output wire       o_UART_TX,
  output wire       o_SPI_MISO
);

  wire clk = i_Clk;

  // --- Tiempo desde el arranque ---------------------------------------------
  // Contador que se detiene al llegar al máximo. Los flip-flops del iCE40
  // parten en 0 después de la configuración, así que no hace falta reset.
  reg [WLento:0] t = 0;
  wire t_tope = t[WLento];
  always @(posedge clk) if (!t_tope) t <= t + 1'b1;

  // --- Interruptores: sincronizador y antirrebote ---------------------------
  reg [2:0] sw_s1 = 0, sw_s2 = 0;
  always @(posedge clk) begin
    sw_s1 <= i_Switch[2:0];
    sw_s2 <= sw_s1;
  end

  // Un solo contador de antirrebote para los tres: el estado filtrado cambia
  // cuando la entrada lleva 2^WAntirreb ciclos distinta de él.
  reg [2:0]           sw_q   = 0;
  reg [WAntirreb-1:0] rebote = 0;
  always @(posedge clk) begin
    if (sw_s2 == sw_q)   rebote <= 0;
    else if (&rebote)    begin sw_q <= sw_s2; rebote <= 0; end
    else                 rebote <= rebote + 1'b1;
  end

  // El salto manual se arma solo después de ver SW1 suelto durante un período
  // completo de antirrebote contado desde el arranque.
  reg [WAntirreb-1:0] suelto = 0;
  reg                 armado = 0;
  always @(posedge clk) begin
    if (sw_s2[0])        suelto <= 0;
    else if (&suelto)    armado <= 1'b1;
    else                 suelto <= suelto + 1'b1;
  end

  // --- Disparo ----------------------------------------------------------------
  // paso_rapido queda en 1 desde que t llega a 2^WRapido.
  reg paso_rapido = 0;
  always @(posedge clk) if (t[WRapido]) paso_rapido <= 1'b1;

  wire manual  = armado & sw_q[0];
  wire lento   = sw_q[1] & t_tope;
  wire rapido  = sw_q[2] & paso_rapido;

  reg boot_q = 0;
  always @(posedge clk) if (manual | lento | rapido) boot_q <= 1'b1;

  SB_WARMBOOT u_wb (
    .BOOT (boot_q),
    .S1   (Destino[1]),
    .S0   (Destino[0])
  );

  // --- UART: un byte al arrancar ---------------------------------------------
  // Se espera 4096 ciclos (164 us) con la línea en reposo antes del bit de
  // partida, para que el receptor vea un reposo limpio después de la alta
  // impedancia de la configuración.
  localparam [7:0] LETRA = (Img == 0) ? 8'h41 : 8'h62;    // "A" o "b"
  reg [9:0]  uart_sr  = 10'h3FF;       // {stop, dato[7:0], start}, sale el bit 0
  reg [3:0]  uart_n   = 0;             // bits que faltan por enviar
  reg [8:0]  uart_div = 0;
  reg        uart_fue = 0;
  always @(posedge clk) begin
    if (!uart_fue && t[12]) begin
      uart_sr  <= {1'b1, LETRA, 1'b0};
      uart_n   <= 4'd10;
      uart_div <= 0;
      uart_fue <= 1'b1;
    end else if (uart_n != 0) begin
      if (uart_div == DivBaudios - 1) begin
        uart_div <= 0;
        uart_sr  <= {1'b1, uart_sr[9:1]};
        uart_n   <= uart_n - 1'b1;
      end else uart_div <= uart_div + 1'b1;
    end
  end
  assign o_UART_TX = uart_sr[0];

  // --- Displays ---------------------------------------------------------------
  // Segundos desde el arranque, de 0 a 9.
  reg [24:0] div_s = 0;
  reg [3:0]  seg_s = 0;
  always @(posedge clk) begin
    if (div_s == WSegundo - 1) begin
      div_s <= 0;
      seg_s <= (seg_s == 4'd9) ? 4'd0 : seg_s + 1'b1;
    end else div_s <= div_s + 1'b1;
  end

  // Mismo orden de bits que hex2seg de pochoco_periph: {G, F, E, D, C, B, A},
  // en 1 el segmento encendido.
  function [6:0] dec2seg;
    input [3:0] d;
    begin
      case (d)
        4'd0: dec2seg = 7'b0111111;
        4'd1: dec2seg = 7'b0000110;
        4'd2: dec2seg = 7'b1011011;
        4'd3: dec2seg = 7'b1001111;
        4'd4: dec2seg = 7'b1100110;
        4'd5: dec2seg = 7'b1101101;
        4'd6: dec2seg = 7'b1111101;
        4'd7: dec2seg = 7'b0000111;
        4'd8: dec2seg = 7'b1111111;
        default: dec2seg = 7'b1101111;   // 9
      endcase
    end
  endfunction

  wire [6:0] seg1 = (Img == 0) ? 7'b1110111 : 7'b1111100;   // "A" o "b"
  wire [6:0] seg2 = dec2seg(seg_s);

  // Los displays de la placa son activos en bajo
  assign {o_Segment1_G, o_Segment1_F, o_Segment1_E, o_Segment1_D,
          o_Segment1_C, o_Segment1_B, o_Segment1_A} = ~seg1;
  assign {o_Segment2_G, o_Segment2_F, o_Segment2_E, o_Segment2_D,
          o_Segment2_C, o_Segment2_B, o_Segment2_A} = ~seg2;

  // --- LEDs -------------------------------------------------------------------
  //   LED 1  encendido en la imagen 0        LED 4  encendido en la imagen 1
//                                           (se invierte al subir BOOT)
  //   LED 2  salto manual armado             LED 3  parpadea una vez por segundo
  assign o_LED[0] = (Img == 0);
  assign o_LED[1] = armado;
  assign o_LED[2] = div_s[23];
  assign o_LED[3] = (Img != 0) ^ boot_q;

  assign o_SPI_MISO = 1'b0;

endmodule
