// xd_vectores.svh: lazo común de los testbenches combinacionales de la pieza D.
//
// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
// Arquitectura de Computadores, Universidad de los Andes, 2026-2.
//
// Se incluye dentro del módulo del testbench, que debe declarar antes el
// cable `r` (salida del módulo bajo prueba) y definir VEC (archivo de
// vectores) y NOMBRE. Lee una línea por vector, generada por
// tools/gen_vectores.py desde el modelo ref/xd.py:
//     <a> <b> <selector> <pasos> <esperado>
// Aplica el módulo `pasos` veces, realimentando su salida en `a`, y compara
// el último resultado con el esperado.

  logic [31:0] a, b, esperado, a0;
  logic [7:0]  sel;
  int          pasos, fd, n = 0, errores = 0;

  initial begin
    fd = $fopen(`VEC, "r");
    if (fd == 0) begin
      $display("ERROR: no se encontro %s", `VEC);
      $fatal(1);
    end
    while ($fscanf(fd, "%h %h %h %h %h\n", a0, b, sel, pasos, esperado) == 5) begin
      a = a0;
      repeat (pasos - 1) begin
        #1 a = r;
      end
      #1;
      if (r !== esperado) begin
        errores++;
        if (errores <= 10)
          $display("  diferencia: a=%08x b=%08x sel=%02x pasos=%0d  obtenido=%08x esperado=%08x",
                   a0, b, sel, pasos, r, esperado);
      end
      n++;
    end
    $fclose(fd);
    if (errores == 0 && n > 0) begin
      $display("PASS %s: %0d vectores identicos al modelo ref/xd.py", `NOMBRE, n);
    end else begin
      $display("FAIL %s: %0d diferencias en %0d vectores", `NOMBRE, errores, n);
      $fatal(1);
    end
    $finish;
  end
