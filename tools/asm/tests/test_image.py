"""Tests de las salidas Verilog del ensamblador (vienen del Proyecto 3).

--vh escribe la imagen del programa como una función de Verilog y --rom
escribe el módulo pochoco_rom, una ROM combinacional. Las dos tienen que
contener exactamente las mismas palabras que el .hex, en el mismo orden.
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import assemble_text, format_hex, format_verilog_image, format_verilog_rom  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CASE_RE = re.compile(r"^\s*(\d+): prog_word = 32'h([0-9a-f]{8});")
ROM_RE = re.compile(r"^\s*\d+'d(\d+)\s*: data_o = 32'h([0-9a-f]{8});")


def image_words(text):
    return {int(m.group(1)): int(m.group(2), 16)
            for m in map(CASE_RE.match, text.splitlines()) if m}


def rom_words(text):
    return {int(m.group(1)): int(m.group(2), 16)
            for m in map(ROM_RE.match, text.splitlines()) if m}


class ImageTests(unittest.TestCase):
    def test_small_program(self):
        words = assemble_text("addi x1, x0, 5\nadd x2, x1, x1\n")
        vh = format_verilog_image(words, "t.s")
        self.assertIn("localparam integer PROG_WORDS = 2;", vh)
        self.assertEqual(image_words(vh), {0: words[0], 1: words[1]})
        self.assertIn("default: prog_word = 32'h00000000;", vh)

    def test_comment_is_disassembly(self):
        vh = format_verilog_image(assemble_text("addi x1, x0, 5\n"), "t.s")
        self.assertRegex(vh, r"// 0x0000: addi x1, x0, 5")

    def test_blink_image_matches_hex(self):
        text = (ROOT / "sw" / "blink.s").read_text(encoding="utf-8")
        words = assemble_text(text)
        vh = format_verilog_image(words, "sw/blink.s")
        self.assertIn(f"localparam integer PROG_WORDS = {len(words)};", vh)
        self.assertEqual(image_words(vh), dict(enumerate(words)))
        hex_words = [int(l, 16) for l in format_hex(words).split()]
        self.assertEqual(hex_words, words)


class RomTests(unittest.TestCase):
    def test_small_program(self):
        words = assemble_text("addi x1, x0, 5\nadd x2, x1, x1\nnop\n")
        rom = format_verilog_rom(words, "t.s")
        self.assertIn("module pochoco_rom (", rom)
        self.assertIn("wire [1:0] word = addr_i[3:2];", rom)  # 3 palabras: 2 bits
        self.assertEqual(rom_words(rom), dict(enumerate(words)))
        self.assertIn("default: data_o = 32'h00000000;", rom)

    def test_blink_rom_matches_hex(self):
        text = (ROOT / "sw" / "blink.s").read_text(encoding="utf-8")
        words = assemble_text(text)
        rom = format_verilog_rom(words, "sw/blink.s")
        self.assertEqual(rom_words(rom), dict(enumerate(words)))


if __name__ == "__main__":
    unittest.main()
