#!/usr/bin/env python3
"""finales.py: veredicto e hipótesis de puntaje de las candidatas finales del aprendizaje en vivo, con la semilla 0.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

    python3 finales.py --arnes build/arnes --semilla 0 --salida mediciones

Para cada candidata (los alias de aprendiz.c):
  1. `veredicto --candidata X --referencia max_media --parada`, salida completa
     en mediciones/veredicto_<X>_s0.txt.
  2. El mismo veredicto en las 9 combinaciones de campo de rivales y G
     (../pruebas/veredictos.py), en mediciones/veredictos_9_s0.txt.
  3. `hipotesis` a 2000 ticks, a 20 000 con las series interiores y a 20 000
     con la vista de parada: salidas completas en mediciones/hipotesis_s0_*.txt
     y la tabla resumen mediciones/finales_s0.md, con H1 (patrimonio), H2
     (razón W/B&H), H3a y H3b, en evidencia y en estrés, como diferencia
     pareada contra max_media con su error.

Las filas `tabla:ka=0` y `mm_patron:apr=0` son los controles con el aprendizaje
apagado: tienen que dar cero en todas las columnas.

Solo usa la semilla 0. Las cifras con semilla reservada las corre el estudio
de cierre, una vez por candidata final.
"""
import argparse
import os
import subprocess
import sys

REF = "max_media"
FINALES = ["espera", "aprendiz", "aprendiz_patron"]             # lista corta para el estudio de cierre
INFORMATIVAS = ["aprendiz_rapido", "aprendiz_puro", "tabla:ka=0", "mm_patron:apr=0"]
VISTAS = ((2000, "todas"), (20000, "interiores"), (20000, "parada"))
CONJUNTOS = ("evidencia", "remuestreo", "plausibles", "estres")


