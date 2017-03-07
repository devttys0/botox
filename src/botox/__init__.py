import struct
from elf import ELF
from architecture import *

class BotoxException(Exception):
    pass

class Botox(object):

    def __init__(self, elfile):
        self.elfile = elfile

    def _resolve_architecture(self, machine_type):
        '''
        Returns a subclass of architecture.Architecture that corresponds
        to the target ELF's architecture.

        @machine_type - The e_ident.ei_machine value from the ELF header.

        Returns a subclass of architecture.Architecture on success.
        Returns None on failure.
        '''
        if machine_type == ELF.EM_MIPS:
            return MIPS
        elif machine_type == ELF.EM_ARM:
            return ARM
        else:
            return None

    def patch(self, payload=None):
        '''
        Injects the supplied payload into the target ELF file.
        The entry point will be modified to point to the injected code.

        @payload - The payload to inject into the ELF file.
                   If no payload is provided, the default pause payload will be used.

        Returns the new entry point address on success.
        Returns None on failure, or (more likely) raises an exception.
        '''
        alignment_size = None
        load_segment_size = None
        load_segment_offset = None
        load_segment_virtual_base_address = None

        # Open the target ELF file for writing
        with ELF(self.elfile, read_only=False) as elf:
            # If no payload was specified, use the built-in pause payload
            if payload is None:
                arch = self._resolve_architecture(elf.header.e_machine)
                if arch is None:
                    raise BotoxException("No default payload for this architecture!")
                payload = arch(elf.header.e_ident.ei_encoding).payload(elf.header.e_entry)

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

        return None
