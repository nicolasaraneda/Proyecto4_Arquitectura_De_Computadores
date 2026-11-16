#!/usr/bin/env python3
"""autoprueba.py: firma esperada, simulación y bitstream de la autoprueba en placa.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

La autoprueba (rtl/autoprueba/autoprueba_top.v, docs/autoprueba.md) es el SoC
que compite con una maestra SPI interna: manda una caminata aleatoria de
NTICKS precios generada con un LFSR y acumula los bytes que lee en una firma
CRC-16. Este script:

  firma       Calcula la firma esperada de un peldaño de dos formas
              independientes y exige que coincidan: con el gemelo digital
              corriendo el mismo .hex con los tiempos de la maestra interna, a
              los tres períodos, y con la referencia del algoritmo
              (ref/trader.py o ref/fondo.py).
  simular     Simula autoprueba_top (RTL, Verilator) apretando cada botón y
              compara la firma de los 7 segmentos con la esperada. En R2
              además sigue en modo continuo y mira que SB_WARMBOOT no suba.
  control     Control negativo: el mismo programa con una constante cambiada
              (R0) o con otra tabla de parámetros (R1 y R2) tiene que terminar
              con LED4 (firma distinta).
  falla       Solo R2: el programa con el supervisor colgado en el tick
              FALLA_TICK. El vigilante tiene que subir BOOT con S1 S0 = 01 al
              terminar la quinta transacción sin respuesta.
  bitstream   Sintetiza, rutea y empaqueta la autoprueba del peldaño, con la
              firma esperada adentro. Informa celdas, BRAM y frecuencia máxima.
              En R2 arma además la imagen testigo, la imagen con la falla y las
              dos imágenes múltiples (icemulti), y las revisa con
              tools/ver_multi.py.
  chip        Simula el bitstream ya ruteado (icebox_vlog) con el mismo
              testbench, por los pines. En R2 también la imagen con la falla y
              la imagen testigo.
  continuo    Solo R2: el gemelo corre la misma caminata que la placa durante
              media hora a cada período y mide el peor caso de respuesta. Si
              todo precio se responde antes del siguiente, la cuenta del
              vigilante no pasa de 1 y no puede disparar (necesita 5).

Peldaños (sección 16.3 del plan): r0 es el core base con sw/trade.s
(max_media); r1 el barrel con emad, devk y la tabla, con sw/fondo.s; r2 es r1
con el vigilante y SB_WARMBOOT.

Uso, desde la raíz:
    python3 tools/autoprueba.py firma r1
    python3 tools/autoprueba.py simular r1 [--botones 3,2,1]
    python3 tools/autoprueba.py bitstream r1
    python3 tools/autoprueba.py chip r1
    python3 tools/autoprueba.py todo r2        # todas, en orden
Los productos quedan en build/autoprueba/<peldaño>/ y el informe en
docs/mediciones/autoprueba_<peldaño>.txt.
"""
import argparse
import concurrent.futures
import hashlib
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
os.environ["PATH"] = os.path.expanduser("~/herramientas/oss-cad-suite/bin") + os.pathsep + os.environ["PATH"]

import fondo     # noqa: E402
import market    # noqa: E402
import trader    # noqa: E402

NTICKS = 2000
PERIODOS = {1: 250000, 2: 25000, 3: 2500}           # ciclos de 40 ns por botón
NOMBRE_PERIODO = {1: "10 ms", 2: "1 ms", 3: "0,1 ms"}
# Tiempos de la maestra interna en el gemelo (ver el encabezado de autoprueba_top.v)
GEMELO_SPI = ["--cs-setup-ns", "1280", "--sclk-medio-ns", "640", "--cs-hold-ns", "640"]
INICIO_NS = 1_000_021        # cualquier instante después del reset; el pin cambia 1 ns después de un flanco
# En el testbench el botón se aprieta en t = 500,8 us (500 us de espera y 800 ns
# de la prueba del eco). El tick 0 parte (t = 0 en la maestra) en el segundo
# flanco de subida después: 500 860 ns.
T0_NS = 500_860
TABLA = "sw/fondo_tabla.hex"
R1_DEFS = "-DESPINO_BARREL -DESPINO_XD_EMAD -DESPINO_XD_DEVK -DESPINO_TABLA"
R2_DEFS = R1_DEFS + " -DESPINO_VIGILANTE"
GEMELO_FONDO = ["--barrel", "--xd", "3"]

