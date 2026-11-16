#!/usr/bin/env python3
"""barrer.py: barrido de variantes del aprendizaje en vivo contra max_media, con la semilla 0.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 barrer.py --arnes build/arnes --semilla 0 --salida mediciones [--etapa NOMBRE] [--largo 2000]

Cada etapa es una lista de variantes fijada en este archivo. Se evalúan con el
comando `hipotesis` del arnés (campo mixto, G = 10), siempre con max_media como
referencia de las diferencias pareadas, y se deja una tabla por etapa y largo
en mediciones/barrido_<etapa>_n<largo>.txt.

A 20 000 ticks se usan dos vistas: interiores (la del criterio de corte) y
parada (la que no selecciona series ni se infla con el rebote).

La columna "juicio" es una lectura rápida del criterio de corte con estas
cifras: PASA si los puntos esperados mejoran en más de dos errores con H3a y
con H3b y el percentil 5 de la competencia no baja en más de dos errores. El
veredicto oficial de las candidatas finales lo da el comando `veredicto`
(finales.py).

Solo se usa la semilla 0. El número de variantes probadas queda en
mediciones/barrido_cuenta.txt.
"""
import argparse
import os
import subprocess
import sys

REF = "max_media"
LOTE = 40          # variantes por llamada (el arnés admite 48 contando la referencia, nada y byh)

T0 = "tabla:"      # prefijo cómodo


