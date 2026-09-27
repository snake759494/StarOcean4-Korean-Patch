"""Keep the release note's counts tied to the verified build."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'build/manifest.json').read_text(encoding='utf-8'))
v=json.loads((ROOT/'build/verification.json').read_text(encoding='utf-8'))
c=json.loads((ROOT/'localization/coverage.json').read_text(encoding='utf-8'))
assert v['status']=='PASS' and v['translated_messages_checked']==c['built_translated_messages']
count=c['built_translated_messages'];remaining=c['remaining_message_slots']
note=f'''# 스타오션4 한글패치 — 진행 중인 빌드

전체 한글패치는 아직 미완성입니다. 검증된 현재 빌드는 일본어 메시지 슬롯 {count:,}개를 번역했습니다. 목록의 {c['catalogued_messages']:,}개 중 {remaining:,}개가 미반영 상태입니다. 이 수치는 중복 리소스와 내부 개발용 문구를 포함하며 고유 문장 수나 플레이 진행률이 아닙니다.

## 현재 번역 범위

- 오프닝 도입 자막 13개와 배틀 시뮬레이터의 메뉴·수업 설명 240개
- 공통 안내와 메뉴·상점·저장·불러오기·설정 도움말
- 배틀 컬렉션 900개 조건, 스킬 이름 144개, 스킬 설명 376개
- 아이템 이름 1,048개(개발용 별칭 포함), 무기·장비 설명 115개
- 장비 효과 653개, 장소 26개, 우주선 22개, 몬스터 이름 535개
- 에지·레이미의 출발 대화와 동료 개인 이벤트 76개, 동일한 대사 리소스의 사본
- 원문 바이트가 정확히 일치하는 중복 메시지

번역 API를 호출하지 않고 문장을 직접 작성했습니다. 일본어 원본 글리프를 렌더링하여 문구와 이름을 대조했습니다. 숫자만 다른 조건과 효과는 검토한 한국어 문장에 원문의 수치를 넣습니다. 몬스터 주얼과 개발용 별칭은 일본어 원문이 일치하는 경우에만 검토한 이름을 재사용합니다.

폰트는 게임 폴더의 `NanumSquareNeo-cBd.ttf`(나눔스퀘어 네오 Bold)입니다. 공용 폰트에 한글 {m['added_glyphs']}개를 추가했고 기존 2,099개 글자는 실제 RGBA가 보존됩니다. 공용 한글은 64픽셀 글꼴과 64픽셀 저장 칸을 쓰며, 전진 폭은 72를 유지합니다. 공용 한글과 용량이 부족한 대사 폰트는 흰색 BC7 모드 5와 네 단계 투명도를 사용합니다. 원본 일본어·영문 텍스처는 재양자화하지 않습니다.

## 검증

{v['compressed_chunks_checked']}개 압축 청크의 엄격한 디코딩, 번역 {count:,}개 인코딩, 미번역 메시지 보존, 한글의 흰색 RGB를 확인했습니다. 확장된 메시지·폰트 리소스는 KCAP의 압축 해제 크기도 함께 갱신합니다. 임시 아카이브에서 반복 적용·복구와 알 수 없는 변경 내용의 쓰기 거부를 검사했습니다.

`build/font_render_preview.png`, `build/opening_preview.png`, `build/story_1316_6_preview.png`는 실제 패치 텍스처를 디코딩한 미리보기입니다. 게임 스크린샷이 아닙니다. 이번 작업에서 게임을 실행하지 않았으며 새 번역의 게임 내 표시와 진행 검증은 수행하지 않았습니다.

## 적용과 복구

설치 경로: `C:\\Program Files (x86)\\Steam\\steamapps\\common\\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster`

게임 텍스트 언어는 일본어 슬롯을 사용합니다. `build_and_apply.cmd`는 복구 → 빌드 → 검증 → 게임 폴더 직접 적용 순서로 실행합니다. 실행 중인 게임에는 쓰지 않으며 게임을 자동 실행하지 않습니다.

```text
python -X utf8 patch_tool.py restore
python -X utf8 build_patch.py
python -X utf8 verify_build.py
python -X utf8 patch_tool.py apply
python -X utf8 patch_tool.py verify
```

원본 백업은 `build/*.original.bin`입니다. 모든 대상의 SHA-256을 확인한 뒤 기록하고 다시 읽어 검증합니다. `restore_original.cmd`로 복구할 수 있습니다.

## 남은 작업

스토리·NPC 대사의 대부분, 다수의 아이템 설명·퀘스트·사전 정보가 남아 있습니다. 공용 한글은 로컬 글자 영역과 충돌하지 않도록 최대 973개로 제한합니다. 이를 넘는 번역에는 리소스별 폰트 확장이 더 필요합니다. 압축 공간을 초과한 중복 문구는 `manifest.json`의 `deferred_duplicates`에 기록하며 완료 수에 포함하지 않습니다.

리소스별 현황: `localization/coverage.json`. 번역 소스: `localization/*_ko.py`.
'''
(ROOT/'README_KO.md').write_text(note,encoding='utf-8')
print('Updated README for',count,'verified messages')
