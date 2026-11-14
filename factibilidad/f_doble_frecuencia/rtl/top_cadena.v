// top_cadena.v: diseño mínimo para medir la cadena de retardo del duplicador.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// El duplicador y un contador de 26 bits en el reloj doblado, con los
// cuatro bits altos en los LED. Se usa en scripts/medir_cadena.sh para
// barrer el largo de la cadena, la semilla y la ubicación.

module top_cadena #(
  parameter N    = 8,
  parameter Modo = 0
) (
  input  wire       i_Clk,
  output wire [3:0] o_LED
);

  wire clk2x;

  duplicador_reloj #(.N(N), .Modo(Modo)) u_dup (
    .clk_i   (i_Clk),
    .clk2x_o (clk2x),
    .pulso_o (),
    .ret_o   (),
    .toma_o  ()
  );

  reg [25:0] cnt_q = 26'd0;
  always @(posedge clk2x) cnt_q <= cnt_q + 1'b1;

  assign o_LED = cnt_q[25:22];

endmodule