def etapas():
    e = {}

    # 1. Tabla de retorno, una fila, sin tercer índice: tasa de aprendizaje por horizonte.
    e["tabla_ka_h"] = (["tabla:ka=0"] +
                       [f"tabla:ka={ka},h={h}" for h in (4, 8, 16, 32) for ka in (6, 8, 10, 12, 14)])

    # 2. Pendiente del valor inicial (fija también el umbral de acción): c en precio/256 por unidad de desviación.
    e["tabla_c"] = [f"tabla:ka={ka},h=16,c={c}" for c in (8, 16, 32, 64, 128) for ka in (8, 10, 12)]

    # 2b. Umbral de acción: corrimiento del umbral de compra (ui) y del de venta (uo), en precio/1024. Con 48 (menos que
    # media casilla, que son 64) la tabla sigue partiendo como max_media: las dos filas con ka=0 son el control.
    e["tabla_umbral"] = (["tabla:ka=0,ui=48,uo=-48", "tabla:ka=0,ui=-48,uo=48"] +
                         [f"tabla:ka={ka},h=16,ui={ui},uo={uo}"
                          for (ui, uo) in ((48, 0), (-48, 0), (0, 48), (0, -48), (48, -48), (-48, 48)) for ka in (8, 10, 12)])

    # 3. Forma de la tabla: tamaño, filas por posición y tercer índice. Un factor a la vez, con ka = 10 y 12.
    formas = ["nb=8", "nb=16", "nb=32", "nb=64,sh=4", "nb=64,sh=3", "filas=2", "ter=1", "ter=2", "ter=3", "ter=1,filas=2",
              "ter=3,nb=8", "ter=2,uv=256", "ter=2,uv=512"]
    e["tabla_forma"] = [f"tabla:ka={ka},h=16,{f}" for f in formas for ka in (10, 12)]

    # 4. Preferencia de acción con contador saturado.
    e["tabla_contador"] = ([f"tabla:modo=1,ka=1,bits={b},h={h},g={g}" for h in (4, 16) for g in (0, 1) for b in (3, 4, 6, 8, 10)] +
                           [f"tabla:modo=1,ka=1,bits={b},h=16,{x}" for x in ("filas=2", "ter=1", "ter=3") for b in (6, 8, 10)])

    # 5. La tabla como ajuste lento de las bandas.
    e["tabla_banda"] = ([f"tabla:banda=1,ka={ka},h={h},lim={lim}" for h in (8, 16, 32) for lim in (1, 2) for ka in (6, 8, 10, 12)] +
                        [f"tabla:banda=1,ka={ka},h=16,lim=2,nb=64,sh=4" for ka in (8, 10, 12)] +
                        [f"tabla:banda=1,ka={ka},h=16,lim=1,mg={mg}" for mg in (64, 128, 256) for ka in (8, 10)] +
                        [f"tabla:banda=1,ka={ka},h=16,lim=1,c={c}" for c in (16, 64) for ka in (8, 10)] +
                        [f"tabla:banda=1,ka={ka},h=16,lim=1,ter={t}" for t in (2, 3) for ka in (8, 10)])

    # 6. El signo del último cambio: reglas fijas (controles, sin aprender) y la tabla que debería descubrirlas.
    e["signo"] = (["tabla:ter=3,ezb=32", "tabla:ter=3,ezb=64", "tabla:ter=3,ezb=96", "tabla:ter=3,ezb=-32",
                   "tabla:ter=1,ezb=64,ezs=-32"] +
                  [f"tabla:ter=3,ezb=64,ka={ka},h={h}" for h in (8, 16) for ka in (8, 10, 12)] +
                  [f"tabla:ter=3,ka={ka},h=8" for ka in (8, 10, 12)] +
                  [f"tabla:ter=3,ka={ka},h=8,nb=8" for ka in (8, 10, 12)])

    # 6c. Sesgo de redondeo de la forma directa T += (R - T) >> ka (dir=1) contra el acumulador (por defecto).
    e["redondeo"] = [f"tabla:ka={ka},h=16{d}" for ka in (10, 12, 14, 16) for d in ("", ",dir=1")]

    # 6b. Meseta de la regla fija "esperar a que el precio deje de bajar" (sin aprender): umbral tras una baja y tras una subida.
    e["espera"] = [f"tabla:ter=1,ezb={b},ezs={u}" for b in (32, 64, 96, 128) for u in (0, -32, -64)]

    # 7. El predictor de patrones operando solo.
    e["patron"] = [f"patron:tipo={t},H={H},sim={s},bits={b},h={h}"
                   for (t, H, s) in ((0, 8, 2), (0, 12, 2), (1, 12, 2), (2, 8, 2), (3, 8, 2), (3, 6, 3))
                   for b in (2, 3) for h in (1, 16)]

    # 8. max_media con el predictor como filtro: postergar entradas (fe) y salidas (fs).
    preds = ((0, 8, 2, 2), (0, 12, 2, 2), (0, 6, 3, 2), (1, 12, 2, 2), (2, 8, 2, 2), (3, 8, 2, 2), (3, 12, 2, 2), (0, 8, 2, 3), (3, 8, 2, 3))
    e["filtro"] = (["mm_patron:apr=0"] +
                   [f"mm_patron:tipo={t},H={H},sim={s},bits={b},h=1,fe={fe},fs={fs},maxp=4"
                    for (t, H, s, b) in preds for (fe, fs) in ((2, 0), (0, 2), (2, 2))] +
                   [f"mm_patron:tipo={t},H={H},sim=2,bits=2,h={h},fe={fe},fs=0,maxp={mp}"
                    for (t, H) in ((0, 8), (3, 8)) for h in (2, 4) for (fe, mp) in ((2, 4), (1, 2), (2, 16))])

    # Cota en puntos: bandas fijas de la familia paramétrica (ya son candidatos del núcleo; aquí son el oráculo por grupo).
    e["cota_bandas"] = [f"param:E={E},X={X}" for E in (48, 64, 80, 112, 128) for X in (0, 16, 32)] + ["param:E=96,X=16", "param:E=96,X=32"]
    return e


