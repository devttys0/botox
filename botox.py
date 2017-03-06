#!/usr/bin/env python
import os
import sys

try:
    from elftools.elf.elffile import ELFFile
    from elftools.elf.sections import SymbolTableSection
    from elftools.common.exceptions import ELFError
except ImportError as e:
    if "__main__" == __name__:
        sys.stderr.write("This tool requires the pyelftools Python module. Please install it from https://github.com/eliben/pyelftools.\n")
        sys.exit(1)
    else:
        raise e

class BotoxException(Exception):
    pass

class Architecture(object):
    CODE = []
    BIG = "big"
    LITTLE = "little"

    def __init__(self, endianess):
        self.endianess = endianess

    def _flip(self, dl):
        fdl = []
        for d in dl:
            fdl.append(d[::-1])
        return fdl

    def payload(self):
        if self.endianess == self.BIG:
            return ''.join(self.CODE)
        else:
            return ''.join(self._flip(self.CODE))

class MIPS(Architecture):
    CODE = [
                "\x24\x02\x0F\xB4",     # li v0, 0xFB4
                "\x00\x00\x00\x0C",     # syscall 0     ; getpid()
                "\x00\x40\x20\x21",     # move a0, v0
                "\x24\x04\x00\x17",     # li a1, 23
                "\x24\x02\x0F\xC5",     # li v0, 0xFC5
                "\x00\x00\x00\x0C",     # syscall 0     ; kill(getpid(), SIGSTOP)
           ]

class Botox(object):

    def __init__(self, elf_file):
        self.symbols = {}
        self.segments = []
        self.abspath = os.path.abspath(elf_file)

        with open(self.abspath) as fp:
            try:
                elf_header = ELFFile(fp)
            except ELFError as e:
                raise BotoxException("Failed to load %s as an ELF file: %s" % (self.abspath, str(e)))

            self._load_symbols(elf_header)
            self._load_segments(elf_header)
            self._detect_architecture(elf_header)

    def _detect_architecture(self, elf_header):
        if elf_header['e_machine'] == "EM_386":
            self.arch = "X86"
        else:
            self.arch = elf_header['e_machine'].replace("EM_", "")

        if elf_header['e_ident']["EI_DATA"].endswith("LSB"):
            self.endianess = Architecture.LITTLE
        else:
            self.endianess = Architecture.BIG

    def _load_symbols(self, elf_header):
        for section in elf_header.iter_sections():
            if isinstance(section, SymbolTableSection) and section['sh_entsize'] != 0:
                for nsym, symbol in enumerate(section.iter_symbols()):
                    address = symbol['st_value']
                    self.symbols[symbol.name] = address

    def symbol_name_to_virtual_address(self, symbol_name):
        for (name, address) in self.symbols.iteritems():
            if name == symbol_name:
                return address
        return None

    def _load_segments(self, elf_header):
        for segment in elf_header.iter_segments():
            self.segments.append(segment)

    def virtual_address_to_physical_offset(self, vaddr):
        for segment in self.segments:
            file_start = segment['p_offset']
            file_size = segment['p_filesz']
            mem_start = segment['p_vaddr']
            mem_size = segment['p_memsz']

            if (vaddr >= mem_start) and (vaddr < (mem_start + mem_size)):
                offset = vaddr - mem_start
                return (file_start + offset)

        return None

    def patch(self, out_file=None, address=None, symbol=None, payload=None):
        if out_file is None:
            out_file = self.abspath

        if payload is None:
            try:
                arch_obj = getattr(sys.modules[__name__], self.arch)
                payload = arch_obj(self.endianess).payload()
            except AttributeError as e:
                raise BotoxException("Sorry, the %s architecture is not supported at this time!" % self.arch)

        if address is None:
            if symbol is None:
                symbol = "main"

            address = self.symbol_name_to_virtual_address(symbol)
            if address is None:
                raise BotoxException("Failed to locate the %s function in the ELF header symbol table! Please specify the virtual address of the main function manually." % symbol)

        file_offset = self.virtual_address_to_physical_offset(address)
        if file_offset is None:
            raise BotoxException("The virtual address 0x%X does not exist in this ELF file!" % address)

        with open(self.abspath, 'rb') as fp:
            data = fp.read(file_offset)
            data += payload
            fp.seek(len(data))
            data += fp.read()

        with open(out_file, 'wb') as fp:
            fp.write(data)

if "__main__" == __name__:
    import getopt

    yes = False
    symbol = None
    address = None
    payload = None
    input_file = None
    output_file = None

    (options, rem) = getopt.getopt(sys.argv[1:], "f:a:s:o:p:y", ["file=", "address=", "symbol=", "output=", "payload=", "yes"])

    for (opt, arg) in options:
        if opt in ("-f", "--file"):
            input_file = arg
        elif opt in ("-o", "--output"):
            output_file = arg
        elif opt in ("-a", "--address"):
            address = int(arg, 0)
        elif opt in ("-p", "--payload"):
            with open(arg) as fp:
                payload = fp.read()
        elif opt in ("-s", "--symbol"):
            symbol = arg
        elif opt in ("-y", "--yes"):
            yes = True

    if input_file is None:
        sys.stderr.write("Usage: %s [OPTIONS]\n\n" % sys.argv[0])
        sys.stderr.write("    -f, --file=<input file>\n")
        sys.stderr.write("    -o, --output=<output file>\n")
        sys.stderr.write("    -p, --payload=<payload input file>\n")
        sys.stderr.write("    -a, --address=<virtual address to patch>\n")
        sys.stderr.write("    -s, --symbol=<name of function to patch>\n")
        sys.stderr.write("    -y, --yes\n")
        sys.stderr.write("\n")
        sys.exit(1)

    if output_file is None and not yes:
        yn = raw_input("WARNING: You have not specified an output file.\n         This means that the input file (%s) will be modified in place, with no backup.\n         Are you sure you want to do this? [y/N] " % os.path.basename(input_file))
        if not yn.lower().startswith('y'):
            sys.stdout.write("Quitting...\n")
            sys.exit(1)

    try:
        elf = Botox(input_file)
        elf.patch(out_file=output_file, address=address, payload=payload, symbol=symbol)
    except BotoxException as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)

