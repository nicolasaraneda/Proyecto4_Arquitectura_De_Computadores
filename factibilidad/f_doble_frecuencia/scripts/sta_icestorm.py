#!/usr/bin/env python3
"""sta_icestorm.py: análisis de tiempos sobre la netlist de icetime, con esquinas y flancos.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.

nextpnr e icetime entregan un solo número por reloj: la ruta más lenta, con
el retardo máximo de la base de tiempos y suponiendo un reloj ideal con ciclo
de trabajo de 50 %. Para el reloj doblado por lógica eso no alcanza, porque
hay que saber cuánto dura el pulso que fabrica la cadena de LUT, cuánto
cambia con la esquina de proceso, voltaje y temperatura, y cuánto tiempo
tiene cada tipo de ruta (subida a subida, subida a bajada, bajada a subida).

Este script lee:
  - la netlist que escribe `icetime -o` desde el .asc ya ruteado. Trae cada
    celda lógica con el pin físico que usó el ruteo y cada tramo de
    interconexión como una celda aparte (LocalMux, InMux, Span4Mux_*, ...);
  - la base de tiempos de icestorm (share/icebox/timings_hx1k.txt), que da
    para cada arco tres valores (mínimo, típico y máximo) de subida y bajada;
  - opcionalmente la netlist que escribe nextpnr con --write, de donde se
    saca qué memorias y qué flip-flops usan el reloj invertido (icetime no lo
    informa).

Y calcula:
  1. Rutas de datos: la peor ruta de cada clase (flanco de lanzamiento y
     flanco de captura), incluyendo el retardo de reloj a salida y el tiempo
     de setup, con reloj ideal. Usa el mayor entre subida y bajada de cada
     arco, igual que icetime.
  2. Red de reloj: si entre un pin de entrada y un buffer global hay lógica
     (el duplicador), simula un flanco de subida y uno de bajada de ese pin
     por la red, con retardos distintos de subida y de bajada, y entrega
     cuándo sube y cuándo baja el reloj generado. De ahí salen el ancho del
     pulso y la latencia para cada flanco de la entrada.
  3. Con las dos cosas, la holgura de cada clase de ruta para un período de
     entrada y un ciclo de trabajo dados, en las tres esquinas.
  4. Lazos combinacionales (el oscilador en anillo de la prueba de placa):
     el período de cada lazo simple, sumando el retardo de subida y el de
     bajada de cada arco, en las tres esquinas.

Con --fijar PIN=VALOR se deja una entrada en un valor constante durante la
simulación de la red de reloj. Sirve para la prueba de placa, donde los
botones eligen la toma de la cadena.

Uso:
  sta_icestorm.py NETLIST_ICETIME.v [--pnr-json POST_PNR.json]
                  [--pin i_Clk] [--periodo-ns 40] [--duty 45,50,55]
                  [--fijar PIN=VALOR ...] [--json SALIDA.json] [--rutas]
"""
import argparse
import collections
import json
import os
import re
import sys

ESQUINAS = ("min", "tip", "max")
TIEMPOS_DEF = os.path.join(os.environ.get("OSS_CAD_SUITE", "/usr/local"), "share/icebox/timings_hx1k.txt")

# Celdas de interconexión: un arco I -> O
BUFFERS = {
    "CascadeBuf", "CascadeMux", "CEMux", "ClkMux", "gio2CtrlBuf", "Glb2LocalMux",
    "GlobalMux", "InMux", "IoInMux", "IoSpan4Mux", "LocalMux", "Odrv4", "Odrv12",
    "Sp12to4", "SRMux", "INV",
}