PELDANOS = {
    # defs: definiciones del RTL; fuente y asm: programa y opciones del
    # ensamblador; gemelo: opciones del gemelo (sin la tabla); ref: referencia;
    # tabla: contenido de la tabla de parámetros (None si el peldaño no la
    # tiene); semilla: del LFSR (T87); continuo: modo continuo de la maestra.
    "r0": dict(defs="", fuente="sw/trade.s", asm=[], gemelo=[], ref="trader", tabla=None,
               semilla=0xACE1, continuo=0),
    "r1": dict(defs=R1_DEFS, fuente="sw/fondo.s", asm=[], gemelo=GEMELO_FONDO, ref="fondo", tabla=TABLA,
               semilla=0x3CA1, continuo=0),
    "r2": dict(defs=R2_DEFS, fuente="sw/fondo.s", asm=[], gemelo=GEMELO_FONDO, ref="fondo", tabla=TABLA,
               semilla=0x3CA1, continuo=1),
}
# Control negativo: algo que la autoprueba tiene que rechazar (LED4). Para R0,
# el umbral de la regla base en el programa. Para R1 y R2, la misma tabla con
# el umbral de entrada del gestor 1 cambiado (el programa no cambia): muestra
# que el SoC usa la tabla de la BRAM. Se eligió ese umbral porque da una firma
# distinta de la de max_media sola (7d4f), que es la que se vería con un gestor
# colgado (T88).
CONTROL = {
    "r0": dict(asm=["-D", "UMBRAL_COMPRA=-128"], texto="UMBRAL_COMPRA=-128 en sw/trade.s"),
    "r1": dict(param={"G1_ENTRA": -64}, texto="G1_ENTRA=-64 en la tabla (era -96)"),
    "r2": dict(param={"G1_ENTRA": -64}, texto="G1_ENTRA=-64 en la tabla (era -96)"),
}
FALLA_TICK = 100             # cuelgue_sup:100 en la prueba del relevo
VIG_N = 4                    # rtl/pochoco_soc.v, parámetro VigN
CONTINUO_MS = 2000           # cuánto sigue la simulación del RTL de R2 después de la firma
MEDIA_HORA_MS = 30 * 60 * 1000
FLASH = 131072               # bytes de la flash de la Go Board


def sh(cmd, log=None, **kw):
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, **kw)
    if log:
        with open(os.path.join(RAIZ, log), "w") as f:
            f.write(r.stdout + r.stderr)
    return r


# --- La secuencia y la firma, igual que autoprueba_maestra --------------------------------
def precios(n=NTICKS, semilla=0xACE1):
    """Caminata aleatoria: 128 y después pasos de +1 o -1 según el bit nuevo del LFSR."""
    lfsr, p, salida = semilla, 128, [128]
    for _ in range(n - 1):
        nuevo = ((lfsr >> 15) ^ (lfsr >> 13) ^ (lfsr >> 12) ^ (lfsr >> 10)) & 1
        lfsr = ((lfsr << 1) & 0xFFFF) | nuevo
        p = min(255, p + 1) if nuevo else max(1, p - 1)
        salida.append(p)
    return salida


def crc16(datos, crc=0xFFFF):
    """CRC-16/CCITT: polinomio 0x1021, valor inicial 0xFFFF, bit más significativo primero.
    Byte a byte da lo mismo que el cálculo bit a bit de la maestra."""
    for b in datos:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def carpeta(peldano):
    d = f"build/autoprueba/{peldano}"
    os.makedirs(os.path.join(RAIZ, d), exist_ok=True)
    return d


def ensamblar(fuente, hexfile, opciones=()):
    r = sh([sys.executable, "tools/pochoasm.py", *opciones, fuente, "-o", hexfile])
    if r.returncode != 0:
        raise SystemExit(f"FAIL: no ensambla {fuente}\n{r.stdout}{r.stderr}")


def escribir_serie(ruta, p):
    with open(os.path.join(RAIZ, ruta), "w", newline="\n") as f:
        f.write("tick,price\n")
        f.writelines(f"{i},{x}\n" for i, x in enumerate(p))


def preparar(peldano):
    """Ensambla el programa del peldaño y escribe la serie. Devuelve (hex, serie)."""
    pd = PELDANOS[peldano]
    d = carpeta(peldano)
    hexfile = f"{d}/programa.hex"
    ensamblar(pd["fuente"], hexfile, pd["asm"])
    serie = f"{d}/serie.csv"
    escribir_serie(serie, precios(semilla=pd["semilla"]))
    return hexfile, serie


def opciones_gemelo(peldano, tabla=None):
    pd = PELDANOS[peldano]
    tabla = tabla or pd["tabla"]
    return pd["gemelo"] + (["--tabla", tabla] if tabla else [])


def leer_firma(peldano):
    return int(open(os.path.join(RAIZ, f"{carpeta(peldano)}/firma.txt")).read(), 16)


