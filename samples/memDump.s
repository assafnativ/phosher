
@ Compile:
@  arm-none-eabi-as -mthumb -EB -o memDump.o memDump.s
@  arm-none-eabi-objcopy -O binary memDump.o memDump.bin

.FILE "memDump_s"
.CODE 16
.thumb_func
.global memDump
.func memDump

memDump:
push {R2-R6, LR}
@ R0 is the address to dump
@ R1 is the how many DWords we want to dump
mov r2, #3
bic r0, r2
lsl r5, r1, #2
mov r4, #0
mov r6, r0
loop:
    ldr r1, [r6, r4]
    adr r0, .hexChar
    ldr r3, .printf
    bl .jumpToR3
    @ Restore target address
add r4, r4, #4
cmp r4, r5
blt loop
pop {R2-R6, PC}

.jumpToR3:
bx r3

.balign 8
.printf:
.word 0x013F98F8+1
.hexChar:
.asciz "%08lx"
.asciz "\r\n"
