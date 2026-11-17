#!/usr/bin/env python3
"""gen_tabla.py: la tabla de parámetros de sw/fondo.s como ROM en Verilog, para la edición ASIC.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Lee sw/fondo_tabla.hex (256 valores de 16 bits) y escribe un módulo pochoco_tabla con la
misma interfaz y la misma lectura registrada que rtl/pochoco_tabla.v, pero con el
contenido como un case (en celdas estándar no hay $readmemh). Las palabras en cero no se
escriben: caen en el default.

Uso: python3 asic/scripts/gen_tabla.py sw/fondo_tabla.hex asic/build/gen/pochoco_tabla_rom.v
"""
import sys

valores = [int(x, 16) for x in open(sys.argv[1]).read().split()]
assert len(valores) == 256, "la tabla tiene que traer 256 valores"
L = ["// Generado por asic/scripts/gen_tabla.py desde " + sys.argv[1] + ". No editar a mano.",
     "module pochoco_tabla #(parameter MemFile = \"\") (",
     "  input  wire        clk_i,", "  input  wire        rd_i,", "  input  wire [7:0]  idx_i,", "  output wire [31:0] rdata_o", ");",
     "  reg [15:0] q;", "  reg [15:0] v;", "  always @(*) begin", "    case (idx_i)"]
for i, v in enumerate(valores):
    if v:
        L.append(f"      8'd{i}: v = 16'h{v:04x};")
L += ["      default: v = 16'h0000;", "    endcase", "  end",
      "  always @(posedge clk_i) begin", "    if (rd_i) q <= v;", "  end",
      "  assign rdata_o = {{16{q[15]}}, q};", "endmodule", ""]
open(sys.argv[2], "w").write("\n".join(L))
