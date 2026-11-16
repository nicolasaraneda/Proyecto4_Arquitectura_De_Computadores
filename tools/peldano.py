#!/usr/bin/env python3
"""peldano.py: el diseño por defecto del repositorio es el del peldaño que compite.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El comando del encabezado de tb/tb_proyecto_4.sv ensambla sw/trade.s y compila
rtl/*.v y rtl/espino_core/*.v sin ninguna definición. Hoy eso da R0: el Espino
base con `max_media`. Si compite R1 o R2, el profesor tiene que poder correr
ese mismo comando, sin cambiar nada, y obtener el diseño que compite con 4/4.

  oficial          Corre el comando del encabezado tal cual, en una copia del
                   árbol de trabajo, y compara decisiones.csv con la referencia
                   del peldaño que hoy es el de por defecto (ref/trader.py si no
                   hay rtl/00_peldano.v, ref/fondo.py si lo hay). No cambia
                   nada. Corre en la integración continua.
  fijar r1|r2      Hace el cambio, en este árbol de trabajo:
                     1. rtl/00_peldano.v con las definiciones del peldaño. El
                        comando oficial lo compila primero (rtl/*.v en orden
                        alfabético) y las definiciones valen para el resto de
                        los archivos. Ningún flujo propio lo ve: todos arman su
                        lista de fuentes sin los rtl/00_* y eligen la variante
                        con sus propias definiciones, como hasta ahora.
                     2. El programa de R0 pasa a sw/max_media.s (git mv) y todas
                        las referencias a sw/trade.s y sw/trade.hex en el
                        Makefile, la integración continua, tools/, ref/, tb/ y
                        formal/ (salvo tb/tb_proyecto_4.sv, que no se toca, y
                        los programas de sw/, que quedan byte por byte) pasan a
                        sw/max_media.s y sw/max_media.hex. R0 sigue siendo R0
                        para todos los flujos.
                     3. sw/trade.s pasa a ser una copia exacta de sw/fondo.s, y
                        sw/trade.hex su ensamblado.
                     4. Corre `oficial`: 4/4 y decisiones.csv igual al de
                        ref/fondo.py.
                   No hace commit. Lo revisa y lo sube Nicolás.
  probar r1|r2     Hace `fijar` en una copia del repositorio (git worktree en
                   build/peldano/), sin tocar este árbol, y corre ahí `oficial`
                   y la lista de pruebas de --pruebas. Así se sabe hoy que el
                   cambio funciona.

Uso:
    python3 tools/peldano.py oficial                 # make peldano-oficial
    python3 tools/peldano.py probar r1               # make peldano-probar PELDANO=r1
    python3 tools/peldano.py fijar r1                # make peldano-fijar PELDANO=r1 (después del 26/11)
Para deshacer `fijar` antes del commit: git checkout -- . && git clean -fd rtl/ sw/
"""
import argparse
import filecmp
import os
import re
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFINICIONES = {
    "r1": ["ESPINO_BARREL", "ESPINO_XD_EMAD", "ESPINO_XD_DEVK", "ESPINO_TABLA"],
    "r2": ["ESPINO_BARREL", "ESPINO_XD_EMAD", "ESPINO_XD_DEVK", "ESPINO_TABLA", "ESPINO_VIGILANTE"],
}
PELDANO_V = "rtl/00_peldano.v"
# Dónde se reemplazan las referencias al programa de R0 (paso 2 de fijar)
CARPETAS = ["tools", "ref", "tb", "formal"]      # sw/ no: los programas no se tocan
ARCHIVOS = ["Makefile", ".github/workflows/ci.yml"]
NO_TOCAR = {"tb/tb_proyecto_4.sv", "tools/peldano.py"}
EXTENSIONES = (".py", ".sh", ".sv", ".v", ".c", ".s", ".mk", ".yml", ".txt", ".sby", ".ys")
# sw/trade.s o sw/trade.hex que no sea parte de otra ruta ($D/sw/trade.hex, base/sw/...)
PATRON = re.compile(r"(?<![\w/$.-])sw/trade\.(s|hex)\b")
# Rutas armadas por partes, que el patrón no ve (se comprueba con make peldano-probar)
POR_PARTES = [('"sw", "trade.hex"', '"sw", "max_media.hex"'), ('"sw", "trade.s"', '"sw", "max_media.s"')]
# Pruebas que corre `probar` después de fijar (rápidas; la integración continua corre todo)
PRUEBAS = ["test-ref", "tb", "equiv-gemelo", "fondo-oficial", "retune-control", "check-tabla", "test-fondo"]


def sh(cmd, cwd=RAIZ, **kw):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=isinstance(cmd, str), **kw)


