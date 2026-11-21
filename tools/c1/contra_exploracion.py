#!/usr/bin/env python3
"""contra_exploracion.py: la referencia entera de C1 (ref/c1/c1.py) contra el C1 de la exploración.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

El C1 de la exploración vive en la rama minutos-reales (ref/cotas/v5.py). Este script la usa desde
su carpeta de trabajo (C1_EXPLORACION, por defecto ~/proyectos/P4_wt_min) y necesita los minutos
reales (P4_DATOS, por defecto ~/proyectos/datos_p4). Compara, ventana por ventana de 20 000 ticks:

  1. byte por byte contra v5.V5Ref (la segunda implementación de la exploración, tick a tick en
     ideas.correr), y con eso las órdenes ejecutadas y el patrimonio;
  2. patrimonio y cantidad de órdenes contra v5.fase_a + v5.post (la que produjo las cifras del
     examen, docs/mediciones/exploracion/c1_examen.txt);
  3. con la política apagada (palabra POLITICA en 0), byte por byte contra la banda 40 de
     ref/fondo.py (la referencia de R2).

Además comprueba que las tablas del modelo (build/c1/modelo, ref/c1/tablas.py) son las que usó la
exploración (sus tablas en caché), celda por celda.

Uso, desde la raíz:  python3 tools/c1/contra_exploracion.py [--conjunto cinco|otras] [--ventanas N]
                     [--salida docs/mediciones/c1/contra_exploracion.txt]
"""
import argparse
import os
import random
import sys
import time
import multiprocessing

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPL = os.path.expanduser(os.environ.get("C1_EXPLORACION", "~/proyectos/P4_wt_min"))
os.environ.setdefault("P4_DATOS", os.path.expanduser("~/proyectos/datos_p4"))
sys.path.insert(0, os.path.join(RAIZ, "ref", "c1"))
sys.path.insert(0, os.path.join(RAIZ, "ref"))
sys.path.insert(0, os.path.join(EXPL, "ref", "cotas"))

import c1 as R            # noqa: E402
import fondo              # noqa: E402  (el de esta rama: se importa antes que los módulos de la exploración)
import tablas as TB       # noqa: E402

_G = {}


class _Graba:
    """Envuelve una estrategia de ideas.correr y guarda los bytes que decide."""

    def __init__(self, s):
        self.s, self.b = s, []

    def decidir(self, p, caja, acc):
        d = self.s.decidir(p, caja, acc)
        self.b.append(d)
        return d


