"""Tests de la directiva .org (relleno con ceros hasta una dirección).

Se usa al final de sw/trade.s para que trade.hex tenga las 512 palabras de la
RAM: así la simulación y la placa parten con la misma memoria (en simulación
una palabra que no está en el .hex queda indefinida; en la placa queda en 0),
y el .hex tiene el tamaño que necesita icebram.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import assemble_text  # noqa: E402
from errors import AssemblerError  # noqa: E402


class OrgTests(unittest.TestCase):
    def test_pads_with_zero_words(self):
        words = assemble_text("nop\n.org 16\n")
        self.assertEqual(words, [0x00000013, 0, 0, 0])

    def test_pads_to_full_ram(self):
        words = assemble_text("nop\n.org 0x800\n")
        self.assertEqual(len(words), 512)
        self.assertEqual(set(words[1:]), {0})

    def test_org_at_current_address_emits_nothing(self):
        self.assertEqual(assemble_text("nop\n.org 4\n"), [0x00000013])

    def test_label_after_org_gets_new_address(self):
        # la etiqueta queda en 0x10, y el .word la referencia
        words = assemble_text(".word dato\n.org 0x10\ndato: .word 7\n")
        self.assertEqual(words, [0x10, 0, 0, 0, 7])

    def test_org_accepts_equ(self):
        words = assemble_text(".equ FIN, 8\nnop\n.org FIN\n")
        self.assertEqual(len(words), 2)

    def test_org_backwards_is_error(self):
        with self.assertRaises(AssemblerError):
            assemble_text("nop\nnop\n.org 4\n")

    def test_org_unaligned_is_error(self):
        with self.assertRaises(AssemblerError):
            assemble_text("nop\n.org 6\n")

    def test_org_beyond_ram_is_error(self):
        with self.assertRaises(AssemblerError):
            assemble_text("nop\n.org 0x804\n")

    def test_code_after_full_ram_is_error(self):
        with self.assertRaises(AssemblerError):
            assemble_text("nop\n.org 0x800\nnop\n")


if __name__ == "__main__":
    unittest.main()