def leer_tiempos(ruta):
    """Devuelve {celda: {"IOPATH": {(de, a): (sube, baja)}, "SETUP": {(pin, reloj): t}}}.

    sube, baja y t son ternas (mínimo, típico, máximo) en picosegundos.
    """
    celdas = {}
    cel = None

    def terna(s):
        return tuple(0.0 if x == "*" else float(x) for x in s.split(":"))

    with open(ruta) as f:
        for linea in f:
            p = linea.split()
            if not p:
                continue
            if p[0] == "CELL":
                cel = celdas.setdefault(p[1], {"IOPATH": {}, "SETUP": {}})
            elif p[0] == "IOPATH":
                k = (p[1], p[2])
                s, b = terna(p[3]), terna(p[4])
                if k in cel["IOPATH"]:               # arcos repetidos: se toma el mayor
                    s0, b0 = cel["IOPATH"][k]
                    s = tuple(max(x, y) for x, y in zip(s, s0))
                    b = tuple(max(x, y) for x, y in zip(b, b0))
                cel["IOPATH"][k] = (s, b)
            elif p[0] == "SETUP":
                pin = p[1].split(":")[1]
                rel = p[2].split(":")[1]
                t = terna(p[3])
                k = (pin, rel)
                if k in cel["SETUP"]:
                    t = tuple(max(x, y) for x, y in zip(t, cel["SETUP"][k]))
                cel["SETUP"][k] = t
    return celdas


RE_INST = re.compile(r"^  (\w+) (?:#\(\n(.*?)\n  \) )?(\S+) \(\n(.*?)\n  \);", re.S | re.M)
RE_PUERTO = re.compile(r"^\s*\.(\w+)\((.*?)\),?\s*$")
RE_ASSIGN = re.compile(r"^  assign (\S+) = (\S+);", re.M)
CONSTANTES = {"gnd", "vcc", ""}


def leer_netlist(ruta):
    """Lee la netlist de icetime. Devuelve (instancias, asignaciones).

    instancias: lista de (tipo, nombre, parámetros, puertos). Los puertos que
    son buses (memorias) quedan como lista de redes, con el bit más alto
    primero, igual que en el archivo.
    """
    texto = open(ruta).read()
    # icetime nombra cada tramo de una red global con su bloque
    # (seg_X_Y_glb_netwk_K_N) y no los une entre sí. El número final es el
    # índice de la red: todos los tramos con el mismo N son net_N.
    texto = re.sub(r"\bseg_\d+_\d+_glb_netwk_\d+_(\d+)\b", r"net_\1", texto)
    insts = []
    for m in RE_INST.finditer(texto):
        tipo, pars, nombre, cuerpo = m.groups()
        if tipo in ("module", "wire", "assign", "inout", "input", "output"):
            continue
        params = {}
        if pars:
            for linea in pars.split("\n"):
                mp = RE_PUERTO.match(linea)
                if mp:
                    params[mp.group(1)] = mp.group(2)
        puertos = {}
        for linea in cuerpo.split("\n"):
            mp = RE_PUERTO.match(linea)
            if not mp:
                continue
            v = mp.group(2).strip()
            if v.startswith("{"):
                puertos[mp.group(1)] = [x.strip() for x in v[1:-1].split(",")]
            else:
                puertos[mp.group(1)] = v
        insts.append((tipo, nombre, params, puertos))
    asigs = RE_ASSIGN.findall(texto)
    return insts, asigs


def leer_invertidos(ruta_json):
    """Elementos con reloj invertido según la netlist de nextpnr (--write).

    Devuelve (memorias con lectura invertida, memorias con escritura
    invertida, celdas lógicas con reloj invertido), con los nombres que usa
    icetime: ram_X_Y y lc40_X_Y_Z.
    """
    ram_r, ram_w, lc = set(), set(), set()
    if not ruta_json:
        return ram_r, ram_w, lc
    j = json.load(open(ruta_json))
    mod = list(j["modules"].values())[0]
    for c in mod["cells"].values():
        bel = c["attributes"].get("NEXTPNR_BEL", "")
        m = re.match(r"X(\d+)/Y(\d+)/(\w+)", bel)
        if not m:
            continue
        x, y, z = m.groups()
        par = c.get("parameters", {})

        def uno(k):
            v = par.get(k, "0")
            return isinstance(v, str) and v.strip("0") != "" or v == 1

        if c["type"] == "ICESTORM_RAM":
            if uno("NEG_CLK_R"):
                ram_r.add("ram_%s_%s" % (x, y))
            if uno("NEG_CLK_W"):
                ram_w.add("ram_%s_%s" % (x, y))
        elif c["type"] == "ICESTORM_LC" and uno("NEG_CLK") and uno("DFF_ENABLE"):
            lc.add("lc40_%s_%s_%s" % (x, y, z[2:]))
    return ram_r, ram_w, lc


