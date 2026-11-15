"""Tests de la extensión xd: emad, devk y mulstep en el opcode custom-0.

La especificación está en docs/extension_isa.md y el resumen para el
ensamblador en docs/ensamblador.md. Se verifican las tres palabras de
referencia, todos los registros en cada campo con ida y vuelta por el
desensamblador, el rechazo de k distinto de 5, las dos formas de habilitar la
extensión y que un programa que no la usa ensambla igual que antes.

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.
Arquitectura de Computadores, Universidad de los Andes, 2026-2.
"""

import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pochoasm import main  # noqa: E402
from core import (  # noqa: E402
    assemble_file,
    assemble_text,
    format_hex,
    format_verilog_image,
    format_verilog_rom,
)
from disasm import decode_one, disassemble  # noqa: E402
from errors import AssemblerError  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]

GOLDEN = [
    ("emad x3, x6, x3, 5", 0x0A33418B),
    ("devk x6, x5, x3, 5", 0x0A32D30B),
    ("mulstep x7, x7, x8", 0x0083A38B),
]

PROGRAMA = """\
.extension xd
.equ K, 5
inicio:
    addi x6, x0, 100
    emad x3, x6, x3, K
    devk x6, x5, x3, 5
    mulstep x7, x7, x8
    j inicio
"""


def xd(text, **kw):
    return assemble_text(text, xd=True, **kw)


def chunks(lines, n=512):
    for i in range(0, len(lines), n):
        yield lines[i:i + n]


class GoldenTests(unittest.TestCase):
    def test_palabras_de_referencia(self):
        for text, word in GOLDEN:
            with self.subTest(text=text):
                self.assertEqual(xd(text + "\n"), [word])

    def test_desensamblado_de_referencia(self):
        for text, word in GOLDEN:
            with self.subTest(text=text):
                self.assertEqual(decode_one(word, 0), text)

    def test_nombres_abi_y_mayusculas(self):
        self.assertEqual(xd("EMAD gp, t1, gp, 5\n"), [0x0A33418B])
        self.assertEqual(xd("devk t1, t0, gp, 0x5\n"), [0x0A32D30B])
        self.assertEqual(xd("MulStep t2, t2, s0\n"), [0x0083A38B])

    def test_campos(self):
        # rd en 11:7, rs1 en 19:15, rs2 en 24:20, k en 29:25, opcode 0x0B.
        for mnem, f3, k in (("emad", 4, 5), ("devk", 5, 5), ("mulstep", 2, 0)):
            sufijo = ", 5" if k else ""
            w = xd(f"{mnem} x1, x2, x4{sufijo}\n")[0]
            with self.subTest(mnem=mnem):
                self.assertEqual(w & 0x7F, 0x0B)
                self.assertEqual((w >> 7) & 0x1F, 1)
                self.assertEqual((w >> 12) & 0x7, f3)
                self.assertEqual((w >> 15) & 0x1F, 2)
                self.assertEqual((w >> 20) & 0x1F, 4)
                self.assertEqual(w >> 25, k)