def oficial(raiz=RAIZ):
    """El comando del encabezado de tb/tb_proyecto_4.sv, tal cual, en una copia."""
    peldano = None
    pv = os.path.join(raiz, PELDANO_V)
    if os.path.exists(pv):
        m = re.search(r"Peldaño: (r\d)", open(pv).read())
        peldano = m.group(1) if m else "?"
    with tempfile.TemporaryDirectory() as tmp:
        copia = os.path.join(tmp, "repo")
        # Copia del árbol de trabajo (con lo que no esté en commit), sin build/
        shutil.copytree(raiz, copia, ignore=shutil.ignore_patterns("build", ".git", "__pycache__"))
        cmds = ["python3 tools/pochoasm.py sw/trade.s -o sw/trade.hex",
                f"iverilog -g2012 -s tb_proyecto_4 -o {tmp}/tb_p4 $(yosys-config --datdir)/ice40/cells_sim.v "
                "rtl/*.v rtl/espino_core/*.v tb/tb_proyecto_4.sv",
                f"vvp -n {tmp}/tb_p4"]
        salida = []
        for c in cmds:
            r = sh(c, cwd=copia)
            salida.append(f"$ {c}\n{r.stdout}{r.stderr}")
            if r.returncode != 0:
                return False, "\n".join(salida) + f"\nFAIL: el comando termino con codigo {r.returncode}"
        log = r.stdout
        ok = "Testbenchs aprobados: 4/4" in log
        ref = "ref/fondo.py" if peldano else "ref/trader.py"
        r = sh(f"python3 {ref} tb/practica.csv --nticks 2000 --periodo-ns 100000 -o {tmp}/ref.csv", cwd=copia)
        igual = r.returncode == 0 and filecmp.cmp(os.path.join(copia, "decisiones.csv"), f"{tmp}/ref.csv", shallow=False)
        lineas = [l for l in log.splitlines() if l.startswith(("Patrimonio", "Peor caso", "PASS", "FAIL", "Testbenchs"))]
        diseno = f"{peldano.upper()} (rtl/00_peldano.v)" if peldano else "R0 (sin rtl/00_peldano.v: Espino base y sw/trade.s)"
        texto = [f"Diseno por defecto: {diseno}", "Comando del encabezado de tb/tb_proyecto_4.sv, sin definiciones:"]
        texto += [f"  {l}" for l in lineas]
        texto.append(f"  decisiones.csv {'identico' if igual else 'DISTINTO'} al de {ref}")
        texto.append(f"{'PASS' if ok and igual else 'FAIL'}: el comando oficial da {'4/4' if ok else 'menos de 4/4'} "
                     f"con el diseno por defecto")
        return ok and igual, "\n".join(texto)


def fijar(peldano, raiz=RAIZ):
    if os.path.exists(os.path.join(raiz, PELDANO_V)):
        raise SystemExit(f"FAIL: ya existe {PELDANO_V}. Para volver atras: git checkout -- . && git clean -fd rtl/ sw/")
    if os.path.exists(os.path.join(raiz, "sw/max_media.s")):
        raise SystemExit("FAIL: ya existe sw/max_media.s")
    defs = DEFINICIONES[peldano]
    # 1. Definiciones del peldaño
    with open(os.path.join(raiz, PELDANO_V), "w", newline="\n") as f:
        f.write("// 00_peldano.v: definiciones del diseño por defecto del repositorio.\n//\n"
                "// Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.\n"
                "// Arquitectura de Computadores, Universidad de los Andes, 2026-2.\n//\n"
                f"// Peldaño: {peldano} (generado por tools/peldano.py fijar {peldano}; no editar a mano).\n//\n"
                "// El comando del encabezado de tb/tb_proyecto_4.sv compila rtl/*.v en orden\n"
                "// alfabético, así que este archivo va primero y sus definiciones valen para\n"
                "// pochoco_soc.v y el resto: sin ninguna opción, el testbench oficial ejercita\n"
                "// el diseño que compite. Los flujos propios del repositorio no lo leen\n"
                "// (excluyen rtl/00_*) y eligen la variante con sus propias definiciones.\n"
                "// No contiene lógica.\n\n")
        for d in defs:
            f.write(f"`define {d}\n")
    # 2. El programa de R0 pasa a sw/max_media.s
    r = sh(["git", "mv", "sw/trade.s", "sw/max_media.s"], cwd=raiz)
    if r.returncode != 0:
        raise SystemExit(f"FAIL: git mv: {r.stderr}")
    if os.path.exists(os.path.join(raiz, "sw/trade.hex")):
        sh(["git", "mv", "sw/trade.hex", "sw/max_media.hex"], cwd=raiz)
    cambiados = []
    rutas = [os.path.join(raiz, a) for a in ARCHIVOS]
    for c in CARPETAS:
        for base, _, archivos in os.walk(os.path.join(raiz, c)):
            if "__pycache__" in base:
                continue
            rutas += [os.path.join(base, a) for a in archivos if a.endswith(EXTENSIONES) or a == "Makefile"]
    for ruta in rutas:
        rel = os.path.relpath(ruta, raiz)
        if rel in NO_TOCAR or not os.path.isfile(ruta):
            continue
        texto = open(ruta, encoding="utf-8").read()
        nuevo = PATRON.sub(lambda m: f"sw/max_media.{m.group(1)}", texto)
        for viejo, reemplazo in POR_PARTES:
            nuevo = nuevo.replace(viejo, reemplazo)
        if nuevo != texto:
            with open(ruta, "w", encoding="utf-8", newline="") as f:
                f.write(nuevo)
            cambiados.append(f"{rel} ({len(PATRON.findall(texto)) + sum(texto.count(v) for v, _ in POR_PARTES)})")
    # 3. sw/trade.s es el programa del peldaño
    shutil.copyfile(os.path.join(raiz, "sw/fondo.s"), os.path.join(raiz, "sw/trade.s"))
    r = sh([sys.executable, "tools/pochoasm.py", "sw/trade.s", "-o", "sw/trade.hex"], cwd=raiz)
    if r.returncode != 0:
        raise SystemExit(f"FAIL: no ensambla sw/trade.s: {r.stdout}{r.stderr}")
    r = sh([sys.executable, "tools/pochoasm.py", "sw/max_media.s", "-o", "sw/max_media.hex"], cwd=raiz)
    if r.returncode != 0:
        raise SystemExit(f"FAIL: no ensambla sw/max_media.s: {r.stdout}{r.stderr}")
    sh(["git", "add", PELDANO_V, "sw/trade.s", "sw/trade.hex", "sw/max_media.hex"], cwd=raiz)
    print(f"Peldano por defecto: {peldano} ({' '.join('-D' + d for d in defs)})")
    print(f"  {PELDANO_V} creado; sw/trade.s es copia de sw/fondo.s; el programa de R0 es sw/max_media.s")
    print(f"  Referencias al programa de R0 actualizadas en {len(cambiados)} archivos:")
    for c in cambiados:
        print(f"    {c}")
    # 4. Comprobación
    ok, texto = oficial(raiz)
    print(texto)
    return ok