class Diseno:
    """Grafo de tiempos: arcos combinacionales, lanzamientos y capturas."""

    def __init__(self, insts, asigs, tiempos, invertidos=(set(), set(), set())):
        self.t = tiempos
        self.arcos = collections.defaultdict(list)    # destino -> [(origen, sube, baja, etiqueta)]
        self.salen = collections.defaultdict(list)    # origen -> [(destino, sube, baja, etiqueta)]
        self.lanza = []      # (red q, red reloj, retardo, flanco, instancia)
        self.captura = []    # (red d, red reloj, setup, flanco, instancia.pin)
        self.luts = {}       # salida -> (instancia, init, [in0..in3])
        self.pads_in = {}    # nombre del pin -> red DIN0
        self.gb = []         # (red de entrada, red de salida, instancia)
        self.cero = (0.0, 0.0, 0.0)
        self.fijos = {}      # red -> valor constante (entradas fijadas con --fijar)
        ram_r, ram_w, lc_neg = invertidos
        pad_de = {}          # red interna del pad -> nombre del pin

        for tipo, nombre, par, pu in insts:
            if tipo == "IO_PAD":
                # PACKAGEPIN es el pin. DOUT del pad va a PADIN del PRE_IO.
                pad_de[pu.get("DOUT", "")] = pu.get("PACKAGEPIN", "")
        for tipo, nombre, par, pu in insts:
            if tipo in BUFFERS or tipo.startswith("Span"):
                s, b = self.t[tipo]["IOPATH"][("I", "O")]
                self._arco(pu["I"], pu["O"], s, b, "%s (%s)" % (nombre, tipo))
            elif tipo == "ICE_GB":
                s, b = self.t[tipo]["IOPATH"][("USERSIGNALTOGLOBALBUFFER", "GLOBALBUFFEROUTPUT")]
                e, o = pu["USERSIGNALTOGLOBALBUFFER"], pu["GLOBALBUFFEROUTPUT"]
                self._arco(e, o, s, b, "%s (ICE_GB)" % nombre)
                self.gb.append((e, o, nombre))
            elif tipo == "ICE_CARRY_IN_MUX":
                s, b = self.t[tipo]["IOPATH"][("carryinitin", "carryinitout")]
                self._arco(pu.get("carryinitin", ""), pu.get("carryinitout", ""), s, b,
                           "%s (ICE_CARRY_IN_MUX)" % nombre)
            elif tipo == "PRE_IO":
                # Entrada: PADIN -> DIN0. La red PADIN es la salida del IO_PAD.
                din = pu.get("DIN0", "")
                pin = pad_de.get(pu.get("PADIN", ""), "")
                if din and pin:
                    self.pads_in[pin] = (din, self.t["PRE_IO"]["IOPATH"][("PADIN", "DIN0")],
                                         self.t["IO_PAD"]["IOPATH"][("PACKAGEPIN", "DOUT")])
            elif tipo == "LogicCell40":
                self._celda_logica(nombre, par, pu, nombre in lc_neg)
            elif tipo == "SB_RAM40_4K":
                self._memoria(nombre, pu, nombre in ram_r, nombre in ram_w)
        for izq, der in asigs:
            self._arco(der, izq, self.cero, self.cero, "")

    def _arco(self, a, b, sube, baja, etiqueta):
        if a in CONSTANTES or b in CONSTANTES or a == b:
            return
        self.arcos[b].append((a, sube, baja, etiqueta))
        self.salen[a].append((b, sube, baja, etiqueta))

    def _celda_logica(self, nombre, par, pu, neg):
        io = self.t["LogicCell40"]["IOPATH"]
        st = self.t["LogicCell40"]["SETUP"]
        seq = par.get("SEQ_MODE", "4'b0000").split("b")[1][0] == "1"
        carry = par.get("C_ON", "1'b0").endswith("1")
        ins = [pu.get("in%d" % i, "") for i in range(4)]
        lcout, ltout = pu.get("lcout", ""), pu.get("ltout", "")
        init = par.get("LUT_INIT", "16'b0").split("b")[1]
        for i, n in enumerate(ins):
            if n in CONSTANTES:
                continue
            if not seq and lcout:
                s, b = io[("in%d" % i, "lcout")]
                self._arco(n, lcout, s, b, "%s (LogicCell40) in%d -> lcout" % (nombre, i))
            if ltout:
                s, b = io[("in%d" % i, "ltout")]
                self._arco(n, ltout, s, b, "%s (LogicCell40) in%d -> ltout" % (nombre, i))
            if seq:
                self.captura.append((n, pu.get("clk", ""), st[("in%d" % i, "clk")],
                                     "neg" if neg else "pos", "%s.in%d" % (nombre, i)))
        if not seq and lcout:
            self.luts[lcout] = (nombre, init, ins)
        if carry and pu.get("carryout", ""):
            for p in ("carryin", "in1", "in2"):
                n = pu.get(p, "")
                if n not in CONSTANTES:
                    s, b = io[(p, "carryout")]
                    self._arco(n, pu["carryout"], s, b, "%s (LogicCell40) %s -> carryout" % (nombre, p))
        if seq:
            s, b = io[("posedge:clk", "lcout")]
            d = tuple(max(x, y) for x, y in zip(s, b))
            if lcout:
                self.lanza.append((lcout, pu.get("clk", ""), d, "neg" if neg else "pos", nombre))
            for p in ("ce", "sr"):
                n = pu.get(p, "")
                if n not in CONSTANTES:
                    self.captura.append((n, pu.get("clk", ""), st[(p, "clk")],
                                         "neg" if neg else "pos", "%s.%s" % (nombre, p)))

    def _memoria(self, nombre, pu, neg_r, neg_w):
        io = self.t["SB_RAM40_4K"]["IOPATH"]
        st = self.t["SB_RAM40_4K"]["SETUP"]

        def bits(p):
            v = pu.get(p, [])
            v = v if isinstance(v, list) else [v]
            n = len(v)
            return [(n - 1 - i, x) for i, x in enumerate(v)]    # (índice, red)

        fr = "neg" if neg_r else "pos"
        fw = "neg" if neg_w else "pos"
        for i, n in bits("RDATA"):
            if n.startswith("dangling") or n in CONSTANTES:
                continue
            s, b = io[("posedge:RCLK", "RDATA[%d]" % i)]
            d = tuple(max(x, y) for x, y in zip(s, b))
            self.lanza.append((n, pu.get("RCLK", ""), d, fr, nombre))
        for p, rel, fl in (("RADDR", "RCLK", fr), ("WADDR", "WCLK", fw),
                           ("WDATA", "WCLK", fw), ("MASK", "WCLK", fw)):
            for i, n in bits(p):
                if n.startswith("dangling") or n in CONSTANTES:
                    continue
                self.captura.append((n, pu.get(rel, ""), st[("%s[%d]" % (p, i), rel)], fl,
                                     "%s.%s[%d]" % (nombre, p, i)))
        for p, rel, fl in (("RE", "RCLK", fr), ("RCLKE", "RCLK", fr),
                           ("WE", "WCLK", fw), ("WCLKE", "WCLK", fw)):
            n = pu.get(p, "")
            if isinstance(n, str) and n not in CONSTANTES and not n.startswith("dangling"):
                self.captura.append((n, pu.get(rel, ""), st[(p, rel)], fl, "%s.%s" % (nombre, p)))

    def fijar(self, pin, valor):
        """Deja el pin de entrada en un valor constante para la simulación de la red de reloj.

        El valor se propaga por los tramos de interconexión (un solo origen
        por red) hasta las entradas de las LUT.
        """
        if pin not in self.pads_in:
            raise SystemExit("--fijar: el pin %s no es una entrada del diseño" % pin)
        pila = [self.pads_in[pin][0]]
        while pila:
            n = pila.pop()
            if n in self.fijos:
                continue
            self.fijos[n] = valor
            for (b, _, _, _) in self.salen.get(n, ()):
                if b not in self.luts and len(self.arcos[b]) == 1:
                    pila.append(b)

    def lazos(self):
        """Lazos combinacionales simples. Devuelve [(cantidad de redes, [período por esquina en ps])].

        En un período del oscilador cada red sube una vez y baja una vez, así
        que el período es la suma del retardo de subida y el de bajada de
        todos los arcos del lazo.
        """
        en_orden = set(self.orden_topologico())
        resto = (set(self.arcos) | set(self.salen)) - en_orden
        cambio = True
        while cambio:                       # quita lo que cuelga del lazo sin volver a él
            cambio = False
            for n in list(resto):
                if not any(b in resto for (b, _, _, _) in self.salen.get(n, ())):
                    resto.discard(n)
                    cambio = True
        res = []
        while resto:
            ini = next(iter(resto))
            per = [0.0, 0.0, 0.0]
            n, visto = ini, []
            simple = True
            while True:
                pred = [(a, s, b) for (a, s, b, _) in self.arcos.get(n, ()) if a in resto]
                if not pred or len({a for (a, _, _) in pred}) != 1:
                    simple = False
                    break
                a, s, b = max(pred, key=lambda x: x[1][2] + x[2][2])
                for ci in range(3):
                    per[ci] += s[ci] + b[ci]
                visto.append(n)
                n = a
                if n == ini:
                    break
                if n in visto:
                    simple = False
                    break
            if not simple:
                break
            res.append((len(visto), per))
            resto -= set(visto)
        return res

    # ------------------------------------------------------------------ rutas de datos
    def orden_topologico(self):
        grado = collections.Counter()
        nodos = set(self.arcos) | set(self.salen)
        for b in self.arcos:
            grado[b] = len(self.arcos[b])
        cola = [n for n in nodos if grado[n] == 0]
        orden = []
        while cola:
            n = cola.pop()
            orden.append(n)
            for (b, _, _, _) in self.salen.get(n, ()):
                grado[b] -= 1
                if grado[b] == 0:
                    cola.append(b)
        self.ciclos = len(nodos) - len(orden)      # nodos en lazos combinacionales
        return orden

    def raiz_reloj(self, red):
        """Sigue la red de reloj hacia atrás hasta la salida de un buffer global."""
        gb_out = {o for (_, o, _) in self.gb}
        visto = 0
        while red not in gb_out and len(self.arcos.get(red, ())) == 1 and visto < 50:
            red = self.arcos[red][0][0]
            visto += 1
        return red

    def rutas(self, esquina=2):
        """Peor ruta por clase. Devuelve {(reloj lanza, flanco, reloj captura, flanco): (retardo, camino)}."""
        orden = self.orden_topologico()
        raiz = {}

        def r(red):
            if red not in raiz:
                raiz[red] = self.raiz_reloj(red)
            return raiz[red]

        res = {}
        clases = sorted({(r(c), f) for (_, c, _, f, _) in self.lanza})
        for (rl, fl) in clases:
            lleg = {}
            prev = {}
            for (q, c, d, f, inst) in self.lanza:
                if r(c) == rl and f == fl and d[esquina] > lleg.get(q, -1.0):
                    lleg[q] = d[esquina]
                    prev[q] = (None, "%s reloj -> salida" % inst, d[esquina])
            for n in orden:
                if n not in lleg:
                    continue
                t0 = lleg[n]
                for (b, s, ba, et) in self.salen.get(n, ()):
                    d = max(s[esquina], ba[esquina])
                    if t0 + d > lleg.get(b, -1.0):
                        lleg[b] = t0 + d
                        prev[b] = (n, et, d)
            for (dn, c, su, f, pin) in self.captura:
                if dn not in lleg:
                    continue
                k = (rl, fl, r(c), f)
                tot = lleg[dn] + su[esquina]
                if k not in res or tot > res[k][0]:
                    camino = [("setup " + pin, su[esquina])]
                    n = dn
                    while n is not None:
                        pn, et, d = prev[n]
                        if et:
                            camino.append((et, d))
                        n = pn
                    res[k] = (tot, list(reversed(camino)))
        return res

    # ------------------------------------------------------------------ red de reloj
    def cono_reloj(self, pin):
        """Redes entre el pin de entrada y los buffers globales que alcanza por lógica."""
        if pin not in self.pads_in:
            return None
        din = self.pads_in[pin][0]
        alcanza = set()
        pila = [din]
        while pila:
            n = pila.pop()
            if n in alcanza:
                continue
            alcanza.add(n)
            for (b, _, _, _) in self.salen.get(n, ()):
                pila.append(b)
        return [(e, o, nom) for (e, o, nom) in self.gb if e in alcanza]

    def simular_flanco(self, pin, sube, gb_in, esquina):
        """Propaga un flanco del pin hasta gb_in. Devuelve [(tiempo ps, valor nuevo)].

        Parte del estado estable con el pin en el valor contrario. Retardo de
        transporte: cada arco retrasa según el sentido del cambio en su
        salida (subida o bajada).
        """
        din, t_pre, t_pad = self.pads_in[pin]
        # Redes del cono, en orden topológico restringido
        orden = [n for n in self.orden_topologico()]
        alcanza = set()
        pila = [din]
        while pila:
            n = pila.pop()
            if n in alcanza:
                continue
            alcanza.add(n)
            for (b, _, _, _) in self.salen.get(n, ()):
                pila.append(b)
        # Solo interesan las redes que además llegan a gb_in
        llega = set()
        pila = [gb_in]
        while pila:
            n = pila.pop()
            if n in llega:
                continue
            llega.add(n)
            for (a, _, _, _) in self.arcos.get(n, ()):
                pila.append(a)
        cono = [n for n in orden if n in alcanza and n in llega]

        def evaluar(valores, n):
            if n in self.luts:
                _, init, ins = self.luts[n]
                idx = 0
                for i, x in enumerate(ins):
                    v = 1 if x == "vcc" else 0 if x in CONSTANTES else valores.get(x, self.fijos.get(x, 0))
                    idx |= v << i
                return int(init[len(init) - 1 - idx])
            a = self.arcos[n][0][0]
            return valores[a]

        # Estado estable inicial
        ini = {din: 0 if sube else 1}
        for n in cono:
            if n != din:
                ini[n] = evaluar(ini, n)
        # Simulación por eventos: (tiempo, red, valor)
        eventos = []
        d0 = (t_pad[0 if sube else 1][esquina] + t_pre[0 if sube else 1][esquina])
        eventos.append((d0, din, 1 if sube else 0))
        val = dict(ini)
        forma = {n: [] for n in cono}
        import heapq
        heapq.heapify(eventos)
        pasos = 0
        while eventos and pasos < 100000:
            pasos += 1
            t, n, v = heapq.heappop(eventos)
            if val[n] == v:
                continue
            val[n] = v
            forma[n].append((t, v))
            for (b, s, ba, _) in self.salen.get(n, ()):
                if b not in forma:
                    continue
                nv = evaluar(val, b)
                # El valor de b que ya está programado es el último evento pendiente o el actual
                pend = [e for e in eventos if e[1] == b]
                ult = max(pend)[2] if pend else val[b]
                if nv != ult:
                    d = s[esquina] if nv == 1 else ba[esquina]
                    heapq.heappush(eventos, (t + d, b, nv))
        return forma[gb_in], ini[gb_in]


