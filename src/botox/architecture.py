import struct
from elf import ELF

class Architecture(object):
    CODE = []
    BIG = ELF.ELFDATA2MSB
    LITTLE = ELF.ELFDATA2LSB

    def __init__(self, endianess):
        self.endianess = endianess

    def _flip(self, dl):
        fdl = []
        for d in dl:
            fdl.append(d[::-1])
        return fdl

    def payload(self, jump_address):
        code = []

        jump_address_lsb = struct.pack(">H", jump_address & 0xFFFF)
        jump_address_msb = struct.pack(">H", (jump_address >> 16) & 0xFFFF)

        for line in self.CODE:
            code.append(line.replace("MSB", jump_address_msb).replace("LSB", jump_address_lsb))

        if self.endianess == self.BIG:
            return ''.join(code)
        else:
            return ''.join(self._flip(code))


class MIPS(Architecture):
    CODE = [
                    "\x24\x02\x0F\xBD",     # li v0, 0xFBD
                    "\x00\x00\x00\x0C",     # syscall 0
                    "\x3c\x08MSB",          # lui t0, <MSB>
                    "\x25\x08LSB",          # addiu t0, t0, <LSB>
                    "\x01\x00\x00\x08",     # jr t0
                    "\x00\x00\x00\x00",     # nop
           ]

class ARM(Architecture):
    CODE = [
                "\xe3\xa0\x70\x1d",     # mov R7, #29
                "\xe3\xa0\x00\x01",     # mov R1, #1
                "\xef\x00\x00\x00",     # svc #0
                "\xe5\x1f\xf0\x04",     # LDR PC=<value>
                "MSBLSB",               # <value>
           ]
