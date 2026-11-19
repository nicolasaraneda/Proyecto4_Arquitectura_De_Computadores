#!/usr/bin/env python3
"""explorar_rival.py: mano a mano contra el rival de Tesla, traza de AMD y variante del caso S
(docs/exploracion_ideas.md, secciones 10 y 11; pedidos del 19/11).

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Rival de Tesla: compra 63 repetido desde el primer 100, vende al ver 220 o más y no vuelve
(`unavez100_220`, su patrimonio sale de la caché en C de la población). Caso S: el 100 llega antes
que el 255; caso B: al revés. Los subconjuntos son los de la población completa (1 368 253
ventanas): todas, y las ventanas de validación por años (enteras en 2024) y por empresas (AMD y
TSLA). Aquí no se ajusta ningún parámetro.

Uso (con export P4_DATOS=~/proyectos/datos_p4):
  python3 ref/cotas/explorar_rival.py amd                 -> amd.txt
  python3 ref/cotas/explorar_rival.py mano --semilla 18   -> mano.txt   (corre la población si falta)
  python3 ref/cotas/explorar_rival.py casos --semilla 18  -> caso_s.txt
"""
import argparse
import hashlib
import os
import random
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import explorar_ideas as E   # noqa: E402
import ideas_caso_s as CS    # noqa: E402
import ideas                 # noqa: E402
import comun                 # noqa: E402
import reales                # noqa: E402

E.CODIGO_EXTRA["casoS"] = hashlib.sha256(open(os.path.abspath(CS.__file__), "rb").read()).hexdigest()[:16]

RIVAL = E.RIVAL_TESLA
SORTEOS = 20000
BASES = [("banda 40", E.B40), ("banda 60", E.B60), ("tres bandas por hilo", E.TRES)]
VARIANTES = [("banda 40, (a) no recompra", ("casoS", {"base": E.B40, "modo": "nunca"})),
             ("banda 40, (b) recompra 1/3", ("casoS", {"base": E.B40, "modo": "tercio"})),
             ("tres bandas, (a) no recompra", ("casoS", {"base": E.TRES, "modo": "nunca"})),
             ("tres bandas, (b) recompra 1/3", ("casoS", {"base": E.TRES, "modo": "tercio"}))]
CON_INFO = [VARIANTES[0][1], VARIANTES[2][1]]      # dan el caso y las recompras de la base en cada ventana


# --- población ----------------------------------------------------------------------------------

def poblacion(carpeta, procesos=None):
    """Conjunto completo, rivales, resultados de bases y variantes, caso y recompras por ventana."""
    conj = E.completa(carpeta)
    R = E.rivales(conj)
    inf = E.evaluar(conj, CON_INFO, procesos, trozo=200, info=True)
    caso = bytearray(x[1] for x in inf[0]["info"])
    rec40 = bytearray(min(255, x[2]) for x in inf[0]["info"])
    rec3 = bytearray(min(255, x[2]) for x in inf[1]["info"])
    for r in inf:
        r["info"] = None
    res = E.evaluar(conj, [sp for _, sp in BASES] + [sp for _, sp in VARIANTES], procesos, trozo=200, info=False)
    for r in res:
        r["info"] = None
    W = {nm: r["W"] for (nm, _), r in zip(BASES + VARIANTES, res)}
    dd = {nm: r for (nm, _), r in zip(BASES + VARIANTES, res)}
    idx = {"todas": list(range(len(conj.filas)))}
    for sep, (aj, va) in E.SEPARACIONES.items():
        idx[f"{sep}-validacion"] = E.sub(conj, va)
    return types.SimpleNamespace(conj=conj, R=R, W=W, res=dd, caso=caso, rec={"banda 40": rec40, "tres": rec3}, idx=idx)


def mano_a_mano(P, W, idx, nombre, semilla):
    """Ventanas y torneos de 3 rondas contra el rival de Tesla. Mismos sorteos para todas las estrategias."""
    Wr = P.R[RIVAL]
    n = len(idx)
    g = sum(1 for i in idx if W[i] > Wr[i])
    e = sum(1 for i in idx if W[i] == Wr[i])
    d, ee = E.delta_ee(P, {"W": W}, {"W": Wr}, idx)
    rng = random.Random(f"mano3-{semilla}-{nombre}")
    g3 = e3 = 0
    for _ in range(SORTEOS):
        a, b, c = idx[rng.randrange(n)], idx[rng.randrange(n)], idx[rng.randrange(n)]
        x = W[a] + W[b] + W[c] - Wr[a] - Wr[b] - Wr[c]
        g3 += x > 0
        e3 += x == 0
    return dict(n=n, g=100 * g / n, e=100 * e / n, p=100 * (n - g - e) / n, d=d, ee=ee,
                g3=100 * g3 / SORTEOS, e3=100 * e3 / SORTEOS, p3=100 * (SORTEOS - g3 - e3) / SORTEOS)


