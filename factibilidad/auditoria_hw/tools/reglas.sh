#!/usr/bin/env bash
# reglas.sh: reglas del enunciado para la configuración "fondo en un chip".
#
# Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
# Arquitectura de Computadores, Universidad de los Andes, 2026-2.
#
# La configuración es el hardware I1 de factibilidad/i_integrado (barrel,
# emad, devk, mulstep, vigilante y tabla de 256 x 16) con el programa
# sw/fondo.s de factibilidad/b_fondo_hilos. Tres comprobaciones:
#
#   R1  El core lee el precio y escribe la decisión. Se corre la serie de
#       práctica completa con tb/tb_carreras.sv sobre ese hardware y se mira
#       cada acceso al esclavo SPI: quién lo hace (monitor M1, solo el hilo 0)
#       y con qué (monitor M8, instrucciones load y store del programa).
#       Además, por lectura del RTL: qué puede escribir el registro DECISION.
#   R2  Nada guarda series de precios. Se compara la memoria al terminar los
#       20 000 ticks con la imagen inicial: solo pueden haber cambiado las 18
#       palabras de estado del programa. La tabla de 256 x 16 tiene que seguir
#       en cero (este programa no la usa). Se listan las constantes de la
#       imagen y los contenidos iniciales de memoria del RTL agregado.
#   R3  Cada módulo agregado tiene testbench. Por cada archivo de la lista de
#       fuentes de I1 que no está en rtl/ del repositorio, se buscan los
#       testbenches de factibilidad/ que instancian su módulo.
#
# Uso: factibilidad/auditoria_hw/tools/reglas.sh   (o make reglas)
# Resultado en mediciones/reglas.txt. Menos de un minuto.
set -uo pipefail
source "$(dirname "$0")/comun.sh"

O=$B/reglas
mkdir -p "$O"
cp $F/sw/fondo.s "$O/fondo.s"
$PYTHON tools/pochoasm.py "$O/fondo.s" -o "$O/fondo.hex" > /dev/null || exit 1
$PYTHON $F/tools/simbolos.py "$O/fondo.s" --vh "$O/simbolos.vh" || exit 1
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_carreras -O3 -DAUD_I1 $DEFS_I1A \
  -DNO_ICE40_DEFAULT_ASSIGNMENTS "-DPROGRAMA=\"$O/fondo.hex\"" "-I$O" --Mdir "$O/obj" -o sim \
  "$CELLS_SIM" $SRC_I $U/tb/tb_carreras.sv > "$O/verilator.log" 2>&1 || { echo "FAIL Verilator no compila"; exit 1; }
"$O/obj/sim" +serie=tb/practica.csv +nticks=20000 +periodo=100000 "+mem_fin=$O/mem_fin.hex" > "$O/run.log" 2>&1

