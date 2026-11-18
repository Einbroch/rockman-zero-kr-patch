# 록맨 제로 1~4 한글패치

GBA 「ロックマンゼロ」 1~4편(일본판) 한글패치 작업 폴더.
일본어 원문에서 새로 번역했고, 대사는 12px 가변폭 한글 출력기(새로 짠 비트맵 합성식)로 찍는다.


> 롬은 저장소·배포물에 넣지 않는다(`.gitignore`). 배포는 [릴리즈](../../releases)의 IPS·xdelta 패치만.

## 시험판

| 편 | 판 | 원본 롬(일본판) | 원본 CRC32 | 결과 CRC32 |
|---|---|---|---|---|
| 록맨 제로 | v0.9.5 | `Rockman Zero (Japan).gba` (8MB) | `FF2A67B1` | `8794236C` |
| 록맨 제로 2 | v0.9.6 | `Rockman Zero 2 (Japan).gba` (8MB) | `9B5C8A4C` | `E502401A` |
| 록맨 제로 3 | v0.9.5 | `Rockman Zero 3 (Japan).gba` (8MB) | `5A2C41A9` | `04514A8F` |
| 록맨 제로 4 | v0.9.4 | `Rockman Zero 4 (Japan).gba` (16MB) | `ECE42D0E` | `D238E897` |

패치 결과는 모두 16MB 다. 각 zip 의 `읽어주세요.txt` 에 적용 방법·들어간 것·확인한 곳이 있다.
모두 **시험판**이다. 처음부터 끝까지 통과 플레이 검증은 하지 않았다.

## 들어간 것(공통)
- 대사 전부와 시스템 문자열(브리핑·메뉴·엘프·장비·저장·스태프 롤 등).
- 그림 글자: 타이틀 로고, 시작 안내·타이틀 메뉴, 일시정지(서브) 화면, 미션 결과 화면, 코드네임, 게임오버.
  3·4편은 오프닝 문단도 다시 그렸다.
- 글꼴: 갈무리(Galmuri) 7·9·11 — SIL OFL 1.1 (`LICENSE-Galmuri.txt`). 4편 오프닝 문단 그림만 맑은 고딕.

## 확인한 것·남은 것
편마다 다르다. 자세한 작업 기록은 [HANDOFF.md](HANDOFF.md).
- 1편: 타이틀·대사·서브 화면·결과 화면 확인. 칭호 도달 경로 일부·엔딩 통과 미확인.
- 2편: 대사·서브 화면 두 벌(첫 미션 주황판·일반 초록판)·결과 화면 확인. 통신 대전 그림 미확인.
- 3편: 타이틀·오프닝·첫 미션·일시정지·결과·게임오버 확인. 베이스·엘프 관리·디스크·저장·엔딩 미확인.
- 4편: 타이틀·오프닝 문단·첫 미션 대사·일시정지·게임오버·결과 화면 확인. 저장·캐러밴·칩 제작·데이터베이스·엔딩 미확인.

## 폴더
| 폴더 | 내용 |
|---|---|
| `rz1/` ~ `rz4/` | 편별 빌드 스크립트, 번역 원고(`ko/` 대사, `ko_sys/` 시스템 문자열), 그림 글자 모듈 |
| `rz2/asm/` | 2~4편 공용 가변폭 출력기·문자열 스캐너(Thumb 어셈블리, keystone 으로 조립) |
| `tools/` | LZ77·IPS·폰트·타일 도구, 에뮬레이터(emucap/Mesen) 확인 도우미 |
| `external/fonts/` | 갈무리 BDF |

## 다시 만들기
필요한 것: Python 3, `keystone-engine`, `pillow`. 일본판 롬을 `roms/` 에 둔다.
2~4편은 원문 목록(`ref/`, 저장소에 없음)이 먼저 있어야 한다. 이 목록은 일본판 롬에서 뽑는다:

```bash
python tools/dump_sequel_text.py 2 3 4
python rz2/dump_system.py
python rz3/dump_system.py
python rz4/dump_system.py
```

그다음 편마다:

```bash
python rz1/build.py
python rz2/build_dialogue.py --screens
python rz3/build_dialogue.py
python rz4/build_dialogue.py
python tools/mkips.py "roms/Rockman Zero 4 (Japan).gba" rz4/out/rz4_dev.gba out.ips
```

1편은 원문 덤프 `rz1/script_jp.json`(`rz1/dump_jp.py` 로 생성)이 필요하다.