def subconjuntos(P):
    out = []
    for k, ix in P.idx.items():
        out.append((k, "todas", ix))
        out.append((k, "S", [i for i in ix if P.caso[i] == 1]))
        out.append((k, "B", [i for i in ix if P.caso[i] == 2]))
    return out


def mano(P, semilla):
    L = [f"Mano a mano contra el rival de Tesla (unavez 100 220), poblacion completa ({len(P.conj.filas)} ventanas). "
         f"ref/cotas/explorar_rival.py mano --semilla {semilla}, commit {E.commit()}",
         "Ventanas: ganamos / empatamos / perdemos (%), diferencia media de patrimonio (nosotros - rival) con error estandar",
         "por grupos de ventanas vecinas (empresa y bloque de 20 dias de inicio). Torneos de 3 rondas: 20 000 sorteos de tres",
         "ventanas del mismo subconjunto y caso (los mismos para las tres estrategias); se compara la suma de las tres rondas.",
         "La diferencia media de la suma de 3 rondas es 3 veces la de las ventanas, con 3 veces su error estandar.", "",
         f"{'subconjunto':22s} {'caso':5s} {'ventanas':>8s} {'estrategia':22s} {'gana':>6s} {'empata':>6s} {'pierde':>6s} "
         f"{'dif. media (ee)':>17s} {'3r gana':>8s} {'3r empata':>9s} {'3r pierde':>9s}"]
    for k, caso, ix in subconjuntos(P):
        for nm, _ in BASES:
            m = mano_a_mano(P, P.W[nm], ix, f"{k}-{caso}", semilla)
            L.append(f"{k:22s} {caso:5s} {m['n']:8d} {nm:22s} {m['g']:6.1f} {m['e']:6.1f} {m['p']:6.1f} "
                     f"{m['d']:+8.0f} ({m['ee']:5.0f}) {m['g3']:8.1f} {m['e3']:9.1f} {m['p3']:9.1f}")
        L.append("")
    return L


# --- variante del caso S ------------------------------------------------------------------------

def comprobar_muestra(carpeta, semilla, procesos):
    """En la muestra, el modo 'todo' tiene que dar lo mismo que la base."""
    cx = E.Ctx(carpeta, semilla, procesos)
    specs = [("casoS", {"base": E.B40, "modo": "todo"}), ("casoS", {"base": E.TRES, "modo": "todo"})]
    r = cx.ev(specs)
    rb = cx.ev([E.B40, E.TRES])
    malos = sum(1 for a, b in zip(r, rb) for i in range(len(cx.todo)) if a["W"][i] != b["W"][i] or a["n"][i] != b["n"][i])
    return f"Comprobacion en la muestra ({len(cx.todo)} ventanas): modo 'todo' contra la base (banda 40 y tres bandas): " \
           f"{malos} diferencias" + ("  PASS" if malos == 0 else "  FAIL")


def casos(P, semilla, linea_muestra):
    L = [f"Variante del caso S (ideas_caso_s.py), poblacion completa ({len(P.conj.filas)} ventanas). "
         f"ref/cotas/explorar_rival.py casos --semilla {semilla}, commit {E.commit()}",
         "Solo en el caso S (100 antes que 255), despues de vender en el 255: (a) no recompra; (b) recompra con un tercio del",
         "patrimonio; (c) recompra todo (lo actual). En el caso B no cambia nada.", linea_muestra, ""]
    grupos = [("banda 40", "banda 40", ["banda 40", "banda 40, (a) no recompra", "banda 40, (b) recompra 1/3"]),
              ("tres", "tres bandas por hilo", ["tres bandas por hilo", "tres bandas, (a) no recompra",
                                                "tres bandas, (b) recompra 1/3"])]
    for k, ix in P.idx.items():
        S = [i for i in ix if P.caso[i] == 1]
        Tx = E.Torneo(ix, P.R, f"completa-{k}-sin-copia", semilla, excluir=("espera_banda40",))
        L += [f"== {k}: {len(ix)} ventanas, {len(S)} en el caso S ({100 * len(S) / len(ix):.1f} %)",
              f"   {'estrategia':32s} | {'caso S: media':>13s} {'p5':>6s} {'peor':>6s} {'dif. con (c) (ee)':>18s} "
              f"{'recompra %':>10s} | {'pts sin copia':>13s} {'1a sola %':>9s} | {'vs rival: gana':>14s} {'empata':>6s} "
              f"{'pierde':>6s} {'dif. (ee)':>14s} {'3r gana':>8s} | {'S vs rival: gana':>16s} {'pierde':>6s}"]
        for rk, base, nombres in grupos:
            rec = sum(1 for i in S if P.rec[rk][i] > 0)
            Wc = P.W[base]
            for nm in nombres:
                W = P.W[nm]
                ws = sorted(W[i] for i in S)
                n = len(ws)
                d, ee = E.delta_ee(P, {"W": W}, {"W": Wc}, S)
                pts, pri = Tx.puntos(W)
                m = mano_a_mano(P, W, ix, f"{k}-todas", semilla)
                ms = mano_a_mano(P, W, S, f"{k}-S", semilla)
                etiqueta = nm if nm != base else f"{base}, (c) recompra todo"
                L.append(f"   {etiqueta:32s} | {sum(ws) / n:13.0f} {ws[int(0.05 * (n - 1))]:6d} {ws[0]:6d} "
                         f"{d:+9.0f} ({ee:5.0f}) {100 * rec / n:10.1f} | {pts:13.3f} {100 * pri:9.1f} | "
                         f"{m['g']:14.1f} {m['e']:6.1f} {m['p']:6.1f} {m['d']:+7.0f} ({m['ee']:4.0f}) {m['g3']:8.1f} | "
                         f"{ms['g']:16.1f} {ms['p']:6.1f}")
        L.append("")
    L.append("recompra %: ventanas del caso S en que el comportamiento base vuelve a comprar despues de vender en el 255.")
    L.append("pts sin copia y 1a sola %: torneo de 3 rondas de la tabla 2 (mismo sorteo que primera.txt), sin espera_banda40.")
    return L


