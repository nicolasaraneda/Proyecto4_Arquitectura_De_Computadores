// testigo_top.v: imagen 1 de las imágenes múltiples de prueba de R2
// (docs/autoprueba.md, sección 8).
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Es lo que aparece en la placa si el vigilante de la imagen 0 pide el
// relevo. Tiene que reconocerse a simple vista y no parecerse a nada que
// muestre la autoprueba:
//   LED1 a LED4   los cuatro encendidos, fijos
//   7 segmentos   "--" (solo el segmento G de cada dígito). La autoprueba
//                 muestra siempre dos dígitos hexadecimales
//   SW4           mientras se mantiene apretado, los 7 segmentos muestran los
//                 minutos desde que esta imagen arrancó, en decimal (hasta 99).
//                 En la prueba de media hora dice cuándo ocurrió el relevo
//   UART          el pin de transmisión repite el de recepción (eco), igual
//                 que en la imagen 0
//   MISO (PMOD)   en 0, igual que en la imagen 0
// No tiene SoC ni vigilante: no puede pedir otro relevo.

module testigo_top #(
  parameter integer MINUTO = 1500000000      // ciclos de 40 ns en un minuto
) (
  input  wire       i_Clk,
  input  wire [3:0] i_Switch,
  output wire [3:0] o_LED,
  output wire       o_Segment1_A, o_Segment1_B, o_Segment1_C, o_Segment1_D,
  output wire       o_Segment1_E, o_Segment1_F, o_Segment1_G,
  output wire       o_Segment2_A, o_Segment2_B, o_Segment2_C, o_Segment2_D,
  output wire       o_Segment2_E, o_Segment2_F, o_Segment2_G,
  input  wire       i_UART_RX,
  output wire       o_UART_TX,
  output wire       o_SPI_MISO
);

  assign o_UART_TX  = i_UART_RX;
  assign o_SPI_MISO = 1'b0;
  assign o_LED      = 4'b1111;

  // Minutos desde el arranque, en dos dígitos decimales que se detienen en 99
  reg [30:0] ciclos = 31'd0;
  reg [3:0]  unidades = 4'd0, decenas = 4'd0;
  wire       tope = (decenas == 4'd9) && (unidades == 4'd9);

  always @(posedge i_Clk) begin
    if (ciclos == MINUTO - 1) begin
      ciclos <= 31'd0;
      if (!tope) begin
        if (unidades == 4'd9) begin
          unidades <= 4'd0;
          decenas  <= decenas + 4'd1;
        end else begin
          unidades <= unidades + 4'd1;
        end
      end
    end else begin
      ciclos <= ciclos + 31'd1;
    end
  end

  function [6:0] dec2seg;                // G..A, activos en alto
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
        default: dec2seg = 7'b1101111;
      endcase
    end
  endfunction

  wire [6:0] guion = 7'b1000000;
  wire [6:0] seg1  = i_Switch[3] ? dec2seg(decenas)  : guion;
  wire [6:0] seg2  = i_Switch[3] ? dec2seg(unidades) : guion;
  // Los 7 segmentos de la placa son activos en bajo
  assign {o_Segment1_G, o_Segment1_F, o_Segment1_E, o_Segment1_D,
          o_Segment1_C, o_Segment1_B, o_Segment1_A} = ~seg1;
  assign {o_Segment2_G, o_Segment2_F, o_Segment2_E, o_Segment2_D,
          o_Segment2_C, o_Segment2_B, o_Segment2_A} = ~seg2;

  wire _sin_uso = &{1'b0, i_Switch[2:0]};

endmodule