def firma(peldano, informe):
    hexfile, serie = preparar(peldano)
    pd = PELDANOS[peldano]
    d = carpeta(peldano)
    # Se compila aparte y se reemplaza de una vez: otra corrida (de otro
    # peldaño) puede estar usando build/gemelo en este momento
    tmp = f"build/gemelo.{os.getpid()}"
    r = sh(["cc", "-O2", "-o", tmp, "ref/gemelo/gemelo.c"])
    if r.returncode != 0:
        raise SystemExit("FAIL: el gemelo no compila")
    os.replace(os.path.join(RAIZ, tmp), os.path.join(RAIZ, "build/gemelo"))
    firmas = {}
    for boton, ciclos in PERIODOS.items():
        csv = f"{d}/gemelo_{boton}.csv"
        r = sh(["build/gemelo", *opciones_gemelo(peldano), "--hex", hexfile, "--serie", serie,
                "--periodo-ns", str(40 * ciclos), "--inicio-ns", str(INICIO_NS), *GEMELO_SPI, "--csv", csv],
               log=f"{d}/gemelo_{boton}.log")
        if "Testbenchs aprobados: 4/4" not in r.stdout:
            raise SystemExit(f"FAIL: el gemelo no entrega 4/4 a {NOMBRE_PERIODO[boton]} (ver {d}/gemelo_{boton}.log)")
        leidos = [int(x.split(",")[2], 16) for x in open(os.path.join(RAIZ, csv)).read().splitlines()[1:]]
        peor = re.search(r"Peor caso precio->decision: (\d+) ciclos \(disponibles: (\d+)\)", r.stdout)
        firmas[boton] = (crc16(leidos), leidos, peor.group(1), peor.group(2))
    p = precios(semilla=pd["semilla"])
    estrategia = fondo.Fondo() if pd["ref"] == "fondo" else trader.Oficial()
    esperados = trader.decisiones(p, estrategia, 0)
    f_ref = crc16(esperados)
    m = market.simular(p, esperados)
    informe.append(f"Serie: caminata aleatoria del LFSR con semilla 0x{pd['semilla']:04X}, {NTICKS} precios, "
                   f"entre {min(p)} y {max(p)}, sha256 {hashlib.sha256(bytes(p)).hexdigest()[:16]}...")
    informe.append(f"Referencia ref/{pd['ref']}.py: firma {f_ref:04x}, {sum(a != b for a, b in zip(esperados, esperados[1:]))} "
                   f"cambios de byte, patrimonio {m.w} con {m.ordenes} ordenes")
    if pd["ref"] == "fondo":
        # Qué tan distinta es la firma de la que daría el supervisor solo (max_media)
        mm = trader.decisiones(p, trader.Oficial(), 0)
        informe.append(f"     max_media sola (el supervisor sin votos) daria {crc16(mm):04x}: "
                       f"{sum(a != b for a, b in zip(mm, esperados))} bytes distintos")
        for k in (1, 2, 3):
            colgado = trader.decisiones(p, fondo.Fondo(fallas=[fondo.Falla(k)]), 0)
            informe.append(f"     con el gestor {k} colgado desde el tick 1 daria {crc16(colgado):04x}: "
                           f"{sum(a != b for a, b in zip(colgado, esperados))} bytes distintos")
    ok = True
    for boton, (f, leidos, peor, disp) in firmas.items():
        igual = leidos == esperados
        ok &= igual and f == f_ref
        informe.append(f"{'PASS' if igual and f == f_ref else 'FAIL'} gemelo con SW{boton} ({NOMBRE_PERIODO[boton]}): "
                       f"firma {f:04x}, bytes {'identicos' if igual else 'DISTINTOS'} a la referencia, "
                       f"peor caso {peor} de {disp} ciclos")
    if not ok:
        raise SystemExit("\n".join(informe) + "\nFAIL: la firma no es la misma en las dos formas de calcularla")
    with open(os.path.join(RAIZ, f"{d}/firma.txt"), "w") as fh:
        fh.write(f"{f_ref:04x}\n")
    return f_ref


def fuentes_soc():
    rtl = sorted(f"rtl/{f}" for f in os.listdir(os.path.join(RAIZ, "rtl")) if f.endswith(".v"))
    core = sorted(f"rtl/espino_core/{f}" for f in os.listdir(os.path.join(RAIZ, "rtl/espino_core")) if f.endswith(".v"))
    return rtl + core + ["rtl/autoprueba/autoprueba_top.v"]


def celdas_sim():
    return subprocess.check_output(["yosys-config", "--datdir"], text=True).strip() + "/ice40/cells_sim.v"


def es_r2(peldano):
    return "-DESPINO_VIGILANTE" in PELDANOS[peldano]["defs"].split()


