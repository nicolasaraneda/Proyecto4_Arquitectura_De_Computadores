#!/usr/bin/env python3
"""pruebas.py: tres pruebas de práctica de 15 preguntas tomadas del banco de la defensa, con su pauta.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

Lee docs/defensa/preguntas.md y arma docs/defensa/pruebas_practica.md: tres pruebas
de 15 preguntas, sin repetir preguntas entre ellas. Cada prueba tiene la misma mezcla
(7 básicas, 5 avanzadas y 3 incómodas) y toca todas las secciones del banco que pueda,
para que nadie se prepare solo su pieza. La pauta es la respuesta escrita del banco y
su dato (archivo:línea). Si el banco cambia, se corre de nuevo: la elección es
reproducible (semilla fija) y no depende de qué preguntas se agregaron al final.

Uso: python3 tools/defensa/pruebas.py
"""
import os
import random
import re

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BANCO = os.path.join(RAIZ, "docs", "defensa", "preguntas.md")
SALIDA = os.path.join(RAIZ, "docs", "defensa", "pruebas_practica.md")
MEZCLA = {"B": 7, "A": 5, "I": 3}


def leer():
    seccion, preguntas, actual = None, [], None
    for linea in open(BANCO, encoding="utf-8").read().splitlines():
        m = re.match(r"^## (\d+)\. (.*)", linea)
        if m:
            seccion = (int(m.group(1)), m.group(2))
            continue
        m = re.match(r"^\*\*(\d+)\. \[([BAI])\] (.*)\*\*$", linea)
        if m:
            actual = dict(n=int(m.group(1)), tipo=m.group(2), texto=m.group(3), seccion=seccion, resp=[])
            preguntas.append(actual)
            continue
        if actual is not None:
            if linea.startswith("## ") or linea.startswith("---"):
                actual = None
            elif linea.strip():
                actual["resp"].append(linea)
    return preguntas


def elegir(preguntas):
    rng = random.Random(20261130)
    usadas = set()
    pruebas = []
    for _ in range(3):
        prueba = []
        for tipo, cuantas in MEZCLA.items():
            pool = [p for p in preguntas if p["tipo"] == tipo and p["n"] not in usadas]
            rng.shuffle(pool)
            # una por sección hasta completar, para cubrir el banco entero
            vistas, elegidas = set(), []
            for p in pool:
                if len(elegidas) == cuantas:
                    break
                if p["seccion"][0] not in vistas:
                    elegidas.append(p)
                    vistas.add(p["seccion"][0])
            for p in pool:
                if len(elegidas) == cuantas:
                    break
                if p not in elegidas:
                    elegidas.append(p)
            prueba += elegidas
            usadas |= {p["n"] for p in elegidas}
        prueba.sort(key=lambda p: (p["seccion"][0], p["n"]))
        pruebas.append(prueba)
    return pruebas


def main():
    preguntas = leer()
    pruebas = elegir(preguntas)
    L = ["# Pruebas de práctica para la defensa", "", "Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.", "",
         f"Tres pruebas de 15 preguntas tomadas del banco (`docs/defensa/preguntas.md`, {len(preguntas)} preguntas), "
         "sin repetir entre ellas. Cada una tiene 7 básicas [B], 5 avanzadas [A] y 3 incómodas [I], repartidas por todas "
         "las secciones del banco. Las genera `python3 tools/defensa/pruebas.py`; si el banco cambia, se generan de nuevo.", "",
         "**Cómo se usan.** Uno lee las preguntas en voz alta, sin mostrar la pauta. El que responde tiene unos 20 segundos "
         "por pregunta y no mira nada. Puntaje por pregunta: 2 si da la idea y el dato (la cifra o el archivo), 1 si da la "
         "idea sin el dato, 0 si no. Una prueba vale 30 puntos. Las [B] que fallen se repiten en el repaso siguiente; las [A] "
         "se le pasan al dueño de la pieza (`docs/defensa/plan_estudio.md`, sección 2).", "",
         "Sugerencia de uso con el plan de estudio: la prueba 1 en el repaso del 21/11, la 2 en el del 24/11 y la 3 en el "
         "ensayo del 30/11, cada vez a alguien que no es dueño de la mayoría de las preguntas.", ""]
    for k, prueba in enumerate(pruebas, 1):
        L += [f"## Prueba {k}", ""]
        for i, p in enumerate(prueba, 1):
            L.append(f"{i}. [{p['tipo']}] {p['texto']} *(pregunta {p['n']}, sección {p['seccion'][0]})*")
        L.append("")
    for k, prueba in enumerate(pruebas, 1):
        L += [f"## Pauta de la prueba {k}", ""]
        for i, p in enumerate(prueba, 1):
            L.append(f"**{i}. [{p['tipo']}] {p['texto']}** (pregunta {p['n']})")
            L += p["resp"]
            L.append("")
    with open(SALIDA, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L).rstrip("\n") + "\n")
    print(f"{os.path.relpath(SALIDA, RAIZ)}: 3 pruebas de 15 preguntas de un banco de {len(preguntas)}")


if __name__ == "__main__":
    main()
