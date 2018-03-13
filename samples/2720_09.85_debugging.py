import os

FILE_NAME = 'rm519__09.85'
BASE = 0x01000000

DUMP_MEM_PROC_ADDR      = 0x01BFBB00
DUMP_MEM_PROC = file('..\\..\\pytrix\\Debugging\\memDump.bin', 'rb').read().encode('hex')
HANDLER_DUMP_ADDR = 0x01BFBD00
HANDLER_DUMP = file('..\\..\\pytrix\\Debugging\\ATCmdHandlerDebug.bin', 'rb').read().encode('hex')

SHELLCODE_ADDR          = 0x01BFD000
SHELLCODE               = '4905 4571 D005 4A05 B404 2200 1C01 1C10 BD00 2500 3108 4708 0108 6301 0145 31FB'

PATCHES = [ \
        ('*#0001#',                 0x01A227CA, '00300023', '00310023'),
        ('Patch AT-Cmd (WS46)',     0x0199DB64, '013194F5', '%08x' % (HANDLER_DUMP_ADDR+1)),
        ('Dump mem proc',           DUMP_MEM_PROC_ADDR, None, DUMP_MEM_PROC ),
        ('New AT-Cmd handler dump', HANDLER_DUMP_ADDR, None, HANDLER_DUMP ),
        ('Detour SHA1 check part',  0x01453218, '220000010010e7ec', '4a004710 %08X' % (SHELLCODE_ADDR + 1)),
        ('The shell code!',         SHELLCODE_ADDR, None, SHELLCODE  ) ]
