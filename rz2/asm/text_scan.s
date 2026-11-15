@ RZ2 counts printable characters for dialogue pacing. Preserve native
@ counting for original ROM strings. Expanded strings use EC–EF + payload.
.align 2
count_chars:
    ldr r1, scan_expansion
    cmp r0, r1
    blo count_native
    movs r1, #0
count_loop:
    ldrb r2, [r0]
    cmp r2, #0xFC
    bhi count_done
    adds r0, #1
    cmp r2, #0xEC
    blo count_glyph
    cmp r2, #0xF0
    bhi count_control
    adds r0, #1
count_glyph:
    adds r1, #1
    b count_loop
count_control:
    cmp r2, #0xF3
    blo count_loop
    cmp r2, #0xF8
    bhi count_loop
    adds r0, #1
    b count_loop
count_done:
    adds r0, r1, #0
    bx lr

.align 2
skip_chars:
    ldr r2, scan_expansion
    cmp r0, r2
    blo skip_native
skip_loop:
    ldrb r2, [r0]
    cmp r2, #0xFC
    bhi skip_done
    cmp r1, #0
    beq skip_done
    adds r0, #1
    cmp r2, #0xEC
    blo skip_glyph
    cmp r2, #0xF0
    bhi skip_control
    adds r0, #1
skip_glyph:
    subs r1, #1
    b skip_loop
skip_control:
    cmp r2, #0xF3
    blo skip_loop
    cmp r2, #0xF8
    bhi skip_loop
    adds r0, #1
    b skip_loop
skip_done:
    bx lr

@ Replay the overwritten Thumb instructions before resuming original ROM.
count_native:
    push {r4-r6, lr}
    adds r4, r0, #0
    movs r5, #0
    ldrb r0, [r4]
    ldr r3, count_return
    bx r3
skip_native:
    ldrb r2, [r0]
    cmp r2, #0xFC
    bhi skip_done
    cmp r1, #0
    beq skip_done
    adds r0, #1
    cmp r2, #0xEF
    bls skip_native_glyph
    cmp r2, #0xF0
    beq skip_native_pair
    cmp r2, #0xF8
    bhi skip_native
    adds r0, #1
    b skip_native
skip_native_pair:
    adds r0, #1
skip_native_glyph:
    subs r1, #1
    b skip_native

.align 2
scan_expansion: .word 0x08800000
count_return:   .word 0x080DE71D