# Preselección para las rondas de 20 000 ticks. Se eligió mirando solo las tablas de 2000 ticks de la semilla 0.
LARGAS = {
    "largas": ["tabla:ka=0",
               "tabla:ka=10,h=16", "tabla:ka=12,h=16", "tabla:ka=14,h=16", "tabla:ka=12,h=32", "tabla:ka=14,h=32",
               "tabla:ka=10,h=16,filas=2", "tabla:ka=10,h=16,ter=1", "tabla:ka=12,h=16,ter=3", "tabla:ka=10,h=16,nb=64,sh=3",
               "tabla:ka=12,h=16,c=64",
               "tabla:modo=1,ka=1,bits=8,h=16,g=0", "tabla:modo=1,ka=1,bits=8,h=16,g=1", "tabla:modo=1,ka=1,bits=10,h=16,g=0",
               "tabla:modo=1,ka=1,bits=6,h=4,g=1",
               "tabla:banda=1,ka=8,h=16,lim=1", "tabla:banda=1,ka=10,h=16,lim=1", "tabla:banda=1,ka=12,h=16,lim=1",
               "tabla:banda=1,ka=14,h=16,lim=1", "tabla:banda=1,ka=10,h=8,lim=1", "tabla:banda=1,ka=12,h=32,lim=2",
               "tabla:banda=1,ka=10,h=16,lim=1,mg=128", "tabla:banda=1,ka=10,h=16,lim=2,nb=64,sh=4",
               "tabla:ter=3,ezb=64", "tabla:ter=1,ezb=64,ezs=-32", "tabla:ter=1,ezb=96,ezs=-32",
               "tabla:ter=3,ezb=64,ka=12,h=8", "tabla:ter=3,ka=10,h=8", "tabla:ter=3,ka=12,h=8",
               "patron:tipo=1,H=12,sim=2,bits=3,h=1", "patron:tipo=3,H=8,sim=2,bits=3,h=16",
               "mm_patron:tipo=1,H=12,sim=2,bits=2,h=1,fe=2,fs=0,maxp=4", "mm_patron:tipo=0,H=12,sim=2,bits=2,h=1,fe=2,fs=0,maxp=4",
               "mm_patron:tipo=0,H=8,sim=2,bits=3,h=1,fe=0,fs=2,maxp=4", "mm_patron:tipo=3,H=8,sim=2,bits=2,h=1,fe=2,fs=0,maxp=4",
               "mm_patron:tipo=0,H=8,sim=2,bits=2,h=2,fe=1,fs=0,maxp=2",
               "tabla:ka=10,h=16,nb=8", "tabla:ter=3,ka=10,h=8,nb=8", "tabla:ter=3,ka=12,h=8,nb=8",
               "param:E=64,X=16", "param:E=80,X=16", "param:E=96,X=16"],
    "redondeo": [f"tabla:ka={ka},h=16{d}" for ka in (12, 14, 16) for d in ("", ",dir=1")],
}

CONJUNTOS = ("evidencia", "remuestreo", "plausibles", "estres")
CLAVES = ("h1_media", "h1_p5", "h1_dif", "h1_dif_ee", "h2r_dif", "h2r_dif_ee", "ordenes", "d_h3a", "d_h3a_ee", "d_h3b", "d_h3b_ee",
          "d_h3a_c_p5", "d_h3a_c_p5_ee", "d_h3b_c_p5", "d_h3b_c_p5_ee", "h3a_media", "h3b_media", "n")


def correr(arnes, specs, largo, semilla, vista, tmp):
    """Devuelve datos[spec][conjunto][clave] para las variantes pedidas (la referencia va siempre primera)."""
    datos = {}
    for i in range(0, len(specs), LOTE):
        parte = specs[i:i + LOTE]
        tsv = os.path.join(tmp, f"barrido_{os.getpid()}.tsv")
        cmd = [arnes, "hipotesis", "--largo", str(largo), "--semilla", str(semilla), "--candidatos", ";".join([REF] + parte),
               "--ref", REF, "--tsv", tsv]
        if vista == "interiores":
            cmd.append("--interior")
        elif vista == "parada":
            cmd.append("--parada")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        with open(tsv, encoding="utf-8") as f:
            next(f)
            for linea in f:
                _, _, _, conjunto, cand, clave, valor = linea.rstrip("\n").split("\t")
                if clave in CLAVES:
                    datos.setdefault(cand, {}).setdefault(conjunto, {})[clave] = float(valor)
        os.remove(tsv)
    return datos


