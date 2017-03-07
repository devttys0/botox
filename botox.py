#!/usr/bin/env python
import struct
from elf import ELF

class BotoxException(Exception):
    pass

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
                "MSBLSB",     # <value>
           ]

class Botox(object):

    def __init__(self, elfile):
        self.elfile = elfile

    def patch(self, payload=None):
        alignment_size = None
        load_segment_size = None
        load_segment_offset = None
        load_segment_virtual_base_address = None

        # Open the target ELF file for writing
        with ELF(self.elfile, read_only=False) as elf:
            # If no payload was specified, use the built-in pause payload
            if payload is None:
                payload = MIPS(elf.header.e_ident.ei_encoding).payload(elf.header.e_entry)

            # Loop through all the program headers looking for the first executable load segment
            for phdr in elf.program_headers:
                if ELF.PT_LOAD == phdr.p_type and True == phdr.flags.execute:
                    alignment_size = phdr.p_align

                    load_segment_size = phdr.p_filesz
                    load_segment_offset = phdr.p_offset
                    load_segment_virtual_base_address = phdr.p_vaddr - phdr.p_offset

                    phdr.p_memsz += alignment_size
                    phdr.p_filesz += alignment_size

                    break

            # Sanity checks
            if None in [alignment_size, load_segment_size, load_segment_offset, load_segment_virtual_base_address]:
                raise BotoxException("Failed to locate a loadable, executable segment! What is this, an ELF file for ants?!")
            if len(payload) > alignment_size:
                raise BotoxException("I'm too lazy to handle payloads larger than the segment alignment size (%d)!" % alignment_size)

            # Pad our payload out to the alignment size of the load segment
            payload += "\x00" * (alignment_size - len(payload))
            payload_size = len(payload)

            # By default, the payload is just slapped on the end of the executable
            # load segment as defined in the program headers.
            payload_offset = load_segment_offset + load_segment_size

            # Each segment defined in the program headers that starts *after*
            # the offset where our payload will be inserted must have its
            # starting offset increased by the size of out payload.
            for phdr in elf.program_headers:
                if payload_offset <= phdr.p_offset:
                    phdr.p_offset += payload_size

            # Each section defined in the section headers that starts *after*
            # the offset where our payload will be inserted must have its
            # starting offset increased by the size of out payload.
            for shdr in elf.section_headers:
                if payload_offset <= shdr.sh_offset:
                    shdr.sh_offset += payload_size

                # The section in which the actual payload should reside must have its size increased
                # to acommodate the new payload, and must also be marked as executable.
                if payload_offset > shdr.sh_offset and payload_offset <= (shdr.sh_offset + shdr.sh_size):
                    shdr.flags.alloc = True
                    shdr.flags.execute = True
                    shdr.sh_size += payload_size

            # If the section headers come after the new payload insertion location
            # (which they will), update the offset of the section headers by the
            # size of the payload.
            if payload_offset <= elf.header.e_shoff:
                elf.header.e_shoff += payload_size

            # Update the program entry point to be the location of our payload
            elf.header.e_entry = load_segment_virtual_base_address + payload_offset

            # Now that all header information has been updated to acommodate the
            # payload, insert the payload into the ELF file.
            elf.insert(payload_offset, payload)

            return elf.header.e_entry

if "__main__" == __name__:
    import sys
    new_entry_point = Botox(sys.argv[1]).patch()
    print "New entry point address: 0x%X" % new_entry_point

