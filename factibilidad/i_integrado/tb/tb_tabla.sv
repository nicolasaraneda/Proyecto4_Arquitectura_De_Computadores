// tb_tabla.sv: la memoria para la tabla de política dentro del SoC integrado,
// usada por los cuatro hilos del barrel.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Corre sw/tabla_prueba.s y compara con un modelo que este testbench calcula
// por su cuenta:
//   - la tabla completa, entrada por entrada, leída de la memoria;
//   - la suma de comprobación que publica cada hilo y la suma total;
//   - el display y los LEDs;
//   - que la memoria de programa y datos (pochoco_ram) no haya cambiado fuera
//     de la zona de resultados. En la forma 2 esto comprueba que una
//     escritura en 0x800 a 0xFFF no cae sobre el programa, que es lo que
//     pasaría en el SoC original, donde esas direcciones repiten la memoria.
//
// Se compila con la misma definición que elige la forma en el SoC:
//   -DI_TABLA=1   BRAM de 256 x 16 por MMIO (rtl/tabla_mmio.v)
//   -DI_TABLA=2   otras 512 palabras de datos (rtl/tabla_ram.v)
// y se corre con +hex=PROGRAMA (tools/tabla.sh).

`timescale 1ns/1ps

`ifndef I_TABLA
  `define I_TABLA 1
`endif

module tb_tabla;
  localparam int          FORMA = `I_TABLA;
  localparam int          N     = (FORMA == 1) ? 256 : 512;
  localparam int          Q     = N / 4;
  localparam logic [31:0] W     = (FORMA == 1) ? 32'h0000_FFFF : 32'hFFFF_FFFF;
  localparam int          RES   = 'h700 / 4;        // palabra de la zona de resultados
  localparam int          TOPE  = 80000;            // ciclos

  logic clk = 0;
  always #20 clk = ~clk;

  wire [3:0] leds;
  pochoco_soc #(.MemFile(""), .PorBits(4)) dut (
    .i_Clk(clk), .o_LED(leds), .i_Switch(4'b0000),
    .o_Segment1_A(), .o_Segment1_B(), .o_Segment1_C(), .o_Segment1_D(),
    .o_Segment1_E(), .o_Segment1_F(), .o_Segment1_G(),
    .o_Segment2_A(), .o_Segment2_B(), .o_Segment2_C(), .o_Segment2_D(),
    .o_Segment2_E(), .o_Segment2_F(), .o_Segment2_G(),
    .i_SPI_SCLK(1'b0), .i_SPI_MOSI(1'b0), .i_SPI_CS_n(1'b1), .o_SPI_MISO());

  // Entrada i de la tabla, leída de la memoria, extendida a 32 bits
  function automatic logic [31:0] tabla(input int k);
`ifdef TB_TABLA_FORMA_2
    return dut.g_tabla_ram.u_tabla.mem[k];
`else
    return {16'b0, dut.g_tabla_mmio.u_tabla.mem[k]};
`endif
  endfunction

  logic [31:0] modelo [0:511];
  logic [31:0] suma [4];
  logic [31:0] total, v, x, e;
  logic [31:0] img [0:511];
  string       hex;
  int          errores = 0, ciclos = 0;

  initial begin
    if (!$value$plusargs("hex=%s", hex)) begin $display("falta +hex=ARCHIVO"); $fatal(1); end
    $readmemh(hex, img);
    $readmemh(hex, dut.u_ram.mem);

    // Modelo: lo mismo que hace cada hilo en sw/tabla_prueba.s
    total = 0;
    for (int t = 0; t < 4; t++) begin
      v = 32'h0000_1037 + 32'h0000_1000 * t;
      for (int k = 0; k < Q; k++) begin
        modelo[t * Q + k] = v & W;
        v = v + 32'h0123_0457;
      end
      suma[t] = 0;
      for (int k = 0; k < Q; k++) begin
        x = modelo[t * Q + k];
        suma[t] = suma[t] + x;
        modelo[t * Q + k] = (x + k + 1) & W;
      end
      e = modelo[t * Q];
      e[15:8] = 8'hA0 + t;                       // sb en el byte 1
      modelo[t * Q] = e;
      suma[t] = suma[t] + {16'b0, e[15:0]};      // lhu de la entrada
      suma[t] = suma[t] + {{24{e[15]}}, e[15:8]}; // lb del byte 1
      total = total + suma[t];
    end
  end

  task automatic revisar;
    // Tabla
    for (int k = 0; k < N; k++) begin
      if (tabla(k) !== modelo[k]) begin
        errores++;
        if (errores <= 8) $display("  tabla[%0d] = %08x, esperado %08x", k, tabla(k), modelo[k]);
      end
    end
    // Sumas publicadas, banderas y total
    for (int t = 0; t < 4; t++) begin
      if (dut.u_ram.mem[RES + t] !== suma[t]) begin
        errores++; $display("  suma del hilo %0d = %08x, esperado %08x", t, dut.u_ram.mem[RES + t], suma[t]);
      end
      if (dut.u_ram.mem[RES + 4 + t] !== 32'd1) begin
        errores++; $display("  bandera del hilo %0d = %08x, esperado 1", t, dut.u_ram.mem[RES + 4 + t]);
      end
    end
    if (dut.u_ram.mem[RES + 8] !== total) begin
      errores++; $display("  suma total = %08x, esperado %08x", dut.u_ram.mem[RES + 8], total);
    end
    if (dut.u_periph.digit_q !== total[7:0]) begin
      errores++; $display("  display = %02x, esperado %02x", dut.u_periph.digit_q, total[7:0]);
    end
    // El resto de la memoria de programa y datos no cambió
    for (int k = 0; k < 512; k++) begin
      if ((k < RES || k > RES + 8) && dut.u_ram.mem[k] !== img[k]) begin
        errores++;
        if (errores <= 8) $display("  la palabra %0d de la memoria de programa cambio: %08x, era %08x", k, dut.u_ram.mem[k], img[k]);
      end
    end
  endtask

  always @(posedge clk) begin
    ciclos++;
    if (leds === 4'hF || ciclos > TOPE) begin
      if (leds !== 4'hF) begin
        errores++; $display("  el supervisor no termino en %0d ciclos (LEDs = %b)", TOPE, leds);
      end
      revisar();
      if (errores == 0)
        $display("PASS tb_tabla forma %0d: %0d entradas iguales al modelo, sumas por hilo %08x %08x %08x %08x, total %08x, display %02x, %0d ciclos",
                 FORMA, N, suma[0], suma[1], suma[2], suma[3], total, total[7:0], ciclos);
      else begin
        $display("FAIL tb_tabla forma %0d: %0d diferencias", FORMA, errores);
        $fatal(1);
      end
      $finish;
    end
  end
endmodule
