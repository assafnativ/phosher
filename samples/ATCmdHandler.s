
@ Compile:
@  arm-none-eabi-as -mthumb -EB -o ATCmdHandler.o ATCmdHandler.s
@  arm-none-eabi-objcopy -O binary ATCmdHandler.o ATCmdHandler.bin

.FILE "ATCMD_Handler_s"
.CODE 16
.thumb_func
.global readMemory
.func readMemory

readMemory:
push {R3-R6, LR}

@ -- Address from str to int
@ R2 -> Command context
@ At offset 0xb8 the Command starts
@ 0xb8 + len("AT+WS46=") == 0xc0
ldr R0, .addrStrOffset
add R0, R0, R2
mov R6, R0
@ R1 == End of the command
mov R1, #0
@ Use base 10
mov R2, #10
ldr R4, .strtoul
bl .jumpToR4
mov R5, R0

@ -- Is zero
ldr R4, .printf
cmp R0, #0
bne .notZero
adr R0, .invalidAddress
mov R1, R6
bl .jumpToR4
pop {R3-R6, PC}

.notZero:
@ -- Print header
mov R1, R0
adr R0, .dumpMemString
bl .jumpToR4

@ -- Dump memory
mov R0, R5
ldr R1, .dumpLength
ldr R4, .memDump
bl .jumpToR4

@---
pop {R3-R6, PC}

.jumpToR4:
bx R4

.balign 8
.printf:
.word 0x013F98F8+1
.strtoul:
.word 0x01928368+1
.memDump:
.word 0x01bfbb00+1
.addrStrOffset:
.word 0xc0
.dumpLength:
.word 0x80
.invalidAddress:
.asciz "\r\nInvalid address: %s\r\n"
.balign 8
.dumpMemString:
.asciz "\r\nMem (%08lx):\r\n"
.balign 8

.hextoul:
push {r1-r7,lr}
@ Current char
movs    r2, r0
@ result = 0
movs    r0, #0

b       .nextChar

.above0x40:
@ currentChar - 'A' + 10
sub     r3, #0x37
@ result *= 0x10
lsl     r0, r0, #4
@ result += currentChar -'A' + 10
add     r0, r3, r0

.nextChar:
@ currentChar = *r2
ldrb    r3, [r2, #0]
movs    r1, r3
sub     r1, #0x30
@ pos += 1
add     r2, #1
cmp     r1, #22
bhi     .returnX
.loopstart:
    cmp     r3, #0x40
    bhi     .above0x40
    cmp     r3, #0x39
    bhi     .returnX
    ldrb    r3, [r2, #0]
    lsl     r0, r0, #4
    add     r0, r1, r0
    movs    r1, r3
    sub     r1, #0x30
    add     r2, #1
    cmp     r1, #22
bls     .loopstart
.returnX:
pop {r1-r7,pc}