{
echo "Auditoría: reglas del enunciado para el fondo en un chip (hardware I1 con sw/fondo.s)"
echo "Generado por factibilidad/auditoria_hw/tools/reglas.sh (make reglas). No editar a mano."
echo
versiones
echo "Hardware: SoC de $I con $DEFS_I1A"
echo "Programa: $F/sw/fondo.s (imagen con sha256 $(sha256sum "$O/fondo.hex" | cut -c1-16)...). Serie de práctica, 20 000 ticks a 0,1 ms."
echo
echo "R1. \"El core debe leer el precio y escribir la decisión\""
grep -E "^(Precios publicados|Decisiones|Lecturas de PRICE|Violaciones M1|Violaciones M8|Ciclos con BOOT)" "$O/run.log" | sed 's/^/   /'
m1=$(grep '^Violaciones M1' "$O/run.log" | awk '{print $3}')
m8=$(grep '^Violaciones M8' "$O/run.log" | awk '{print $3}')
if [ "$m1" = 0 ] && [ "$m8" = 0 ] && grep -q "^PASS monitores" "$O/run.log"; then
  echo "PASS R1: los $(grep '^Lecturas de PRICE' "$O/run.log" | grep -o '[0-9]*') precios los lee y las $(grep '^Decisiones' "$O/run.log" | grep -o '[0-9]*') decisiones las escribe el hilo 0 del core, con instrucciones lw y sw"
else echo "FAIL R1: hay accesos al SPI que no son load o store del hilo 0"; fi
echo "   Por lectura del RTL, lo único que escribe el registro DECISION (tx_hold del esclavo SPI):"
grep -n "tx_hold <=" $E/soc/pochoco_spi_slave.v | sed 's/^/     /'
echo "   y lo único que maneja el bus del esclavo (en $I/rtl/pochoco_soc.v):"
grep -nE "assign spi_req|assign spi_sel|\.req_i +\(spi_req\)|\.wdata_i +\(data_wdata\)," $I/rtl/pochoco_soc.v | sed 's/^/     /'
echo "   data_req, data_we, data_addr y data_wdata salen solo del core: $(grep -cE "\.data_(req|we|addr|wdata)_o" $I/rtl/pochoco_soc.v) conexiones, todas en u_core."
echo "   Módulos agregados con salida hacia el esclavo SPI o hacia el bus de datos: ninguno (vigilante solo tiene las salidas boot_o y sel_o;"
echo "   tabla_mmio y tabla_ram solo rdata_o; xd_opa, xd_alu y xd_unit son combinacionales dentro de la etapa X del core)."
echo "   Salidas de cada módulo agregado:"
for f in $E/rtl/vigilante.v $I/rtl/tabla_mmio.v $I/rtl/tabla_ram.v $D/rtl/xd_opa.v; do
  echo "     $(basename "$f"): $(grep -E "^ *output" "$f" | sed -E 's/^ *output +(wire|reg)? *(\[[^]]*\])? *//; s/[,;].*//' | tr '\n' ' ')"
done
echo
echo "R2. \"No almacenar series de precios en el diseño\""
$PYTHON - "$O/fondo.hex" "$O/mem_fin.hex" "$O/simbolos.vh" <<'PY'
import re, sys
ini = [int(x, 16) for x in open(sys.argv[1]).read().split()]
fin = []
for linea in open(sys.argv[2]):
    linea = linea.split("//")[0].strip()
    if linea and not linea.startswith("@"):
        fin += [int(x, 16) for x in linea.split()]
pal = dict(re.findall(r"`define PAL_(\w+) (\d+)", open(sys.argv[3]).read()))
nombre = {int(v): k for k, v in pal.items()}
# Estado del programa: PUB, CAJA, ACC, W1..W3, REF1..REF3 y DES, EST, TMP de cada gestor
estado = {int(pal["PUB"]), int(pal["CAJA"]), int(pal["ACC"]), int(pal["W1"]), int(pal["W2"]), int(pal["W3"])}
estado |= {0x7D0 // 4, 0x7D4 // 4, 0x7D8 // 4}
for k in ("1", "2", "3"):
    estado |= {int(pal["DES" + k]), int(pal["EST" + k]), int(pal["EST" + k]) + 1}
cambiadas = [i for i in range(min(len(ini), len(fin))) if ini[i] != fin[i]]
codigo = max(i for i in range(int(pal["PUB"])) if ini[i] != 0) + 1
print(f"   Imagen inicial: {len(ini)} palabras; {codigo} de programa, {512 - int(pal['PUB'])} de datos y {int(pal['PUB']) - codigo} en cero entre medio.")
datos = [(i, ini[i]) for i in range(int(pal["PUB"]), 512) if ini[i] != 0]
print("   Palabras de datos distintas de cero en la imagen (dirección: valor): " + ", ".join(f"0x{4 * i:03X}: {v}" for i, v in datos))
print(f"   Palabras de la memoria que cambiaron en 20 000 ticks: {len(cambiadas)} de 512 (" + ", ".join(f"0x{4 * i:03X}" for i in cambiadas) + ")")
fuera = [i for i in cambiadas if i not in estado]
print(f"   De ellas, fuera de las 18 palabras de estado del programa: {len(fuera)}")
if not fuera and len(cambiadas) <= 18:
    print(f"PASS R2: después de 20 000 precios el programa cambió {len(cambiadas)} palabras, todas de su estado. No hay ningún arreglo que crezca con la serie")
else:
    print("FAIL R2: hay escrituras fuera del estado del programa: " + ", ".join(f"0x{4 * i:03X}" for i in fuera))
PY
t=$(grep '^Tabla distinta de 0' "$O/run.log" | grep -o '[0-9]*' | tail -1)
if [ "$t" = 0 ]; then echo "PASS R2: la tabla de 256 x 16 sigue en cero (el programa no la usa y el hardware la entrega en cero)"
else echo "FAIL R2: la tabla tiene $t entradas distintas de cero"; fi
echo "   Contenido inicial de memoria en el RTL de I1 (\$readmemh y valores por defecto de sus parámetros):"
for f in rtl/pochoco_ram.v $I/rtl/tabla_mmio.v $I/rtl/tabla_ram.v $A/rtl/espino_barrel_regfile.v; do
  echo "     $f: $(grep -c 'readmemh' "$f") \$readmemh; $(grep -E "parameter +(MemFile|TablaFile)" "$f" | sed 's/^ *//; s/,$//' | tr '\n' ' ')"
done
echo "     $I/rtl/pochoco_soc.v: $(grep -E "parameter +(MemFile|TablaFile)" $I/rtl/pochoco_soc.v | sed 's/^ *//; s/ *\/\/.*//; s/,$//' | tr '\n' ' ')"
echo "   Constantes del programa (sw/fondo.s): $(grep -cE '^\.equ' $F/sw/fondo.s) .equ, ninguna tabla. Umbrales de los gestores: $(grep -E '^\.equ G[123]_(ENTRA|SALE)' $F/sw/fondo.s | awk '{print $2 $3}' | tr '\n' ' ')"
echo
echo "R3. \"Todo hardware agregado debe estar en el repositorio con su testbench\""
fallas=0
SOC_TBS=$(grep -lE "^[[:space:]]*pochoco_soc[[:space:]]+#" $I/tb/*.sv | tr '\n' ' ')
for f in $SRC_I; do
  case $f in rtl/*) continue ;; esac
  for mod in $(grep -oE "^module +[\`A-Za-z_0-9]+" "$f" | awk '{print $2}'); do
    [ "$mod" = '`POCHOCO_SOC_MODULE' ] && mod=pochoco_soc
    [ "$mod" = '`POCHOCO_SPI_MODULE' ] && mod=pochoco_spi_slave
    if [ "$mod" = pochoco_soc ]; then tbs=$SOC_TBS
    else tbs=$(grep -lE "^[[:space:]]*$mod[[:space:]]+(#[[:space:]]*\(|[a-z_0-9]+[[:space:]]*\()" factibilidad/*/tb/*.sv factibilidad/*/tb/*.v 2>/dev/null | grep -v auditoria_hw | tr '\n' ' '); fi
    formal=$(grep -lE "top +$mod\b|-top $mod\b" factibilidad/*/formal/*.sby factibilidad/*/tools/formal.sh 2>/dev/null | tr '\n' ' ')
    if [ -n "$tbs" ]; then printf "   %-24s propio: %s%s\n" "$mod" "$tbs" "${formal:+| formal: $formal}"
    else printf "   %-24s SIN testbench que lo instancie solo. Se prueba dentro del SoC%s\n" "$mod" "${formal:+ | formal: $formal}"; fallas=$((fallas + 1)); fi
  done
done
echo "   Testbenches que instancian el SoC de I1 (y con él los módulos sin testbench propio): $SOC_TBS"
echo "   más $A/tb/tb_verif.sv (cada hilo contra el Espino base, lo usa tools/verif_rv32e.sh de la pieza) y tb/tb_proyecto_4.sv."
echo "   $(echo $SRC_I | tr ' ' '\n' | grep -vc '^rtl/') archivos agregados en la lista de fuentes de I1. De los xd_*, I1 solo instancia xd_opa; los demás"
echo "   son de otros subconjuntos de la extensión."
if [ $fallas = 0 ]; then echo "PASS R3: todos los módulos agregados tienen un testbench que los instancia solos"
else echo "AVISO R3: $fallas módulos agregados no tienen un testbench que los instancie solos (el core, el banco de registros, el decodificador,"
     echo "         la copia del esclavo SPI y xd_unit). Se prueban dentro del SoC. Si la regla exige un testbench por módulo, falta escribirlos."; fi
echo "   En el repositorio: $(git ls-files $A $D $E | wc -l) archivos de a_barrel, d_isa y e_warmboot ya están en commits. $I y $F todavía no:"
echo "   $(git ls-files $I $F | wc -l) archivos versionados. Para cumplir la regla tienen que entrar en un commit, y lo que vaya a la competencia, pasar a rtl/ y tb/."
} | tee "$M/reglas.txt"

! grep -q "^FAIL" "$M/reglas.txt"
