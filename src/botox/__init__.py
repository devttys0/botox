import sys
import struct
from elf import ELF
from exceptions import *
from architecture import *

class Botox(object):

    def __init__(self, elfile, verbose=False):
        '''
        Class constructor.

        @elfile  - Path to the target ELF file to patch.
        @verbose - Set to True to enable verbose debug print statements.

        Returns None.
        '''
        self.elfile = elfile
        self.verbose = verbose

    def _resolve_architecture(self, machine_type, ei_class):
        '''
        Returns a subclass of architecture.Architecture that corresponds
        to the target ELF's architecture.

        @machine_type - The e_machine value from the ELF header.
        @ei_class     - The e_ident.ei_class value from the ELF header.

        Returns a subclass of architecture.Architecture on success.
        Returns None on failure.
        '''
        if machine_type == ELF.EM_MIPS:
            return MIPS
        elif machine_type == ELF.EM_ARM:
            return ARM
        elif machine_type == ELF.EM_X86_64:
            return X86_64
        elif machine_type == ELF.EM_386:
            if ELF.ELFCLASS64 == ei_class:
                return X86_64
            else:
                return X86
        else:
            return None

    def _debug_print(self, msg):
        '''
        For internal debug use.

        @msg - Message to print to stderr, if self.verbose is True.

        Returns None.
        '''
        if True == self.verbose:
            sys.stderr.write(msg + "\n")

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
            # Relocatable files, shared objects, etc should be ignored.
            # These can be supported in the future, but relative addressing
            # support needs to be added to the payload code in architectures.py.
            if ELF.ET_EXEC != elf.header.e_type:
                raise BotoxException("Sorry, I only support ELF executable files!")

            # If no payload was specified, use the built-in pause payload
            if payload is None:
                arch = self._resolve_architecture(elf.header.e_machine, elf.header.e_ident.ei_class)
                if arch is None:
                    raise BotoxException("Sorry, this architecture [0x%X 0x%X] is not supported!" % (elf.header.e_machine, elf.header.e_ident.ei_class))
                payload = arch(elf.header.e_ident.ei_encoding).payload(elf.header.e_entry)

            # Loop through all the program headers looking for the first executable load segment
            for phdr in elf.program_headers:
                if ELF.PT_LOAD == phdr.p_type and True == phdr.flags.execute:
                    self._debug_print("Modifying program header #%d" % phdr.index)

                    alignment_size = phdr.p_align

                    load_segment_size = phdr.p_filesz
                    load_segment_offset = phdr.p_offset
                    load_segment_virtual_base_address = phdr.p_vaddr - phdr.p_offset

                    # Don't want to insert multiple SIGSTOPs, do a sanity check before modifying anything.
                    # Check the first few bytes of the current entry point against the first few bytes of the payload.
                    # Can't check against the entire payload, since the end of the payload will be jumping to the
                    # entry point, which will change each time botox modifies an ELF file; 16 bytes should be sufficient.
                    if elf.read((elf.header.e_entry - load_segment_virtual_base_address), 16) == payload[0:16]:
                        raise BotoxException("I've already patched this binary, and I shan't do it again!")

                    # Increase this segment's file and memory size so we can shove our payload in it
                    phdr.p_memsz += alignment_size
                    phdr.p_filesz += alignment_size

                    break

            # Sanity checks
            if None in [alignment_size, load_segment_size, load_segment_offset, load_segment_virtual_base_address]:
                raise BotoxException("Failed to locate a loadable, executable segment! What is this, an ELF file for ants?!")
            if len(payload) > alignment_size:
                raise BotoxException("Sorry, my developer was too lazy to tell me how to handle payloads larger than the segment alignment size (%d)!" % alignment_size)

            # Pad our payload out to the alignment size of the load segment
            payload += "\x00" * (alignment_size - len(payload))
            payload_size = len(payload)

            # By default, the payload is just slapped on the end of the executable
            # load segment as defined in the program headers.
            payload_offset = load_segment_offset + load_segment_size
            self._debug_print("Payload will be placed at file offset 0x%X (virtual address: 0x%X)" % (payload_offset, load_segment_virtual_base_address + payload_offset))

            # Each segment defined in the program headers that starts *after*
            # the offset where our payload will be inserted must have its
            # starting offset increased by the size of our payload.
            for phdr in elf.program_headers:
                if payload_offset <= phdr.p_offset:
                    self._debug_print("Increasing the size of program header #%d by 0x%X" % (phdr.index, payload_size))
                    phdr.p_offset += payload_size

            # Each section defined in the section headers that starts *after*
            # the offset where our payload will be inserted must have its
            # starting offset increased by the size of our payload.
            for shdr in elf.section_headers:
                if payload_offset <= shdr.sh_offset:
                    self._debug_print("Increasing the size of section header %s by 0x%X" % (shdr.name, payload_size))
                    shdr.sh_offset += payload_size

                # The section in which the actual payload should reside must have its size increased
                # to acommodate the new payload, and must also be marked as executable.
                if payload_offset > shdr.sh_offset and payload_offset <= (shdr.sh_offset + shdr.sh_size):
                    self._debug_print("Payload will reside in section %s, increasing its size by 0x%X" % (shdr.name, payload_size))
                    shdr.flags.execute = True
                    shdr.flags.allocate = True
                    shdr.sh_size += payload_size

            # If the section headers come after the new payload insertion location
            # (which they will), update the offset of the section headers by the
            # size of the payload.
            if payload_offset <= elf.header.e_shoff:
                self._debug_print("Increasing section header offset by 0x%X" % payload_size)
                elf.header.e_shoff += payload_size

            # Update the program entry point to be the location of our payload
            self._debug_print("Setting ELF entry point to 0x%X" % (load_segment_virtual_base_address + payload_offset))
            elf.header.e_entry = load_segment_virtual_base_address + payload_offset

            # Now that all header information has been updated to acommodate the
            # payload, insert the payload into the ELF file.
            self._debug_print("Inserting payload of size 0x%X at file offset 0x%X" % (payload_size, payload_offset))
            elf.insert(payload_offset, payload)

            return elf.header.e_entry

        return None

