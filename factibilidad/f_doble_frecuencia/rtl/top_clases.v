// top_clases.v: diseño de control para validar scripts/sta_icestorm.py.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Tres registros en un solo reloj: uno en el flanco de subida, uno en el de
// bajada y otro en el de subida. Entre ellos hay una ruta corta y una larga
// (un producto por constante). Con Caso = 0 la ruta larga va del flanco de
// bajada al de subida, y con Caso = 1 del de subida al de bajada. Así la
// ruta crítica que informa nextpnr es de una clase conocida y se puede
// comparar con la que calcula sta_icestorm.py para esa clase.

module top_clases #(
  parameter Caso = 0
) (
  input  wire       i_Clk,
  input  wire [3:0] i_Switch,
  output wire [3:0] o_LED
);

  reg [7:0] a_q = 8'd0, b_q = 8'd0, c_q = 8'd0;

  function [7:0] larga;
    input [7:0] x;
    begin
      larga = (x * 8'd37) + {x[0], x[7:1]} + (x << 3);
    end
  endfunction

  function [7:0] corta;
    input [7:0] x;
    begin
      // Rotación en 3 y no en 4: con 4 las dos mitades del resultado quedan
      // iguales, o_LED sale constante con Caso = 1 y Yosys borra el diseño.
      corta = x ^ {x[2:0], x[7:3]};
    end
  endfunction

  always @(posedge i_Clk) a_q <= {a_q[6:0], a_q[7] ^ a_q[5]} ^ {4'b0, i_Switch};
  always @(negedge i_Clk) b_q <= (Caso == 0) ? corta(a_q) : larga(a_q);
  always @(posedge i_Clk) c_q <= (Caso == 0) ? larga(b_q) : corta(b_q);

  assign o_LED = c_q[7:4] ^ c_q[3:0];

endmodule
