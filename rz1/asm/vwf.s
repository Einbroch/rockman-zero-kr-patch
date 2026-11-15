@ 록맨 제로 1 — 12px 한글 가변폭(VWF) 출력기
@ 원래 출력기 0x080bc3e8(글자 코드 단위 캐시)를 대체한다. 캐시 노드 80개는 그대로 쓴다.
@  노드 = [0]next [4]A [6]B   A = 왼쪽 4px 조각 번호(bit15 = 강조색), B = 오른쪽 조각 번호(bit15 = 업로드 필요)
@  노드 주소 -> 타일 번호: T = 0x37E - (0x02023620 - node)/4  (위 T, 아래 T+1)
@ 리스트: 활성 [0x02023628], 지난 프레임 [0x0202362c], 빈 칸 [0x02023630]
@ 글자 인코딩: <0x80 1바이트 글리프, 0x80~0xEF 리드 + 트레일(0x00~0xEF): g = 0x80 + (lead-0x80)*0xF0 + trail
@ 글리프표 GTAB[g] = u32 (첫 조각 번호 | 조각 수<<16), 조각 데이터 QDAT + q*32 (16행 x 2바이트)
@ 카운트(글자 수 r2)는 바이트 단위로 줄인다 — 원래 0x080bc270(글자 건너뛰기)와 같은 셈법.