def analizar_reloj(dis, pin):
    """Para cada buffer global alimentado por lógica desde el pin: pulso y latencia."""
    salida = []
    gbs = dis.cono_reloj(pin)
    if not gbs:
        return salida
    for (e, o, nom) in gbs:
        s_gb, b_gb = dis.t["ICE_GB"]["IOPATH"][("USERSIGNALTOGLOBALBUFFER", "GLOBALBUFFEROUTPUT")]
        fila = {"gb": nom, "red": o, "esquinas": {}}
        for ci, cn in enumerate(ESQUINAS):
            datos = {}
            for sube in (True, False):
                forma, v0 = dis.simular_flanco(pin, sube, e, ci)
                k = "sube" if sube else "baja"
                datos[k] = {"inicial": v0, "eventos": [(round(t, 1), v) for t, v in forma]}
            # ¿Es un duplicador? Un pulso (0 -> 1 -> 0) con cada flanco de entrada
            dup = all(datos[k]["inicial"] == 0 and [v for _, v in datos[k]["eventos"]] == [1, 0]
                      for k in ("sube", "baja"))
            datos["duplicador"] = dup
            if dup:
                for k in ("sube", "baja"):
                    (t1, _), (t0, _) = datos[k]["eventos"]
                    # hasta la salida del buffer global: el flanco de subida del pulso
                    # usa el retardo de subida del buffer y el de bajada, el de bajada
                    datos[k]["latencia_ps"] = round(t1 + s_gb[ci], 1)
                    datos[k]["ancho_ps"] = round((t0 + b_gb[ci]) - (t1 + s_gb[ci]), 1)
            fila["esquinas"][cn] = datos
        salida.append(fila)
    return salida


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("netlist")
    ap.add_argument("--tiempos", default=TIEMPOS_DEF)
    ap.add_argument("--pnr-json", default=None, help="netlist de nextpnr (--write), para los relojes invertidos")
    ap.add_argument("--pin", default="i_Clk", help="pin de entrada del reloj")
    ap.add_argument("--periodo-ns", type=float, default=40.0)
    ap.add_argument("--duty", default="45,50,55", help="ciclos de trabajo del oscilador, en %")
    ap.add_argument("--fijar", action="append", default=[], metavar="PIN=VALOR",
                    help="entrada constante durante la simulación de la red de reloj (se puede repetir)")
    ap.add_argument("--json", default=None, help="escribir el resultado completo")
    ap.add_argument("--rutas", action="store_true", help="imprimir la peor ruta de cada clase, tramo a tramo")
    a = ap.parse_args(argv)

    tiempos = leer_tiempos(a.tiempos)
    insts, asigs = leer_netlist(a.netlist)
    dis = Diseno(insts, asigs, tiempos, leer_invertidos(a.pnr_json))
    for f in a.fijar:
        pin, _, val = f.partition("=")
        dis.fijar(pin, int(val))
    res = {"netlist": a.netlist, "celdas": len(insts), "fijos": a.fijar}

    print("Netlist: %s (%d celdas, %d lanzamientos, %d capturas)" %
          (a.netlist, len(insts), len(dis.lanza), len(dis.captura)))

    # 1. Rutas de datos
    res["rutas"] = {}
    por_esq = [dis.rutas(ci) for ci in range(3)]
    if dis.ciclos:
        print("AVISO: %d redes en lazos combinacionales, no analizadas" % dis.ciclos)
    print("\nPeor ruta por clase, con reloj ideal (ns, incluye reloj a salida y setup):")
    print("  %-34s %8s %8s %8s" % ("lanza -> captura", "min", "tip", "max"))
    for k in sorted(por_esq[2]):
        rl, fl, rc, fc = k
        nombre = "%s %s -> %s %s" % (fl, rl, fc, rc) if rl != rc else "%s -> %s (%s)" % (fl, fc, rl)
        v = [por_esq[ci][k][0] / 1000.0 for ci in range(3)]
        print("  %-34s %8.2f %8.2f %8.2f" % (nombre[:34], v[0], v[1], v[2]))
        res["rutas"]["%s>%s" % (fl, fc) if rl == rc else nombre] = {
            "reloj_lanza": rl, "reloj_captura": rc, "min": v[0], "tip": v[1], "max": v[2]}
        if a.rutas:
            for et, d in por_esq[2][k][1]:
                print("      %7.3f  %s" % (d / 1000.0, et))

    # 2. Red de reloj
    relojes = analizar_reloj(dis, a.pin)
    res["reloj"] = relojes
    for fila in relojes:
        print("\nRed de reloj desde el pin %s hasta el buffer global %s:" % (a.pin, fila["gb"]))
        for cn in ESQUINAS:
            d = fila["esquinas"][cn]
            if not d["duplicador"]:
                ev = [d[k]["eventos"] for k in ("sube", "baja")]
                if all(len(e) == 1 for e in ev):
                    print("  %s: sigue al pin sin doblarlo (retardo hasta la entrada del buffer: %.2f ns al subir, %.2f ns al bajar)" %
                          (cn, ev[0][0][0] / 1000, ev[1][0][0] / 1000))
                else:
                    print("  %s: no se comporta como duplicador: %s" % (cn, json.dumps(d)))
                continue
            print("  %s: flanco de subida de %s: latencia %.2f ns, pulso %.2f ns | "
                  "flanco de bajada: latencia %.2f ns, pulso %.2f ns" %
                  (cn, a.pin, d["sube"]["latencia_ps"] / 1000, d["sube"]["ancho_ps"] / 1000,
                   d["baja"]["latencia_ps"] / 1000, d["baja"]["ancho_ps"] / 1000))

    # 3. Holguras con el reloj doblado
    dups = [f for f in relojes if all(f["esquinas"][c]["duplicador"] for c in ESQUINAS)]
    if dups:
        fila = dups[0]
        T = a.periodo_ns
        res["holguras"] = []
        print("\nHolgura con el reloj doblado, período de entrada %.1f ns (ns; negativa = no cierra):" % T)
        print("  %-6s %-5s %9s %9s | %-22s %9s %9s %9s" %
              ("duty", "esq.", "período A", "período B", "clase", "necesita", "dispone", "holgura"))
        for duty in [float(x) for x in a.duty.split(",")]:
            for ci, cn in enumerate(ESQUINAS):
                d = fila["esquinas"][cn]
                lr, lf = d["sube"]["latencia_ps"] / 1000, d["baja"]["latencia_ps"] / 1000
                wr, wf = d["sube"]["ancho_ps"] / 1000, d["baja"]["ancho_ps"] / 1000
                ta = T * duty / 100 + (lf - lr)          # del flanco de subida de la entrada al de bajada
                tb = T * (100 - duty) / 100 - (lf - lr)  # del de bajada al de subida siguiente
                disp = {"pos>pos": min(ta, tb), "neg>neg": min(ta, tb),
                        "pos>neg": min(wr, wf), "neg>pos": min(ta - wr, tb - wf)}
                for k in sorted(por_esq[ci]):
                    rl, fl, rc, fc = k
                    if rl != fila["red"] or rc != fila["red"]:
                        continue
                    clase = "%s>%s" % (fl, fc)
                    nec = por_esq[ci][k][0] / 1000.0
                    hol = disp[clase] - nec
                    print("  %-6s %-5s %9.2f %9.2f | %-22s %9.2f %9.2f %9.2f" %
                          ("%g %%" % duty, cn, ta, tb, clase, nec, disp[clase], hol))
                    res["holguras"].append({"duty": duty, "esquina": cn, "periodo_a": ta, "periodo_b": tb,
                                            "clase": clase, "necesita": nec, "dispone": disp[clase],
                                            "holgura": hol})
    # 4. Lazos combinacionales
    res["lazos"] = []
    for (n, per) in dis.lazos():
        print("\nLazo combinacional de %d redes: período %.2f ns (mín), %.2f ns (típ), %.2f ns (máx)" %
              (n, per[0] / 1000, per[1] / 1000, per[2] / 1000))
        res["lazos"].append({"redes": n, "periodo_ns": {"min": per[0] / 1000, "tip": per[1] / 1000,
                                                         "max": per[2] / 1000}})
    if a.json:
        json.dump(res, open(a.json, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