def juicio(d):
    mejora = d["d_h3a"] > 2 * d["d_h3a_ee"] and d["d_h3b"] > 2 * d["d_h3b_ee"]
    empeora = d["d_h3a"] < -2 * d["d_h3a_ee"] or d["d_h3b"] < -2 * d["d_h3b_ee"]
    baja_p5 = d["d_h3a_c_p5"] < -2 * d["d_h3a_c_p5_ee"] or d["d_h3b_c_p5"] < -2 * d["d_h3b_c_p5_ee"]
    if mejora and not baja_p5:
        return "PASA"
    if empeora:
        return "empeora"
    return "igual" if not mejora else "p5 baja"


def tabla(titulo, specs, datos, largo, vista, semilla, salida):
    ref = datos[REF]
    with open(salida, "w", encoding="utf-8") as f:
        f.write(f"{titulo}\n")
        f.write(f"Semilla {semilla}, rondas de {largo} ticks, series {vista}, campo mixto, G = 10. Diferencias pareadas contra {REF}.\n")
        f.write(f"{REF}: patrimonio medio {ref['evidencia']['h1_media']:.0f} (p5 {ref['evidencia']['h1_p5']:.0f}), "
                f"H3a {ref['evidencia']['h3a_media']:.3f}, H3b {ref['evidencia']['h3b_media']:.3f}, "
                f"{ref['evidencia']['ordenes']:.1f} ordenes por ronda, {ref['evidencia']['n']:.0f} series de evidencia.\n")
        f.write("H1: patrimonio. H2: razon W/B&H. H3a y H3b: puntos del torneo (0 a 2). p5: percentil 5 de la competencia de tres rondas.\n\n")
        cab = (f"{'variante':<58} {'ord':>6} | {'H1 evid':>8} {'+-':>4} {'H1 rem':>7} {'+-':>4} {'H1 pla':>7} {'+-':>4} {'H1 est':>7} {'+-':>4} | "
               f"{'H2 evid':>7} {'+-':>6} | {'H3a evid':>8} {'+-':>6} {'H3b evid':>8} {'+-':>6} | {'p5 H3a':>7} {'+-':>6} {'p5 H3b':>7} {'+-':>6} | "
               f"{'H3a rem':>7} {'H3a pla':>7} {'H3b rem':>7} {'H3b pla':>7} | {'H3a est':>7} {'+-':>6} {'H3b est':>7} {'+-':>6} | juicio")
        f.write(cab + "\n")
        for s in specs:
            d = datos[s]
            ev, re, pl, es = d["evidencia"], d["remuestreo"], d["plausibles"], d["estres"]
            f.write(f"{s:<58} {ev['ordenes']:6.1f} | {ev['h1_dif']:+8.0f} {ev['h1_dif_ee']:4.0f} {re['h1_dif']:+7.0f} {re['h1_dif_ee']:4.0f} "
                    f"{pl['h1_dif']:+7.0f} {pl['h1_dif_ee']:4.0f} {es['h1_dif']:+7.0f} {es['h1_dif_ee']:4.0f} | "
                    f"{ev['h2r_dif']:+7.3f} {ev['h2r_dif_ee']:6.3f} | "
                    f"{ev['d_h3a']:+8.3f} {ev['d_h3a_ee']:6.3f} {ev['d_h3b']:+8.3f} {ev['d_h3b_ee']:6.3f} | "
                    f"{ev['d_h3a_c_p5']:+7.3f} {ev['d_h3a_c_p5_ee']:6.3f} {ev['d_h3b_c_p5']:+7.3f} {ev['d_h3b_c_p5_ee']:6.3f} | "
                    f"{re['d_h3a']:+7.3f} {pl['d_h3a']:+7.3f} {re['d_h3b']:+7.3f} {pl['d_h3b']:+7.3f} | "
                    f"{es['d_h3a']:+7.3f} {es['d_h3a_ee']:6.3f} {es['d_h3b']:+7.3f} {es['d_h3b_ee']:6.3f} | {juicio(ev)}\n")
    return {s: juicio(datos[s]["evidencia"]) for s in specs}