def leer_tsv(ruta):
    d = {}
    with open(ruta, encoding="utf-8") as f:
        next(f)
        for linea in f:
            _, _, _, conjunto, cand, clave, valor = linea.rstrip("\n").split("\t")
            d.setdefault(cand, {}).setdefault(conjunto, {})[clave] = float(valor)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arnes", default="build/arnes")
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--salida", default="mediciones")
    a = ap.parse_args()
    if a.semilla != 0:
        sys.exit("este estudio usa solo la semilla 0")
    aqui = os.path.dirname(os.path.abspath(__file__))
    tmp = os.path.join(aqui, "build")
    os.makedirs(tmp, exist_ok=True)
    os.makedirs(a.salida, exist_ok=True)
    todas = FINALES + INFORMATIVAS

    # 1. Veredicto del criterio de corte, con la vista de parada.
    resumen = {}
    for c in FINALES + INFORMATIVAS[:2]:
        txt = subprocess.run([a.arnes, "veredicto", "--candidata", c, "--referencia", REF, "--semilla", str(a.semilla), "--parada"],
                             check=True, capture_output=True, text=True).stdout
        with open(os.path.join(a.salida, f"veredicto_{c}_s{a.semilla}.txt"), "w", encoding="utf-8") as f:
            f.write(txt)
        v = {}
        for linea in txt.splitlines():
            if linea.startswith("VEREDICTO"):
                clave, _, valor = linea.partition(":")
                v[clave.replace("VEREDICTO", "").strip() or "global"] = valor.split()[0]
            elif linea.startswith("Veredicto literal"):
                v["literal"] = linea.rsplit(":", 1)[1].strip()
        resumen[c] = v
        print(f"veredicto {c}: {v}", flush=True)

    # 2. Las 9 combinaciones de campo y G.
    script = os.path.join(aqui, "..", "pruebas", "veredictos.py")
    entorno = dict(os.environ, PROCESOS="2", HILOS_VEREDICTO="2")
    txt = subprocess.run([sys.executable, script, "--arnes", a.arnes, "--candidatas", ";".join(FINALES), "--referencia", REF,
                          "--semilla", str(a.semilla)], check=True, capture_output=True, text=True, env=entorno).stdout
    with open(os.path.join(a.salida, f"veredictos_9_s{a.semilla}.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    print("veredictos en las 9 combinaciones: listo", flush=True)

    # 3. Hipótesis de puntaje en los dos largos.
    datos = {}
    for largo, vista in VISTAS:
        tsv = os.path.join(tmp, f"finales_{largo}_{vista}.tsv")
        cmd = [a.arnes, "hipotesis", "--largo", str(largo), "--semilla", str(a.semilla), "--candidatos", ";".join([REF] + todas),
               "--ref", REF, "--tsv", tsv]
        if vista == "interiores":
            cmd.append("--interior")
        elif vista == "parada":
            cmd.append("--parada")
        txt = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
        with open(os.path.join(a.salida, f"hipotesis_s{a.semilla}_n{largo}_{vista}.txt"), "w", encoding="utf-8") as f:
            f.write(txt)
        datos[(largo, vista)] = leer_tsv(tsv)
        print(f"hipotesis {largo} {vista}: listo", flush=True)

    with open(os.path.join(a.salida, f"finales_s{a.semilla}.md"), "w", encoding="utf-8") as f:
        f.write(f"# Candidatas finales del aprendizaje en vivo contra `{REF}`, semilla {a.semilla}\n\n")
        f.write("Salida de `finales.py`. Campo mixto, G = 10. Diferencias pareadas contra la referencia, con su error estándar.\n")
        f.write("H1: patrimonio final. H2: razón W / comprar y mantener. H3a y H3b: puntos del torneo (0 a 2), lineal en patrimonio y en puesto.\n")
        f.write("p5: percentil 5 de la competencia de tres rondas.\n\n")
        f.write("## Veredicto del criterio de corte (`veredicto --parada`)\n\n")
        f.write("| Candidata | Especificación | 2000 ticks | 20 000 ticks | Global | Literal (solo el signo) |\n|---|---|---|---|---|---|\n")
        specs = {}
        for linea in subprocess.run([a.arnes, "listar"], check=True, capture_output=True, text=True).stdout.splitlines():
            p = linea.split()
            if len(p) >= 2 and p[0].startswith("cand:"):
                specs[p[0][5:]] = p[1]
        for c in FINALES + INFORMATIVAS[:2]:
            v = resumen[c]
            f.write(f"| `{c}` | `{specs.get(c, c)}` | {v.get('2000', '')} | {v.get('20000', '')} | **{v.get('global', '')}** | {v.get('literal', '')} |\n")
        for largo, vista in VISTAS:
            d = datos[(largo, vista)]
            r = d[REF]["evidencia"]
            f.write(f"\n## Rondas de {largo} ticks, series {vista}\n\n")
            f.write(f"`{REF}` en evidencia ({r['n']:.0f} series): patrimonio {r['h1_media']:.0f} (p5 {r['h1_p5']:.0f}), W/B&H {r['h2r_media']:.3f}, "
                    f"H3a {r['h3a_media']:.3f}, H3b {r['h3b_media']:.3f}, {r['ordenes']:.1f} órdenes por ronda.\n\n")
            for conj in CONJUNTOS:
                f.write(f"Conjunto {conj} ({d[REF][conj]['n']:.0f} series):\n\n")
                f.write("| Candidata | Órdenes | H1 | H2 (razón) | H3a | H3b | p5 H3a | p5 H3b |\n|---|---|---|---|---|---|---|---|\n")
                for c in todas:
                    x = d[c][conj]
                    f.write(f"| `{c}` | {x['ordenes']:.1f} | {x['h1_dif']:+.0f} ± {x['h1_dif_ee']:.0f} | {x['h2r_dif']:+.3f} ± {x['h2r_dif_ee']:.3f} | "
                            f"{x['d_h3a']:+.3f} ± {x['d_h3a_ee']:.3f} | {x['d_h3b']:+.3f} ± {x['d_h3b_ee']:.3f} | "
                            f"{x['d_h3a_c_p5']:+.3f} ± {x['d_h3a_c_p5_ee']:.3f} | {x['d_h3b_c_p5']:+.3f} ± {x['d_h3b_c_p5_ee']:.3f} |\n")
                f.write("\n")
    print("tabla: " + os.path.join(a.salida, f"finales_s{a.semilla}.md"))


if __name__ == "__main__":
    main()