# --- traza de AMD -------------------------------------------------------------------------------

def traza(w, spec):
    st = ideas.cuenta_spec(spec) if spec[0] == "unavez" else ideas.crear(spec)
    caja, acc, d = ideas.CAJA0, 0, ideas.M
    filas = []
    Wmax, tmax = -1, -1
    for n, p in enumerate(w):
        if d:
            a, q = d >> 6, d & 63
            if a == 1:
                q = min(q, (caja - ideas.COMISION) // p)
                if q > 0:
                    caja -= q * p + ideas.COMISION
                    acc += q
                    filas.append((n, p, f"compra {q}", caja, acc, caja + acc * p))
            elif a == 2:
                q = min(q, acc)
                if q > 0:
                    caja += q * p - ideas.COMISION
                    acc -= q
                    filas.append((n, p, f"vende {q}", caja, acc, caja + acc * p))
        W = caja + acc * p
        if W > Wmax:
            Wmax, tmax = W, n
        d = st.decidir(p, caja, acc)
    return filas, caja + acc * w[-1], Wmax, tmax, st


def amd(carpeta):
    fechas, minutos, x = reales.leer_sesion(carpeta, "AMD")
    s0 = next(i for i in range(len(fechas)) if fechas[i] == "2022-01-10" and minutos[i] == 50)
    w = comun.normalizar(x[s0:s0 + E.LARGO])
    i100, i255 = w.index(100), w.index(255)
    L = [f"Ronda de AMD del 18/11 (AMD desde el 10/1/2022 a las {reales.hora(50)}, 20 000 minutos). "
         f"ref/cotas/explorar_rival.py amd, commit {E.commit()}",
         f"Primer 100 en el tick {i100}, primer 255 en el tick {i255}: caso {'S' if i100 < i255 else 'B'}. "
         f"Precio final {w[-1]}.", ""]
    for nm, sp in (("banda 60 (la que corrio el 18/11)", E.B60), ("banda 40", E.B40),
                   ("rival de Tesla", ("unavez", 100, 220))):
        filas, Wf, Wmax, tmax, st = traza(w, sp)
        fase = f"; fase D desde el tick {st.tD}" if hasattr(st, "tD") else ""
        L += [f"== {nm}: patrimonio final {Wf}; maximo {Wmax} en el tick {tmax} (precio {w[tmax]}){fase}",
              f"   {'tick':>6s} {'precio':>6s} {'orden ejecutada':>16s} {'caja':>7s} {'acciones':>8s} {'patrimonio':>10s}"]
        for f in filas:
            L.append(f"   {f[0]:6d} {f[1]:6d} {f[2]:>16s} {f[3]:7d} {f[4]:8d} {f[5]:10d}")
        despues = [f for f in filas if f[0] > tmax]
        compras = [f for f in despues if f[2].startswith("compra")]
        L.append(f"   despues del maximo: {len(despues)} ordenes, {len(compras)} compras"
                 + (f" (la primera en el tick {compras[0][0]} a {compras[0][1]})" if compras else ""))
        L.append("")
    return L


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", choices=("amd", "mano", "casos"))
    ap.add_argument("--semilla", type=int, default=E.SEMILLA)
    ap.add_argument("--datos", default=None)
    ap.add_argument("--procesos", type=int, default=None)
    a = ap.parse_args()
    carpeta = reales.carpeta_datos(a.datos)
    os.makedirs(E.SALIDA, exist_ok=True)
    if a.accion == "amd":
        L, nombre = amd(carpeta), "amd.txt"
    elif a.accion == "mano":
        L, nombre = mano(poblacion(carpeta, a.procesos), a.semilla), "mano.txt"
    else:
        lm = comprobar_muestra(carpeta, a.semilla, a.procesos)
        L, nombre = casos(poblacion(carpeta, a.procesos), a.semilla, lm), "caso_s.txt"
    texto = "\n".join(L) + "\n"
    open(os.path.join(E.SALIDA, nombre), "w").write(texto)
    print(texto, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