def aprende(spec):
    """True si la variante ajusta algo en vivo (no es una regla fija ni un control con el aprendizaje apagado)."""
    nombre, _, par = spec.partition(":")
    campos = dict(x.split("=") for x in par.split(",") if "=" in x)
    if nombre == "tabla":
        return int(campos.get("ka", 0)) > 0
    if nombre == "mm_patron":
        return int(campos.get("apr", 1)) > 0
    return nombre == "patron"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arnes", default="build/arnes")
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--salida", default="mediciones")
    ap.add_argument("--etapa", default="todas")
    ap.add_argument("--largo", type=int, default=0, help="0: las etapas a 2000 ticks y la preseleccion a 20 000")
    a = ap.parse_args()
    if a.semilla != 0:
        sys.exit("este estudio explora solo con la semilla 0")
    os.makedirs(a.salida, exist_ok=True)
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
    os.makedirs(tmp, exist_ok=True)
    cuenta = []
    todos_juicios = {}
    plan = []
    if a.largo in (0, 2000):
        plan += [(n, s, 2000, "todas") for n, s in etapas().items()]
    if a.largo in (0, 20000):
        plan += [(n, s, 20000, v) for n, s in LARGAS.items() for v in ("interiores", "parada")]
    for nombre, specs, largo, vista in plan:
        if a.etapa not in ("todas", nombre):
            continue
        datos = correr(a.arnes, specs, largo, a.semilla, vista, tmp)
        sufijo = "" if largo == 2000 else "_" + vista
        ruta = os.path.join(a.salida, f"barrido_{nombre}_n{largo}{sufijo}.txt")
        juicios = tabla(f"Barrido: etapa {nombre}", specs, datos, largo, vista, a.semilla, ruta)
        cuenta.append((nombre, largo, vista, len(specs)))
        for s, j in juicios.items():
            todos_juicios[(s, largo, vista)] = j
        print(f"{ruta}: {len(specs)} variantes", flush=True)
    if a.etapa == "todas" and a.largo == 0:
        todas = set()
        for _, specs in etapas().items():
            todas.update(specs)
        with open(os.path.join(a.salida, "barrido_cuenta.txt"), "w", encoding="utf-8") as f:
            f.write("Variantes evaluadas en el barrido (semilla 0)\n")
            for nombre, largo, vista, n in cuenta:
                f.write(f"  {nombre:<16} {largo:>6} ticks, {vista:<10} {n:>4}\n")
            propias = [s for s in todas if not s.startswith("param:")]
            f.write(f"Variantes distintas a 2000 ticks: {len(todas)} ({len(propias)} de este estudio y {len(todas) - len(propias)} bandas fijas de la cota)\n")
            f.write(f"Preseleccion a 20 000 ticks: {len(LARGAS['largas'])}, mas {len(LARGAS['redondeo'])} de la prueba de redondeo\n")
            f.write("\nLectura rapida del criterio (columna juicio), variantes distintas de este estudio:\n")
            for largo, vista in ((2000, "todas"), (20000, "interiores"), (20000, "parada")):
                for grupo, filtro in (("que aprenden", True), ("fijas o con el aprendizaje apagado", False)):
                    js = {s: j for (s, l, v), j in todos_juicios.items()
                          if l == largo and v == vista and not s.startswith("param:") and aprende(s) == filtro}
                    n = {k: sum(1 for j in js.values() if j == k) for k in ("PASA", "p5 baja", "igual", "empeora")}
                    f.write(f"  {largo:>6} ticks, {vista:<10} {grupo:<36} {len(js):>4}: PASA {n['PASA']}, mejora y baja el p5 {n['p5 baja']}, "
                            f"igual {n['igual']}, empeora {n['empeora']}\n")
                    for s in sorted(s for s, j in js.items() if j == "PASA"):
                        f.write(f"           PASA: {s}\n")


if __name__ == "__main__":
    main()