def compilar_rtl(peldano, hexfile, obj, tabla=None):
    """Compila tb_autoprueba con el RTL del peldaño. Devuelve la ruta del ejecutable."""
    pd = PELDANOS[peldano]
    d = carpeta(peldano)
    esperada = leer_firma(peldano)
    vig = ["-DVIGILANTE"] if es_r2(peldano) else []
    r = sh(["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module", "tb_autoprueba",
            "-DNO_ICE40_DEFAULT_ASSIGNMENTS", *pd["defs"].split(), *vig, f'-GPROGRAMA="{hexfile}"',
            f'-GTABLA="{tabla or pd["tabla"] or TABLA}"', f"-GCONT={pd['continuo']}", f"-GSEM=16'h{pd['semilla']:04x}",
            f"-GFIRMA_P=16'h{esperada:04x}", "-O3", "--Mdir", f"{d}/{obj}", "-o", "sim",
            celdas_sim(), *fuentes_soc(), "tb/autoprueba/tb_autoprueba.sv"], log=f"{d}/verilator_{obj}.log")
    if r.returncode != 0:
        raise SystemExit(f"FAIL: Verilator no compila la autoprueba (ver {d}/verilator_{obj}.log)")
    return f"{d}/{obj}/sim"


def correr(ejecutable, log, *plusargs):
    r = sh([ejecutable, *plusargs], log=log)
    lineas = r.stdout.splitlines()

    def una(prefijo):
        x = [l for l in lineas if l.startswith(prefijo)]
        return x[0] if x else None
    return {k: una(k) for k in ("RESULTADO", "PINES", "CONTINUO", "WARMBOOT")}, r.stdout