def probar(peldano, pruebas):
    d = os.path.join(RAIZ, "build", "peldano", peldano)
    sh(["git", "worktree", "remove", "--force", d])
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    r = sh(["git", "worktree", "add", "--detach", d, "HEAD"])
    if r.returncode != 0:
        raise SystemExit(f"FAIL: git worktree: {r.stderr}")
    try:
        # El worktree parte del último commit: se copian los cambios sin commit de este árbol
        diff = sh(["git", "diff", "HEAD", "--binary"]).stdout
        if diff:
            p = subprocess.run(["git", "apply", "--whitespace=nowarn"], cwd=d, input=diff, text=True, capture_output=True)
            if p.returncode != 0:
                raise SystemExit(f"FAIL: no se pudieron copiar los cambios sin commit: {p.stderr}")
        for nuevo in sh(["git", "ls-files", "--others", "--exclude-standard"]).stdout.split():
            os.makedirs(os.path.dirname(os.path.join(d, nuevo)) or d, exist_ok=True)
            shutil.copy2(os.path.join(RAIZ, nuevo), os.path.join(d, nuevo))
        print(f"Prueba de 'fijar {peldano}' en una copia ({os.path.relpath(d, RAIZ)}), sin tocar este arbol:")
        ok = fijar(peldano, d)
        for p in pruebas:
            try:
                r = sh(["make", p], cwd=d, timeout=1200)
                bien = r.returncode == 0
            except subprocess.TimeoutExpired:
                r = subprocess.CompletedProcess([], 1, "", "no termino en 20 minutos")
                bien = False
            ok &= bien
            print(f"{'PASS' if bien else 'FAIL'} make {p} despues de fijar")
            if not bien:
                print("  " + "\n  ".join((r.stdout + r.stderr).splitlines()[-15:]))
        print(f"{'PASS' if ok else 'FAIL'}: fijar {peldano} deja el comando oficial en 4/4 con {peldano.upper()} "
              f"y {len(pruebas)} objetivos propios en verde")
        return ok
    finally:
        sh(["git", "worktree", "remove", "--force", d])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="orden", required=True)
    sub.add_parser("oficial")
    for nombre in ("fijar", "probar"):
        p = sub.add_parser(nombre)
        p.add_argument("peldano", choices=sorted(DEFINICIONES))
        if nombre == "probar":
            p.add_argument("--pruebas", default=",".join(PRUEBAS))
    a = ap.parse_args(argv)
    if a.orden == "oficial":
        ok, texto = oficial()
        print(texto)
    elif a.orden == "fijar":
        ok = fijar(a.peldano)
    else:
        ok = probar(a.peldano, [p for p in a.pruebas.split(",") if p])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