def _ordenes(w, bs):
    """Órdenes ejecutadas (tick, acción, cantidad) con la contabilidad oficial."""
    caja, acc, d, out = 10000, 0, 0, []
    for i, p in enumerate(w):
        a, q = d >> 6, d & 63
        if a == 1:
            q = min(q, (caja - 5) // p)
            if q > 0:
                caja -= q * p + 5
                acc += q
                out.append((i, 1, q))
        elif a == 2:
            q = min(q, acc)
            if q > 0:
                caja += q * p - 5
                acc -= q
                out.append((i, 2, q))
        d = bs[i]
    return out, caja + acc * w[-1]


def _una(i):
    import ideas
    import v5 as V
    import explorar_v5 as X
    w = _G["vent"][i]
    T, T0 = _G["T"], _G["T0"]
    mio, c = R.correr(w, T)
    g = _Graba(V.V5Ref(**X.REF_ARGS["C1"]))
    Wx, nx, _ = ideas.correr(w, g)
    ob, Wm = _ordenes(w, mio)
    ox, Wx2 = _ordenes(w, g.b)
    dif_b = [k for k in range(len(w)) if mio[k] != g.b[k]]
    # fase_a + post
    pre = V.precalcular(w)
    pre["v2c8"] = V.precalcular_v2c(w, pre["tA"], 8)
    optA, optP = X.FINALISTAS[list(X.FINALISTAS)[0]]
    Wp, npo, grupo, Dp = V.post(w, pre, V.fase_a(w, pre, optA), {"b40": V.rival(w, "b40")}, optP)
    # política apagada contra la banda 40 de R2
    ap, _ = R.correr(w, T0)
    f40 = fondo.Fondo()
    b40 = [f40.decidir(p) for p in w]
    return dict(i=i, dif_bytes=len(dif_b), primer=dif_b[0] if dif_b else -1, ord_igual=ob == ox, W=Wm, Wx=Wx, Wp=Wp,
                n=len(ob), nx=nx, np=npo, modo=c.modo, grupo=grupo, apagada=sum(1 for a, b in zip(ap, b40) if a != b),
                emu=c.W, seguro=c.seguro, D=c.D, Dp=Dp)


def tablas_iguales():
    """Las celdas del modelo recalculado contra las de la caché de la exploración."""
    import optimo_estrategia as OE
    import v5 as V
    import paseo_optimo as PO
    A, M = TB.celdas()
    comp = OE.comprimida("V3", "log")
    mal = 0
    for j in range(8):
        pa = V.tabla_pA(j)
        for tr in range(16):
            c = comp.cel[("A", j, tr)]
            rp = tr * OE.LARGO_TRAMO + OE.LARGO_TRAMO // 2
            ok = [p for p in range(101, 255) if p >= c[0][0] and pa[rp * PO.L + p - 100] >= 0.95]
            mal += A[(j, tr)] != ((min(ok) if ok else 256), c[1][0])
    m = V.comprimida_tramos(8)
    for F in "BCD":
        for j in range(8):
            for tr in range(8):
                alto, bajo, salida, bajo1 = m.cel[(F, j, tr)]
                mal += (alto, salida) != (256, 256) or M[(F, j, tr)] != (bajo, bajo1)
    return mal


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--conjunto", default="cinco")
    ap.add_argument("--ventanas", type=int, default=2400)
    ap.add_argument("--salida")
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    a = ap.parse_args()
    import explorar_regimen as XR
    t0 = time.time()
    D = XR.cargar(a.conjunto)
    vent = D.ventanas
    _G["vent"] = vent
    T = TB.palabras()
    _G["T"] = T
    _G["T0"] = TB.palabras({TB.T_POLITICA: TB.POLITICA_APAGADA})
    rng = random.Random("c1-contra-exploracion")
    ids = sorted(rng.sample(range(len(vent)), min(a.ventanas, len(vent))))
    with multiprocessing.get_context("fork").Pool(a.jobs) as pool:
        res = pool.map(_una, ids, chunksize=8)
    L = [f"# Referencia entera de C1 (ref/c1/c1.py) contra el C1 de la exploración", "",
         f"Generado por tools/c1/contra_exploracion.py. Exploración: {EXPL} (rama minutos-reales). Conjunto `{a.conjunto}`: "
         f"{len(vent)} ventanas de 20 000 ticks; se comparan {len(ids)} elegidas al azar (semilla fija).", ""]
    mt = tablas_iguales()
    L.append(f"- Tablas: {mt} celdas distintas entre el modelo recalculado (ref/c1/tablas.py) y las tablas en caché de la "
             f"exploración (320 celdas, 640 niveles).")
    nb = sum(1 for r in res if r["dif_bytes"])
    L.append(f"- Byte por byte contra `v5.V5Ref`: {len(res) - nb} ventanas idénticas de {len(res)}; "
             f"{sum(r['dif_bytes'] for r in res)} bytes distintos en total ({len(res) * 20000} comparados).")
    no = sum(1 for r in res if not r["ord_igual"])
    L.append(f"- Órdenes ejecutadas (tick, acción y cantidad) contra `v5.V5Ref`: {no} ventanas con alguna diferencia.")
    nw = sum(1 for r in res if r["W"] != r["Wx"])
    L.append(f"- Patrimonio final contra `v5.V5Ref`: {nw} ventanas distintas.")
    npd = sum(1 for r in res if r["W"] != r["Wp"] or r["n"] != r["np"])
    L.append(f"- Patrimonio y cantidad de órdenes contra `v5.fase_a` + `v5.post` (la del examen): {npd} ventanas distintas.")
    nd = sum(1 for r in res if r["D"] != r["Dp"])
    L.append(f"- D final (patrimonio propio menos el del clon) contra `v5.post`: {nd} ventanas distintas.")
    ne = sum(1 for r in res if r["emu"] != r["W"])
    L.append(f"- Cuenta propia emulada por el hilo 3 contra el patrimonio de la contabilidad oficial: {ne} ventanas distintas.")
    na = sum(1 for r in res if r["apagada"])
    L.append(f"- Política apagada, byte por byte contra la banda 40 de `ref/fondo.py`: {na} ventanas con diferencias.")
    ns = sum(r["seguro"] for r in res)
    L.append(f"- Ventanas que terminan en modo seguro: {ns}.")
    modos = [sum(1 for r in res if r["modo"] == m) for m in range(3)]
    L.append(f"- Modo al final: fase A {modos[0]}, recuperación {modos[1]}, candado {modos[2]}. "
             f"Órdenes por ronda: {sum(r['n'] for r in res) / len(res):.1f}. Patrimonio medio: {sum(r['W'] for r in res) / len(res):.0f}.")
    if nb or no or nw or npd:
        L.append("")
        L.append("Diferencias (primeras 20): ventana, bytes distintos, primer tick, patrimonio propio, de V5Ref y de post")
        for r in [r for r in res if r["dif_bytes"] or r["W"] != r["Wp"] or r["n"] != r["np"]][:20]:
            L.append(f"  {r['i']}: {r['dif_bytes']} bytes, tick {r['primer']}, {r['W']} / {r['Wx']} / {r['Wp']}, órdenes {r['n']} / {r['nx']} / {r['np']}")
    total = mt + nb + no + nw + npd + na + ne + nd
    L.append("")
    L.append(("PASS" if total == 0 else "FAIL") + f": {total} diferencias. Tiempo: {time.time() - t0:.0f} s.")
    txt = "\n".join(L) + "\n"
    print(txt)
    if a.salida:
        os.makedirs(os.path.dirname(a.salida), exist_ok=True)
        with open(a.salida, "w") as f:
            f.write(txt)
    sys.exit(0 if total == 0 else 1)


if __name__ == "__main__":
    main()