def en_paralelo(tareas):
    """tareas: lista de (clave, función, argumentos). Devuelve {clave: resultado}."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(tareas))) as ex:
        futuros = {k: ex.submit(f, *a) for k, f, a in tareas}
        return {k: fu.result() for k, fu in futuros.items()}


def simular(peldano, informe, botones):
    d = carpeta(peldano)
    esperada = leer_firma(peldano)
    sim = compilar_rtl(peldano, f"{d}/programa.hex", "obj")
    r2 = es_r2(peldano)
    extra = [f"+CONTINUO_MS={CONTINUO_MS}"] if PELDANOS[peldano]["continuo"] else []
    res = en_paralelo([(b, correr, (sim, f"{d}/sim_{b}.log", f"+BOTON={b}", f"+FIRMA={esperada:04x}", *extra))
                       for b in botones])
    ok = True
    for b in botones:
        lin, salida = res[b]
        resl = lin["RESULTADO"] or "RESULTADO sin salida: " + salida[-200:]
        bien = resl.endswith("PASS") and bool(lin["PINES"]) and lin["PINES"].endswith("PASS")
        if extra:
            bien &= bool(lin["CONTINUO"]) and lin["CONTINUO"].endswith("PASS")
        if r2:
            bien &= lin["WARMBOOT"] == "WARMBOOT nunca"
        ok &= bien
        informe.append(f"{'PASS' if bien else 'FAIL'} RTL con SW{b} ({NOMBRE_PERIODO[b]}): {resl}")
        if extra:
            informe.append(f"     {lin['CONTINUO']}")
        if r2:
            informe.append(f"     {lin['WARMBOOT']}: SB_WARMBOOT no se dispara en toda la corrida")
    return ok


def tabla_control(peldano):
    """Escribe la tabla del control negativo. Devuelve su ruta."""
    ruta = f"{carpeta(peldano)}/control_tabla.hex"
    with open(os.path.join(RAIZ, ruta), "w", newline="\n") as f:
        f.write(fondo.tabla_hex(CONTROL[peldano]["param"]))
    return ruta


def control(peldano, informe):
    """La autoprueba con un programa o una tabla alterados debe terminar en LED4, no en LED3."""
    pd, c = PELDANOS[peldano], CONTROL[peldano]
    d = carpeta(peldano)
    esperada = leer_firma(peldano)
    hexfile, tabla = f"{d}/programa.hex", None
    if "asm" in c:
        hexfile = f"{d}/control.hex"
        ensamblar(pd["fuente"], hexfile, pd["asm"] + c["asm"])
    else:
        tabla = tabla_control(peldano)
    r = sh(["build/gemelo", *opciones_gemelo(peldano, tabla), "--hex", hexfile, "--serie", f"{d}/serie.csv",
            "--periodo-ns", "100000", "--inicio-ns", str(INICIO_NS), *GEMELO_SPI, "--csv", f"{d}/control.csv"])
    leidos = [int(x.split(",")[2], 16) for x in open(os.path.join(RAIZ, f"{d}/control.csv")).read().splitlines()[1:]]
    f_control = crc16(leidos)
    nota = ""
    if tabla:
        p = precios(semilla=pd["semilla"])
        ref = trader.decisiones(p, fondo.Fondo(c["param"]), 0)
        nota = (f"; ref/fondo.py con ese parametro da {crc16(ref):04x}"
                f"{'' if ref == leidos else ' (DISTINTO del gemelo)'}")
        if ref != leidos:
            f_control = -1
    sim = compilar_rtl(peldano, hexfile, "obj_control", tabla)
    lin, _ = correr(sim, f"{d}/control_3.log", "+BOTON=3", f"+FIRMA={esperada:04x}")
    res = lin["RESULTADO"] or "sin salida"
    ok = (res.endswith("FAIL") and "LED=1010" in res and f_control >= 0 and f"firma={f_control:04x}" in res
          and f_control != esperada)
    informe.append(f"{'PASS' if ok else 'FAIL'} control negativo ({c['texto']}): el gemelo da "
                   f"{f_control:04x}{nota}, y la autoprueba lo rechaza con LED4: {res}")
    return ok


def programa_falla(peldano):
    d = carpeta(peldano)
    r = sh([sys.executable, "tools/fondo/variante.py", f"cuelgue_sup:{FALLA_TICK}", "-o", f"{d}/falla.s"])
    if r.returncode != 0:
        raise SystemExit(f"FAIL: variante.py\n{r.stdout}{r.stderr}")
    ensamblar(f"{d}/falla.s", f"{d}/falla.hex")
    return f"{d}/falla.hex"


def revisar_disparo(linea, boton):
    """Del WARMBOOT t_ns=... s1s0=.. del testbench: (ok, texto)."""
    m = re.search(r"WARMBOOT t_ns=(\d+) s1s0=(\d\d)", linea or "")
    if not m:
        return False, f"BOOT no subio ({linea})"
    t, s1s0 = int(m.group(1)), m.group(2)
    periodo = 40 * PERIODOS[boton]
    n, desfase = divmod(t - T0_NS, periodo)
    # La transacción nf = FALLA_TICK - 1 (la placa no pierde precios) trae el
    # precio que cuelga al supervisor; es la primera sin respuesta. La número
    # VIG_N + 1 es nf + VIG_N. CS_n sube 305 ciclos después del comienzo del
    # tick (12 200 ns) y BOOT tres flancos después: el primero que ve CS_n en
    # alto carga el sincronizador, el segundo lo pasa a cs_active y en el
    # tercero el vigilante sube BOOT (12 320 ns).
    nb = FALLA_TICK - 1 + VIG_N
    ok = s1s0 == "01" and n == nb and desfase == 40 * (305 + 3)
    return ok, (f"BOOT sube en t = {t} ns con S1 S0 = {s1s0}: transaccion {n} (se esperaba {nb} = "
                f"{FALLA_TICK - 1} + {VIG_N}), {desfase} ns despues del comienzo del tick, cuando CS_n "
                f"ya subio (12 200 ns) y antes de la transaccion siguiente")


def falla(peldano, informe, botones):
    if not es_r2(peldano):
        return True
    d = carpeta(peldano)
    esperada = leer_firma(peldano)
    sim = compilar_rtl(peldano, programa_falla(peldano), "obj_falla")
    # Basta con simular hasta un poco después del disparo
    limite = {b: max(2, (FALLA_TICK + 20) * 40 * PERIODOS[b] // 1_000_000) for b in botones}
    res = en_paralelo([(b, correr, (sim, f"{d}/falla_{b}.log", f"+BOTON={b}", f"+FIRMA={esperada:04x}",
                                    f"+LIMITE_MS={limite[b]}")) for b in botones])
    ok = True
    for b in botones:
        bien, texto = revisar_disparo(res[b][0]["WARMBOOT"], b)
        ok &= bien
        informe.append(f"{'PASS' if bien else 'FAIL'} RTL con el supervisor colgado en el tick {FALLA_TICK}, "
                       f"SW{b} ({NOMBRE_PERIODO[b]}): {texto}")
    return ok


# --- Bitstreams -----------------------------------------------------------------------------
def pnr(nombre, d, lectura, chparam, top):
    """yosys, nextpnr e icepack. Devuelve (ok, celdas, bram, fmax, sha256) o lanza SystemExit."""
    r = sh(["yosys", "-q", "-l", f"{d}/{nombre}.yosys.log", "-p",
            f"{lectura}; {chparam}; synth_ice40 -top {top} -json {d}/{nombre}.json"])
    if r.returncode != 0:
        raise SystemExit(f"FAIL: yosys (ver {d}/{nombre}.yosys.log)")
    r = sh(["nextpnr-ice40", "--hx1k", "--package", "vq100", "--freq", "25", "--json", f"{d}/{nombre}.json",
            "--pcf", "goboard.pcf", "--asc", f"{d}/{nombre}.asc", "-l", f"{d}/{nombre}.nextpnr.log", "-q"])
    log = open(os.path.join(RAIZ, f"{d}/{nombre}.nextpnr.log")).read()
    if r.returncode != 0:
        return False, (re.findall(r"ERROR:.*", log) or ["ver el log"])[0], None, None, None
    lc = re.findall(r"ICESTORM_LC:\s+(\d+)/\s*(\d+)", log)[-1]
    ram = re.findall(r"ICESTORM_RAM:\s+(\d+)/\s*(\d+)", log)[-1]
    fmax = re.findall(r"Max frequency for clock '[^']*': ([\d.]+) MHz", log)
    sh(["icepack", f"{d}/{nombre}.asc", f"{d}/{nombre}.bin"])
    h = hashlib.sha256(open(os.path.join(RAIZ, f"{d}/{nombre}.bin"), "rb").read()).hexdigest()
    return True, f"{lc[0]} de {lc[1]}", f"{ram[0]} de {ram[1]}", (fmax[-1] if fmax else None), h


def chparam_autoprueba(peldano, hexfile, esperada):
    pd = PELDANOS[peldano]
    return (f'chparam -set MemFile "{hexfile}" -set TablaFile "{pd["tabla"] or TABLA}" '
            f"-set CONTINUO {pd['continuo']} -set SEMILLA {pd['semilla']} -set FIRMA_ESPERADA {esperada} autoprueba_top")


def bitstream(peldano, informe):
    pd = PELDANOS[peldano]
    d = carpeta(peldano)
    esperada = leer_firma(peldano)
    lectura = f"read_verilog {pd['defs']} {' '.join(fuentes_soc())}"
    trabajos = [("principal", pnr, (f"autoprueba_{peldano}", d, lectura,
                                    chparam_autoprueba(peldano, f"{d}/programa.hex", esperada), "autoprueba_top"))]
    if es_r2(peldano):
        hex_falla = programa_falla(peldano)
        trabajos.append(("falla", pnr, (f"falla_{peldano}", d, lectura,
                                        chparam_autoprueba(peldano, hex_falla, esperada), "autoprueba_top")))
        trabajos.append(("testigo", pnr, ("testigo", d, "read_verilog rtl/autoprueba/testigo_top.v", "", "testigo_top")))
    res = en_paralelo(trabajos)
    ok = True
    etiquetas = {"principal": f"autoprueba_{peldano}", "falla": f"falla_{peldano} (imagen 0 de la prueba del relevo)",
                 "testigo": "testigo (imagen 1 de las dos imagenes multiples)"}
    for k, (bien, lc, ram, fmax, h) in res.items():
        if not bien:
            informe.append(f"FAIL nextpnr {etiquetas[k]}: {lc}")
            ok = False
            continue
        bien = fmax is not None and float(fmax) >= 25.0
        ok &= bien
        adentro = f", firma esperada {esperada:04x} adentro" if k != "testigo" else ""
        informe.append(f"{'PASS' if bien else 'FAIL'} bitstream {d}/{etiquetas[k].split()[0]}.bin: {lc} celdas, "
                       f"{ram} BRAM, frecuencia maxima {fmax} MHz{adentro}")
        informe.append(f"     sha256 {h}")
    if es_r2(peldano) and ok:
        ok &= multi(peldano, informe)
    return ok


def multi(peldano, informe):
    """Las dos imágenes múltiples de R2 (icemulti -p0) y su revisión."""
    d = carpeta(peldano)
    # La prueba del relevo también sin la orden de dormir la flash (icepack -s),
    # por si el warm boot no la despierta (docs/autoprueba.md, sección 8)
    for n in (f"falla_{peldano}", "testigo"):
        sh(["icepack", "-s", f"{d}/{n}.asc", f"{d}/{n}_sin_dormir.bin"])
    archivos = {
        f"autoprueba_{peldano}_multi": [f"autoprueba_{peldano}.bin", "testigo.bin"],
        f"relevo_{peldano}_multi": [f"falla_{peldano}.bin", "testigo.bin"],
        f"relevo_{peldano}_multi_sin_dormir": [f"falla_{peldano}_sin_dormir.bin", "testigo_sin_dormir.bin"],
    }
    ok = True
    for nombre, imagenes in archivos.items():
        rutas = [f"{d}/{x}" for x in imagenes]
        r = sh(["icemulti", "-p0", "-o", f"{d}/{nombre}.bin", *rutas], log=f"{d}/{nombre}.icemulti.log")
        v = sh([sys.executable, "tools/ver_multi.py", "--flash", str(FLASH), f"{d}/{nombre}.bin", *rutas])
        bien = r.returncode == 0 and v.returncode == 0
        ok &= bien
        h = hashlib.sha256(open(os.path.join(RAIZ, f"{d}/{nombre}.bin"), "rb").read()).hexdigest() if bien else "-"
        informe.append(f"{'PASS' if bien else 'FAIL'} imagen multiple {d}/{nombre}.bin: imagen 0 {imagenes[0]}, "
                       f"imagen 1 {imagenes[1]} (icemulti -p0, tools/ver_multi.py)")
        informe.extend("       " + x for x in v.stdout.strip().splitlines())
        informe.append(f"     sha256 {h}")
    return ok


def compilar_chip(d, asc, nombre, tb, top, vig=False):
    sh([sys.executable, "tools/chip_vlog.py", asc, "goboard.pcf", "-o", f"{d}/{nombre}.v"])
    r = sh(["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module", top,
            "-DCHIP", *(["-DVIGILANTE"] if vig else []), "-DNO_ICE40_DEFAULT_ASSIGNMENTS", "-O3",
            "--Mdir", f"{d}/obj_{nombre}", "-o", "sim", celdas_sim(), f"{d}/{nombre}.v", tb],
           log=f"{d}/verilator_{nombre}.log")
    return f"{d}/obj_{nombre}/sim" if r.returncode == 0 else None


def chip(peldano, informe, botones):
    d = carpeta(peldano)
    esperada = leer_firma(peldano)
    r2 = es_r2(peldano)
    extra = [f"+CONTINUO_MS={CONTINUO_MS}"] if PELDANOS[peldano]["continuo"] else []
    sim = compilar_chip(d, f"{d}/autoprueba_{peldano}.asc", "chip", "tb/autoprueba/tb_autoprueba.sv",
                        "tb_autoprueba", r2)
    if not sim:
        informe.append(f"FAIL Verilator no compila el bitstream ruteado (ver {d}/verilator_chip.log)")
        return False
    tareas = [(("normal", b), correr, (sim, f"{d}/chip_{b}.log", f"+BOTON={b}", f"+FIRMA={esperada:04x}", *extra))
              for b in botones]
    if r2:
        sim_f = compilar_chip(d, f"{d}/falla_{peldano}.asc", "chip_falla", "tb/autoprueba/tb_autoprueba.sv",
                              "tb_autoprueba", True)
        sim_t = compilar_chip(d, f"{d}/testigo.asc", "chip_testigo", "tb/autoprueba/tb_testigo.sv", "tb_testigo")
        if not sim_f or not sim_t:
            informe.append(f"FAIL Verilator no compila la imagen con la falla o la testigo (ver {d}/verilator_chip_*.log)")
            return False
        limite = max(2, (FALLA_TICK + 20) * 40 * PERIODOS[3] // 1_000_000)
        tareas.append((("falla", 3), correr, (sim_f, f"{d}/chip_falla_3.log", "+BOTON=3", f"+FIRMA={esperada:04x}",
                                               f"+LIMITE_MS={limite}")))
        tareas.append((("testigo", 0), sh, ([sim_t], f"{d}/chip_testigo.log")))
    res = en_paralelo(tareas)
    ok = True
    for b in botones:
        lin, salida = res[("normal", b)]
        resl = lin["RESULTADO"] or "RESULTADO sin salida: " + salida[-200:]
        bien = resl.endswith("PASS") and bool(lin["PINES"]) and lin["PINES"].endswith("PASS")
        if extra:
            bien &= bool(lin["CONTINUO"]) and lin["CONTINUO"].endswith("PASS")
        if r2:
            bien &= lin["WARMBOOT"] == "WARMBOOT nunca"
        ok &= bien
        informe.append(f"{'PASS' if bien else 'FAIL'} bitstream ruteado con SW{b} ({NOMBRE_PERIODO[b]}): {resl}")
        if extra:
            informe.append(f"     {lin['CONTINUO']}")
        if r2:
            informe.append(f"     {lin['WARMBOOT']}: SB_WARMBOOT no se dispara")
    if r2:
        bien, texto = revisar_disparo(res[("falla", 3)][0]["WARMBOOT"], 3)
        ok &= bien
        informe.append(f"{'PASS' if bien else 'FAIL'} bitstream ruteado de la imagen con el supervisor colgado, SW3: {texto}")
        salida = res[("testigo", 0)].stdout
        bien = "RESULTADO testigo PASS" in salida
        ok &= bien
        informe.append(f"{'PASS' if bien else 'FAIL'} bitstream ruteado de la imagen testigo: "
                       + "; ".join(x[5:] for x in salida.splitlines() if x.startswith("PASS ") or x.startswith("FAIL ")))
    return ok


def testigo_rtl(peldano, informe):
    """La imagen testigo en RTL, con el minuto acortado."""
    if not es_r2(peldano):
        return True
    d = carpeta(peldano)
    r = sh(["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module", "tb_testigo",
            "-O3", "--Mdir", f"{d}/obj_testigo", "-o", "sim", "rtl/autoprueba/testigo_top.v",
            "tb/autoprueba/tb_testigo.sv"], log=f"{d}/verilator_testigo.log")
    if r.returncode != 0:
        informe.append(f"FAIL Verilator no compila la testigo (ver {d}/verilator_testigo.log)")
        return False
    salida = sh([f"{d}/obj_testigo/sim"], log=f"{d}/testigo_rtl.log").stdout
    ok = "RESULTADO testigo PASS" in salida
    informe.append(f"{'PASS' if ok else 'FAIL'} RTL de la imagen testigo (minuto de 1000 ciclos): "
                   + "; ".join(x[5:] for x in salida.splitlines() if x.startswith("PASS ") or x.startswith("FAIL ")))
    return ok


def escribir_caminata(ruta, n, semilla):
    """Como precios(), pero escribe la serie a medida que la genera. Devuelve (mínimo, máximo)."""
    lfsr, p, lo, hi = semilla, 128, 128, 128
    with open(os.path.join(RAIZ, ruta), "w", newline="\n") as f:
        f.write("tick,price\n0,128\n")
        for i in range(1, n):
            nuevo = ((lfsr >> 15) ^ (lfsr >> 13) ^ (lfsr >> 12) ^ (lfsr >> 10)) & 1
            lfsr = ((lfsr << 1) & 0xFFFF) | nuevo
            p = min(255, p + 1) if nuevo else max(1, p - 1)
            lo, hi = min(lo, p), max(hi, p)
            f.write(f"{i},{p}\n")
    return lo, hi


def continuo(peldano, informe):
    """Media hora de la caminata en el gemelo, a cada período: peor caso de respuesta."""
    if not PELDANOS[peldano]["continuo"]:
        return True
    pd = PELDANOS[peldano]
    d = carpeta(peldano)
    ok = True
    tareas, rangos = [], {}
    for boton, ciclos in PERIODOS.items():
        n = MEDIA_HORA_MS * 25_000 // ciclos
        rangos[boton] = (n, *escribir_caminata(f"{d}/media_hora_{boton}.csv", n, pd["semilla"]))
        tareas.append((boton, sh, (["build/gemelo", *opciones_gemelo(peldano), "--hex", f"{d}/programa.hex",
                                    "--serie", f"{d}/media_hora_{boton}.csv", "--periodo-ns", str(40 * ciclos),
                                    "--inicio-ns", str(INICIO_NS), *GEMELO_SPI], f"{d}/media_hora_{boton}.log")))
    res = en_paralelo(tareas)
    for boton in PERIODOS:
        n, lo, hi = rangos[boton]
        salida = res[boton].stdout
        peor = re.search(r"Peor caso precio->decision: (\d+) ciclos \(disponibles: (\d+)\)", salida)
        bien = bool(peor) and int(peor.group(1)) < int(peor.group(2))
        ok &= bien
        informe.append(f"{'PASS' if bien else 'FAIL'} gemelo, media hora con SW{boton} ({NOMBRE_PERIODO[boton]}): "
                       f"{n} precios (entre {lo} y {hi}), peor caso precio->decision "
                       f"{peor.group(1) if peor else '?'} de {peor.group(2) if peor else '?'} ciclos")
        os.remove(os.path.join(RAIZ, f"{d}/media_hora_{boton}.csv"))
    if ok:
        informe.append("     Todo precio se responde antes de que llegue el siguiente: la cuenta del vigilante "
                       f"vuelve a 0 en cada tick y no llega a {VIG_N + 1}")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("accion", choices=("firma", "simular", "control", "falla", "bitstream", "chip", "continuo", "todo"))
    ap.add_argument("peldano", choices=sorted(PELDANOS))
    ap.add_argument("--botones", default="3,2,1", help="botones a simular (3 es el período más corto)")
    ap.add_argument("--botones-chip", default="3", help="botones a simular con el bitstream ruteado")
    a = ap.parse_args(argv)
    os.chdir(RAIZ)
    botones = [int(x) for x in a.botones.split(",")]
    informe = []
    ok = True
    todo = a.accion == "todo"
    if a.accion == "firma" or todo:
        firma(a.peldano, informe)
    if a.accion == "bitstream" or todo:
        ok &= bitstream(a.peldano, informe)
    if a.accion == "simular" or todo:
        ok &= simular(a.peldano, informe, botones)
        ok &= testigo_rtl(a.peldano, informe)
    if a.accion == "control" or todo:
        ok &= control(a.peldano, informe)
    if a.accion == "falla" or todo:
        ok &= falla(a.peldano, informe, botones)
    if a.accion == "chip" or todo:
        ok &= chip(a.peldano, informe, [int(x) for x in a.botones_chip.split(",")])
    if a.accion == "continuo" or todo:
        ok &= continuo(a.peldano, informe)
    commit = sh(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    texto = "\n".join([f"Autoprueba del peldano {a.peldano} ({a.accion}), commit {commit}",
                       f"Generado por tools/autoprueba.py {a.accion} {a.peldano}. No editar a mano.", ""] + informe +
                      ["", "PASS" if ok else "FAIL"]) + "\n"
    print(texto, end="")
    if todo:
        with open(os.path.join(RAIZ, f"docs/mediciones/autoprueba_{a.peldano}.txt"), "w") as f:
            f.write(texto)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