@ ---- 출력기 진입: r0 = 타일맵 쓰기 위치, r1 = 문자열, r2 = 카운트 -> r0 = 남은 카운트
render:
    push {r4-r7, lr}
    mov r3, r8
    push {r3}
    mov r3, r9
    push {r3}
    mov r3, r10
    push {r3}
    mov r3, r11
    push {r3}
    sub sp, #8               @ [sp+0] 줄 시작 [sp+4] 이름 복귀 포인터 / r11 = 대기 조각(-1 없음)
    str r0, [sp, #0]
    adds r4, r0, #0    @ r4 = 현재 칸 위치
    adds r7, r1, #0    @ r7 = 문자열
    lsls r6, r2, #16
    lsrs r6, r6, #16    @ r6 = 카운트
    movs r0, #0
    str r0, [sp, #4]
    mvns r0, r0
    mov r11, r0
    movs r0, #0
    mov r10, r0              @ r10 = 색 비트(0 또는 0x8000)

r_loop:
    cmp r6, #0
    beq r_done
r_fetch:
    ldrb r0, [r7]
    cmp r0, #0xFC
    bls r_notend
    @ 끝 바이트: 이름 삽입 중이면 복귀
    ldr r1, [sp, #4]
    cmp r1, #0
    beq r_done
    adds r7, r1, #1
    movs r1, #0
    str r1, [sp, #4]
    b r_fetch
r_notend:
    cmp r0, #0xF0
    bhs r_ctrl
    cmp r0, #0x80
    bhs r_two
    adds r7, #1
    subs r6, #1
    b r_glyph
r_two:
    subs r0, #0x80
    movs r1, #0xF0
    muls r0, r1, r0
    ldrb r1, [r7, #1]
    adds r0, r0, r1
    adds r0, #0x80
    adds r7, #2
    subs r6, #2
    bpl r_glyph
    movs r6, #0
r_glyph:
    @ r0 = 글리프 번호
    ldr r1, L_GTAB
    lsls r0, r0, #2
    ldr r0, [r1, r0]
    lsrs r5, r0, #31
    mov r9, r5               @ r9 = 1 이면 같은 조각 반복
    lsls r5, r0, #1
    lsrs r5, r5, #17    @ 조각 수 (bit16~30)
    lsls r0, r0, #16
    lsrs r0, r0, #16    @ 첫 조각
    mov r8, r0
r_q:
    cmp r5, #0
    beq r_loop
    mov r0, r8
    bl emit
    cmp r0, #0
    beq r_abort
    mov r0, r8
    mov r1, r9
    cmp r1, #0
    bne 7f
    adds r0, #1
7:  mov r8, r0
    subs r5, #1
    b r_q

r_ctrl:
    cmp r0, #0xF1
    bne 1f
    movs r1, #0
    mov r10, r1
    adds r7, #1
    b r_fetch
1:  cmp r0, #0xF2
    bne 2f
    movs r1, #0x80
    lsls r1, r1, #8
    mov r10, r1
    adds r7, #1
    b r_fetch
2:  cmp r0, #0xFC
    bne 3f
    movs r0, #0
    bl flush
    ldr r0, [sp, #0]
    adds r0, #0x80
    str r0, [sp, #0]
    adds r4, r0, #0
    adds r7, #1
    b r_fetch
3:  cmp r0, #0xF9
    bne 4f
    str r7, [sp, #4]
    ldr r1, L_NAMEPTR
    ldr r7, [r1]
    b r_fetch
4:  cmp r0, #0xF8
    bhi 5f
    cmp r0, #0xF3
    blo 5f
    adds r7, #2    @ F3~F8 + 인수 1
    b r_fetch
5:  cmp r0, #0xF0
    bne 6f
    adds r7, #2    @ F0 xx (원본 확장 글자) — 쓰지 않음, 건너뜀
    b r_fetch
6:  adds r7, #1    @ FA, FB
    b r_fetch

r_done:
    movs r0, #0
    bl flush
r_abort:
    adds r0, r6, #0
    add sp, #8
    pop {r3}
    mov r11, r3
    pop {r3}
    mov r10, r3
    pop {r3}
    mov r9, r3
    pop {r3}
    mov r8, r3
    pop {r4-r7}
    pop {r1}
    bx r1

@ ---- 대기 조각이 있으면 빈 조각과 짝지어 칸으로 낸다. r0 무시. 반환 r0 = 1 성공/0 고갈
flush:
    push {lr}
    mov r1, r11
    movs r0, #1
    adds r2, r1, #1
    beq 1f               @ 대기 없음
    movs r0, #0    @ 빈 조각
    bl emit
1:  pop {r1}
    bx r1

@ ---- 조각 하나 내기. r0 = 조각 번호(색 비트 없음). 반환 r0 = 1/0
emit:
    push {lr}
    mov r2, r11
    adds r3, r2, #1
    bne 1f
    @ 대기 없음 -> 왼쪽 조각으로 보관 (색 비트 붙임)
    mov r3, r10
    orrs r0, r3
    mov r11, r0
    movs r0, #1
    pop {r1}
    bx r1
1:  @ 칸 = (A=r2, B=r0)
    movs r3, #0
    mvns r3, r3
    mov r11, r3              @ 대기 비움
    adds r1, r0, #0
    adds r0, r2, #0
    bl cell
    pop {r1}
    bx r1

@ ---- 칸 찾기/할당 후 타일맵 쓰기. r0 = A(색 포함), r1 = B. r4(render) = 칸 위치(갱신)
cell:
    push {r5-r7, lr}
    @ 활성 리스트 검색
    ldr r2, L_ACTIVE
    ldr r3, [r2]
c_a:
    cmp r3, #0
    beq c_old
    ldrh r5, [r3, #4]
    cmp r5, r0
    bne c_an
    ldrh r5, [r3, #6]
    lsls r5, r5, #17
    lsrs r5, r5, #17
    cmp r5, r1
    beq c_put
c_an:
    ldr r3, [r3]
    b c_a
c_old:
    @ 지난 프레임 리스트 검색 (r6 = 이전 노드 주소의 next 칸)
    ldr r6, L_OLD
    ldr r3, [r6]
c_o:
    cmp r3, #0
    beq c_new
    ldrh r5, [r3, #4]
    cmp r5, r0
    bne c_on
    ldrh r5, [r3, #6]
    lsls r5, r5, #17
    lsrs r5, r5, #17
    cmp r5, r1
    bne c_on
    @ 떼어서 활성으로
    ldr r5, [r3]
    str r5, [r6]
    ldr r5, [r2]
    str r5, [r3]
    str r3, [r2]
    b c_put
c_on:
    adds r6, r3, #0
    ldr r3, [r3]
    b c_o
c_new:
    ldr r6, L_FREE
    ldr r3, [r6]
    cmp r3, #0
    bne c_take
    ldr r5, L_OLD
    ldr r3, [r5]
    str r3, [r6]
    movs r7, #0
    str r7, [r5]
    cmp r3, #0
    beq c_fail
c_take:
    ldr r5, [r3]
    str r5, [r6]
    ldr r5, [r2]
    str r5, [r3]
    str r3, [r2]
    strh r0, [r3, #4]
    movs r5, #0x80
    lsls r5, r5, #8
    orrs r5, r1
    strh r5, [r3, #6]
c_put:
    @ 타일 번호 = 0x37E - (0x02023620 - node)/4
    ldr r5, L_NODETOP
    subs r5, r5, r3
    lsrs r5, r5, #2
    ldr r6, L_37E
    subs r6, r6, r5
    strh r6, [r4]
    adds r6, #1
    adds r5, r4, #0
    adds r5, #0x40
    strh r6, [r5]
    adds r4, #2
    movs r0, #1
    pop {r5-r7}
    pop {r1}
    bx r1
c_fail:
    movs r0, #0
    pop {r5-r7}
    pop {r1}
    bx r1

@ ---- 업로드: 원래 0x080bc094 대체. 활성 리스트에서 플래그 노드의 타일 2장을 조각으로 합성
upload:
    push {r4-r7, lr}
    ldr r0, L_ACTIVE
    ldr r4, [r0]
    ldr r0, L_BGCNT
    ldrh r0, [r0]
    movs r1, #0xC
    ands r0, r1
    lsls r0, r0, #12
    movs r1, #0xC0
    lsls r1, r1, #19    @ 0x06000000
    adds r0, r0, r1
    mov r12, r0              @ 타일 기준
u_loop:
    cmp r4, #0
    beq u_end
    ldrh r1, [r4, #6]
    lsls r2, r1, #16
    bpl u_next           @ bit15 없음
    lsls r1, r1, #17
    lsrs r1, r1, #17
    strh r1, [r4, #6]    @ 플래그 지움
    ldrh r0, [r4, #4]
    @ 타일 주소
    ldr r2, L_NODETOP
    subs r2, r2, r4
    lsrs r2, r2, #2
    ldr r3, L_37E
    subs r3, r3, r2
    lsls r3, r3, #5
    add r3, r12              @ r3 = VRAM 목적지
    ldr r2, L_QDAT
    lsls r5, r0, #17
    lsrs r5, r5, #17
    lsls r5, r5, #5
    adds r5, r5, r2    @ r5 = 왼쪽 조각
    lsls r1, r1, #5
    adds r6, r1, r2    @ r6 = 오른쪽 조각
    movs r7, #16
    lsrs r0, r0, #15    @ r0 = 색 비트(0/1)
u_row:
    ldrh r1, [r5]
    ldrh r2, [r6]
    lsls r2, r2, #16
    orrs r1, r2
    cmp r0, #0
    beq 1f
    lsls r1, r1, #2
1:  stmia r3!, {r1}
    adds r5, #2
    adds r6, #2
    subs r7, #1
    bne u_row
u_next:
    ldr r4, [r4]
    b u_loop
u_end:
    pop {r4-r7}
    pop {r0}
    bx r0

.align 2
L_GTAB:    .word GTAB_ADDR
L_QDAT:    .word QDAT_ADDR
L_NAMEPTR: .word 0x02023634
L_ACTIVE:  .word 0x02023628
L_OLD:     .word 0x0202362C
L_FREE:    .word 0x02023630
L_NODETOP: .word 0x02023620
L_37E:     .word 0x37E
L_BGCNT:   .word 0x02004F34
