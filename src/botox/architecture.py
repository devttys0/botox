import struct
from elf import ELF
from exceptions import BotoxException

try:
    from keystone import *
except ImportError as e:
    raise BotoxException("Botox requires the keystone module! Please install it from: https://github.com/keystone-engine/keystone")

class Architecture(object):
    '''
    Architecture class. All other arch-specific classes should be subclassed from this.
    '''
    # Payload code, one assembly instruction per list entry. This code will
    # be assembled at run time by the keystone library. The payload code should
    # send itself a SIGSTOP signal, then jump to the original program's entry
    # point; effectively:
    #
    #       kill(getpid(), SIGSTOP);
    #       goto entry_point;
    #
    # As the actual entry point address will not be known until runtime, the
    # literal string "entry_point" may be used in the assembly code. This will
    # be replaced at runtime byt the hexadecimal entry point address prior to
    # assembly.
    ASM = []
    # The keystone.KS_ARCH_XXX architecture associated with this architecture
    ARCH = None
    # The keystone.KS_MODE_XXX mode to be used with this architecture
    MODE = None

    BIG = ELF.ELFDATA2MSB
    LITTLE = ELF.ELFDATA2LSB

    ENTRY_POINT = "entry_point"

    def __init__(self, endianess):
        '''
        Class constructor.

        @endianess - The endianess of the target architecture, as specified in the ELF
                     header (e_ident.ei_encoding).

        Returns None.
        '''
        self.endianess = endianess

    def payload(self, jump_address):
        '''
        Generates a payload that will pause the process execution
        until a SIGCONT signal is passed to the process, at which
        point the code will jump to a specified address.

        @jump_address - The address to jump to when SIGCONT is encountered.

        Returns a string containing the shellcode.
        '''
        encoding = []

        # Set big/little endian flag for keystone
        if self.endianess == self.BIG:
            endian_mode = KS_MODE_BIG_ENDIAN
        else:
            endian_mode = KS_MODE_LITTLE_ENDIAN

        # Instatiate the keystone.Ks class for assembly
        ks = Ks(self.ARCH, self.MODE | endian_mode)

        # Assemble each line to a list of raw bytes that are appended to the
        # encoding list. Exceptions in assembling any specific line of code
        # will be caught and a BotoxException will be raised.
        for line in self.ASM:
            assembly = line.replace(self.ENTRY_POINT, hex(jump_address))

            try:
                (hexbytes, count) = ks.asm(assembly)
                encoding += hexbytes
            except KeyboardInterrupt as e:
                raise e
            except Exception as e:
                raise BotoxException("Failed to assemble payload line '%s': %s" % (assembly, str(e)))

        # Convert the list of raw bytes into a string and return
        return ''.join([chr(byte) for byte in encoding])

class X86(Architecture):
    ARCH = KS_ARCH_X86
    MODE = KS_MODE_32
    ASM = [
                "mov eax, 20",
                "int 0x80",         # getpid();
                "mov ebx, eax",
                "mov ecx, 19",
                "mov eax, 37",
                "int 0x80",         # kill(pid, SIGSTOP);
                "mov eax, %s" % Architecture.ENTRY_POINT,
                "jmp eax",          # goto entry_point
          ]

class MIPS(Architecture):
    ARCH = KS_ARCH_MIPS
    MODE = KS_MODE_MIPS32
    ASM = [
                "li $v0, 0xFB4",
                "syscall 0",        # getpid();
                "move $a0, $v0",
                "li $a1, 23",
                "li $v0, 0xFC5",
                "syscall 0",        # kill(pid, SIGSTOP);
                "li $t0, %s" % Architecture.ENTRY_POINT,
                "jr $t0",           # goto entry_point;
           ]

class ARM(Architecture):
    ARCH = KS_ARCH_ARM
    ARCH = KS_MODE_ARM
    ASM = [
                "mov R7, #29",
                "mov R1, #1",
                "svc #0",
                "LDR PC=%s" % Architecture.ENTRY_POINT
           ]