class RegistrosTests(unittest.TestCase):
    """Las 16 x 16 x 16 combinaciones de registros de cada instrucción."""

    def _todas(self, mnem, f3, f7, sufijo):
        lines, esperado = [], []
        for rd in range(16):
            for rs1 in range(16):
                for rs2 in range(16):
                    lines.append(f"{mnem} x{rd}, x{rs1}, x{rs2}{sufijo}")
                    esperado.append((f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x0B)
        total = 0
        for i, bloque in enumerate(chunks(lines)):
            words = xd("\n".join(bloque) + "\n")
            self.assertEqual(words, esperado[512 * i:512 * i + len(bloque)])
            # ida y vuelta: el texto desensamblado es el mismo que se escribió
            dis = disassemble(words)
            self.assertEqual([d.split(": ", 1)[1] for d in dis], bloque)
            self.assertEqual(xd("\n".join(dis) + "\n"), words)
            total += len(words)
        self.assertEqual(total, 4096)

    def test_emad_todos_los_registros(self):
        self._todas("emad", 0b100, 5, ", 5")

    def test_devk_todos_los_registros(self):
        self._todas("devk", 0b101, 5, ", 5")

    def test_mulstep_todos_los_registros(self):
        self._todas("mulstep", 0b010, 0, "")

    def test_x16_es_error(self):
        casos = [
            "emad x16, x1, x2, 5", "emad x1, x16, x2, 5", "emad x1, x2, x16, 5",
            "devk x16, x1, x2, 5", "devk x1, x31, x2, 5", "devk x1, x2, x16, 5",
            "mulstep x16, x1, x2", "mulstep x1, x16, x2", "mulstep x1, x2, x17",
        ]
        for text in casos:
            with self.subTest(text=text):
                with self.assertRaises(AssemblerError) as ctx:
                    xd("nop\n" + text + "\n")
                self.assertEqual(ctx.exception.line, 2)
                self.assertIn("RV32E solo tiene x0-x15", str(ctx.exception))

    def test_registro_desconocido(self):
        with self.assertRaises(AssemblerError) as ctx:
            xd("mulstep x1, q7, x2\n")
        self.assertIn("registro desconocido", str(ctx.exception))


class KTests(unittest.TestCase):
    def test_k_distinto_de_5_es_error(self):
        for mnem in ("emad", "devk"):
            for k in (0, 4, 6, 31, 32, -1, 37, 0x25):
                with self.subTest(mnem=mnem, k=k):
                    with self.assertRaises(AssemblerError) as ctx:
                        xd(f"nop\nnop\n{mnem} x3, x6, x3, {k}\n")
                    self.assertEqual(ctx.exception.line, 3)
                    msg = str(ctx.exception)
                    self.assertIn("line 3:", msg)
                    self.assertIn(f"k = {k} ", msg)
                    self.assertIn("k cableado en 5", msg)

    def test_k_por_equ(self):
        self.assertEqual(xd(".equ K, 5\nemad x3, x6, x3, K\n"), [0x0A33418B])
        self.assertEqual(xd(".equ K, 0b101\ndevk x6, x5, x3, K\n"), [0x0A32D30B])

    def test_k_por_equ_invalido(self):
        with self.assertRaises(AssemblerError) as ctx:
            xd(".equ K, 4\nemad x3, x6, x3, K\n")
        self.assertEqual(ctx.exception.line, 2)
        self.assertIn("k cableado en 5", str(ctx.exception))

    def test_k_por_define(self):
        self.assertEqual(xd("emad x3, x6, x3, K\n", defines={"K": 5}), [0x0A33418B])
        # -D pisa el .equ del archivo, para bien y para mal
        self.assertEqual(xd(".equ K, 4\ndevk x6, x5, x3, K\n", defines={"K": 5}), [0x0A32D30B])
        with self.assertRaises(AssemblerError):
            xd(".equ K, 5\ndevk x6, x5, x3, K\n", defines={"K": 6})

    def test_k_no_definida(self):
        with self.assertRaises(AssemblerError) as ctx:
            xd("emad x3, x6, x3, K\n")
        self.assertIn("no definida", str(ctx.exception))

    def test_k_no_puede_ser_registro(self):
        with self.assertRaises(AssemblerError):
            xd("emad x3, x6, x3, x5\n")


class HabilitacionTests(unittest.TestCase):
    def test_sin_habilitar_es_error(self):
        for text, _ in GOLDEN:
            mnem = text.split()[0]
            with self.subTest(mnem=mnem):
                with self.assertRaises(AssemblerError) as ctx:
                    assemble_text("nop\n" + text + "\n")
                self.assertEqual(ctx.exception.line, 2)
                msg = str(ctx.exception)
                self.assertIn(f"'{mnem}'", msg)
                self.assertIn(".extension xd", msg)
                self.assertIn("--xd", msg)
                self.assertIn("barrel", msg)

    def test_directiva_habilita(self):
        for text, word in GOLDEN:
            with self.subTest(text=text):
                self.assertEqual(assemble_text(".extension xd\n" + text + "\n"), [word])

    def test_directiva_no_ocupa_espacio(self):
        words = assemble_text("nop\n.extension xd\nfin: j fin\n")
        self.assertEqual(words, assemble_text("nop\nfin: j fin\n"))
        self.assertEqual(len(words), 2)

    def test_directiva_repetida_y_con_opcion(self):
        text = ".extension xd\n.EXTENSION XD\nmulstep x7, x7, x8\n"
        self.assertEqual(assemble_text(text), [0x0083A38B])
        self.assertEqual(assemble_text(text, xd=True), [0x0083A38B])

    def test_directiva_despues_del_uso_es_error(self):
        with self.assertRaises(AssemblerError) as ctx:
            assemble_text("nop\nmulstep x7, x7, x8\n.extension xd\n")
        self.assertEqual(ctx.exception.line, 2)
        self.assertIn("antes del primer uso", str(ctx.exception))

    def test_otra_extension_es_error(self):
        for nombre in ("otra", "m", "xdd", "zba"):
            with self.subTest(nombre=nombre):
                with self.assertRaises(AssemblerError) as ctx:
                    assemble_text(f"nop\n.extension {nombre}\n")
                self.assertEqual(ctx.exception.line, 2)
                self.assertIn("extensión desconocida", str(ctx.exception))
                # tampoco con la extensión ya habilitada por la opción
                with self.assertRaises(AssemblerError):
                    assemble_text(f".extension {nombre}\n", xd=True)

    def test_directiva_sin_nombre_o_con_dos(self):
        for text in (".extension\n", ".extension xd, xd\n"):
            with self.subTest(text=text):
                with self.assertRaises(AssemblerError):
                    assemble_text(text)

    def test_la_directiva_no_queda_pegada_entre_llamadas(self):
        assemble_text(".extension xd\nmulstep x7, x7, x8\n")
        with self.assertRaises(AssemblerError):
            assemble_text("mulstep x7, x7, x8\n")

    def test_habilitar_no_habilita_shifts(self):
        with self.assertRaises(AssemblerError):
            xd("slli x1, x2, 5\n")


class AridadTests(unittest.TestCase):
    def test_aridad_incorrecta(self):
        casos = [
            ("emad x3, x6, x3", 4, 3),
            ("emad x3, x6, x3, 5, 5", 4, 5),
            ("emad", 4, 0),
            ("devk x6, x5, x3", 4, 3),
            ("devk x6, x5", 4, 2),
            ("mulstep x7, x7", 3, 2),
            ("mulstep x7, x7, x8, 5", 3, 4),
        ]
        for text, espera, recibe in casos:
            with self.subTest(text=text):
                with self.assertRaises(AssemblerError) as ctx:
                    xd(text + "\n")
                self.assertIn(f"espera {espera} operando(s), recibió {recibe}", str(ctx.exception))


class DesensambladorTests(unittest.TestCase):
    def test_custom0_invalido_es_desconocido(self):
        def palabra(f7, f3, rs2=3, rs1=6, rd=3):
            return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x0B

        invalidas = []
        for f3 in range(8):
            for f7 in range(128):
                valida = (f3 in (4, 5) and f7 == 5) or (f3 == 2 and f7 == 0)
                if not valida:
                    invalidas.append(palabra(f7, f3))
        self.assertEqual(len(invalidas), 8 * 128 - 3)
        for w in invalidas:
            with self.subTest(word=f"{w:08x}"):
                with self.assertRaises(ValueError):
                    decode_one(w, 0)

    def test_programa_ida_y_vuelta(self):
        words = assemble_text(PROGRAMA)
        dis = "\n".join(disassemble(words)) + "\n"
        self.assertEqual(assemble_text(dis, xd=True), words)
        # el texto desensamblado no trae la directiva: sin --xd no ensambla
        with self.assertRaises(AssemblerError):
            assemble_text(dis)

    def test_vh_y_rom_con_la_extension(self):
        words = assemble_text(PROGRAMA)
        vh = format_verilog_image(words, "t.s")
        rom = format_verilog_rom(words, "t.s")
        for salida in (vh, rom):
            self.assertIn("32'h0a33418b;  // 0x0004: emad x3, x6, x3, 5", salida)
            self.assertIn("32'h0a32d30b;  // 0x0008: devk x6, x5, x3, 5", salida)
            self.assertIn("32'h0083a38b;  // 0x000c: mulstep x7, x7, x8", salida)
        self.assertIn("localparam integer PROG_WORDS = 5;", vh)

    def test_vh_y_rom_con_custom0_invalido(self):
        # emad con k = 4: ilegal para el core, queda como .word en el comentario
        words = assemble_text(".word 0x0833418b\n")
        for salida in (format_verilog_image(words, "t.s"), format_verilog_rom(words, "t.s")):
            self.assertIn("32'h0833418b;  // 0x0000: .word 0x0833418b", salida)


class CliTests(unittest.TestCase):
    def _run(self, text, *extra):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "a.s"
            src.write_text(text, encoding="utf-8")
            out, err = StringIO(), StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = main([str(src), "-o", str(Path(d) / "a.hex"), *extra])
            hexa = (Path(d) / "a.hex").read_text() if rc == 0 else None
            otros = {p.name: p.read_text(encoding="utf-8") for p in Path(d).iterdir()
                     if p.suffix in (".vh", ".v")}
            return rc, err.getvalue(), hexa, otros

    def test_sin_opcion_es_error(self):
        rc, err, _, _ = self._run("emad x3, x6, x3, 5\n")
        self.assertEqual(rc, 1)
        self.assertIn("error: line 1:", err)
        self.assertIn("--xd", err)

    def test_con_opcion(self):
        rc, _, hexa, _ = self._run("emad x3, x6, x3, 5\ndevk x6, x5, x3, 5\nmulstep x7, x7, x8\n", "--xd")
        self.assertEqual(rc, 0)
        self.assertEqual(hexa, "0a33418b\n0a32d30b\n0083a38b\n")

    def test_con_directiva(self):
        rc, _, hexa, _ = self._run(".extension xd\nmulstep x7, x7, x8\n")
        self.assertEqual(rc, 0)
        self.assertEqual(hexa, "0083a38b\n")

    def test_k_por_linea_de_comandos(self):
        rc, _, hexa, _ = self._run("emad x3, x6, x3, K\n", "--xd", "-D", "K=5")
        self.assertEqual((rc, hexa), (0, "0a33418b\n"))
        rc, err, _, _ = self._run("emad x3, x6, x3, K\n", "--xd", "-D", "K=7")
        self.assertEqual(rc, 1)
        self.assertIn("k cableado en 5", err)

    def test_vh_y_rom_por_linea_de_comandos(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "a.s"
            src.write_text(PROGRAMA, encoding="utf-8")
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                rc = main([str(src), "-o", str(Path(d) / "a.hex"),
                           "--vh", str(Path(d) / "a.vh"), "--rom", str(Path(d) / "a.v")])
            self.assertEqual(rc, 0)
            self.assertIn("emad x3, x6, x3, 5", (Path(d) / "a.vh").read_text(encoding="utf-8"))
            self.assertIn("mulstep x7, x7, x8", (Path(d) / "a.v").read_text(encoding="utf-8"))


class NoRegresionTests(unittest.TestCase):
    """Un programa que no usa la extensión ensambla byte a byte igual."""

    def setUp(self):
        self.fuente = (ROOT / "sw" / "trade.s").read_text(encoding="utf-8")
        self.hexa = (ROOT / "sw" / "trade.hex").read_bytes()

    def test_trade_igual_que_antes(self):
        self.assertEqual(format_hex(assemble_text(self.fuente)).encode(), self.hexa)

    def test_trade_igual_con_la_extension_habilitada(self):
        self.assertEqual(format_hex(assemble_text(self.fuente, xd=True)).encode(), self.hexa)
        self.assertEqual(format_hex(assemble_text(".extension xd\n" + self.fuente)).encode(), self.hexa)

    def test_trade_por_archivo(self):
        with tempfile.TemporaryDirectory() as d:
            salida = Path(d) / "trade.hex"
            # firma anterior, sin el parámetro nuevo
            assemble_file(ROOT / "sw" / "trade.s", salida)
            self.assertEqual(salida.read_bytes(), self.hexa)
            assemble_file(ROOT / "sw" / "trade.s", salida, allow_shifts=False, defines=None, xd=True)
            self.assertEqual(salida.read_bytes(), self.hexa)


if __name__ == "__main__":
    unittest.main()
