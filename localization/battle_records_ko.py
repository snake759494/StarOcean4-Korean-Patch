"""Reviewed numeric variants of authored battle collection conditions.

Only complete source sentences listed below match. Numbers are copied verbatim;
unknown conditions remain untouched, never guessed from individual words.
"""
import json,re
from pathlib import Path
PATTERNS={}
for line in '''
Defeat {n} enemies|적 {n}마리 처치
Register {n} preemptive attacks|선제공격 {n}회 성공
Deal at least {n} points of damage|피해 {n} 이상 주기
Land {n} hits in total|누적 {n}회 명중
Deal exactly {n} points of damage|정확히 {n}의 피해 주기
Land {n} hits during Rush Mode|러시 모드 중 {n}회 명중
Land {n} consecutive hits unassisted|혼자서 {n}회 연속 명중
Pull off {n} Blindsides|사이드 아웃 {n}회 성공
Fight as battle leader for {n} minutes|전투 리더로 누적 {n}분 전투
Attack first {n} times in a row|{n}회 연속 첫 공격 성공
Stay in Rush Mode for {n} seconds|러시 모드 {n}초 유지
Land {n} consecutive hits from in front|정면에서 {n}회 연속 명중
Obtain {n} Anthropology item drops|인간 지식으로 아이템 {n}개 획득
Win {n} colosseum solo battles|투기장 개인전 {n}회 승리
Land a {n}-hit Rush Combo|러시 콤보 {n}회 연계
Press {n} buttons|버튼 {n}회 누르기
Squat {n} times|{n}회 쪼그려 앉기
Defeat {n} humanoid enemies|인간형 적 {n}마리 처치
Defeat {n} poisoned enemies|독에 걸린 적 {n}마리 처치
Jump for a total height of {n} meters|누적 점프 높이 {n}미터 달성
Win {n} consecutive colosseum solo battles|투기장 개인전 {n}연승
Deal {n} points of damage without a weapon|무기 없이 피해 {n} 주기
Recover from poison {n} times|독 상태에서 {n}회 회복
Win {n} battles without using MP|MP를 쓰지 않고 전투 {n}회 승리
Survive incapacitation via Fury {n} times|전투 불능이 될 공격을 근성으로 {n}회 버티기
Recover from paralysis {n} times|마비 상태에서 {n}회 회복
Take no damage {n} times in a row|받은 피해 0을 {n}회 연속 기록
Defeat {n} plant enemies|식물형 적 {n}마리 처치
Defeat {n} enemies using only jump attacks|점프 공격만으로 적 {n}마리 처치
Land {n} consecutive long-range attacks|원거리 공격 {n}회 연속 명중
Obtain {n} Botany item drops|식물 지식으로 아이템 {n}개 획득
Interrupt an enemy's casting {n} times|적의 문장술 시전 {n}회 방해
Recover from cursed status {n} times|저주 상태에서 {n}회 회복
Survive incapacitation via Fury {n} times in a row|전투 불능이 될 공격을 근성으로 {n}회 연속 버티기
Absorb a total of {n} MP|MP 누적 {n} 흡수
Recover from incapacitation {n} times in one battle|한 전투에서 전투 불능 상태로부터 {n}회 회복
Defeat {n} paralyzed enemies|마비된 적 {n}마리 처치
Defeat {n} types of enemies|{n}종류의 적 처치
Fight {n} battles|전투 {n}회 참가
Defeat {n} insect enemies|곤충형 적 {n}마리 처치
Reduce an enemy's HP to {n}|적의 남은 HP를 {n}으로 만들기
Get enraged {n} times|분노 상태 {n}회 돌입
Scan {n} enemies|에너미 서치 {n}회 사용
Land {n} critical hits during Rush Mode|러시 모드 중 크리티컬 {n}회 명중
Spend a total of {n} minutes airborne|공중 체류 시간 누적 {n}분 달성
Stab enemies {n} times with a rapier|레이피어 찌르기 공격 {n}회
Defeat {n} enemies using only symbols|문장술만으로 적 {n}마리 처치
Defeat {n} consecutive enemies of the same type|같은 종류의 적 {n}마리 연속 처치
Defeat {n} Grigori|그리골리 {n}마리 처치
Become incapacitated {n} times|전투 불능 {n}회
Get knocked down {n} times|누적 {n}회 다운
Win with {n} MP remaining|남은 MP가 {n}인 상태로 승리
Earn a total of {n} Fol|누적 {n}폴 획득
Hide {n} times|숨기 {n}회
Roll forward a total of {n}km|앞으로 굴러 누적 {n}킬로미터 이동
Obtain {n} Parapsychology item drops|사령 지식으로 아이템 {n}개 획득
Get knocked down {n} times in one battle|한 전투에서 {n}회 다운
Defeat {n} undead enemies|언데드형 적 {n}마리 처치
Silence {n} enemies in a row|적 {n}마리에게 연속으로 침묵 부여
Roll forward {n} times|앞으로 {n}회 구르기
Defeat {n} silenced enemies|침묵에 걸린 적 {n}마리 처치
Land the battle-winning blow {n} times|전투를 끝내는 마지막 일격 {n}회
Win in {n} seconds or less|{n}초 이내 승리
Defeat {n} enemies using jump attacks|점프 공격으로 적 {n}마리 처치
Defeat {n} mechanical enemies|기계형 적 {n}마리 처치
Activate Rush Mode {n} times|러시 모드 {n}회 발동
Defeat {n} enemies without being knocked down|다운되지 않고 적 {n}마리 처치
Obtain {n} Robotics item drops|기계 지식으로 아이템 {n}개 획득
Guard against {n} consecutive attacks|공격 {n}회 연속 가드
Land the battle-winning blow {n} times in a row|전투를 끝내는 마지막 일격 {n}회 연속 성공
Defeat {n} consecutive enemies without being knocked down|다운되지 않고 적 {n}마리 연속 처치
Defeat {n} Kokabiel Spawn|코카비엘 비트 {n}마리 처치
Defeat {n} fogged enemies|안개 상태의 적 {n}마리 처치
Defeat {n} avian enemies|조류형 적 {n}마리 처치
Recover HP with items {n} times in a row|아이템으로 HP {n}회 연속 회복
Earn {n} consecutive Bonus Board bonuses|보너스 보드 보너스 {n}회 연속 획득
Steal successfully {n} times|훔치기 {n}회 성공
Defeat {n} enemies using only special arts|필살기만으로 적 {n}마리 처치
Obtain {n} Ornithology item drops|조류 지식으로 아이템 {n}개 획득
Fight a single battle for {n} minutes|한 전투에서 {n}분 동안 싸우기
Run {n} kilometers in battle|전투 중 누적 {n}킬로미터 달리기
Jump {n} times in a row|{n}회 연속 점프
Blindside one enemy {n} times|같은 적에게 사이드 아웃 {n}회 성공
Defeat {n} demon enemies|마물형 적 {n}마리 처치
Successfully cast a symbol {n} times in a row|문장술 {n}회 연속 시전 성공
Defeat an enemy over {n} meters away|{n}미터 이상 떨어진 적 처치
Use MP in {n} consecutive victorious battles|MP를 사용한 전투에서 {n}회 연속 승리
Obtain {n} Demonology item drops|마물 지식으로 아이템 {n}개 획득
Cast {n} symbols|문장술 {n}회 시전
Defeat {n} enemies using only items|아이템만으로 적 {n}마리 처치
Shatter {n} frozen enemies|얼어붙은 적 {n}마리 격파
Fight for over {n} hours in total|누적 {n}시간 이상 전투
Recover exactly {n} HP|HP를 정확히 {n} 회복
Escape from battle {n} times|전투에서 {n}회 도주
Jump {n} times|누적 {n}회 점프
Absorb a total of {n} HP|HP 누적 {n} 흡수
Defeat {n} airborne enemies|공중에 뜬 적 {n}마리 처치
Defeat {n} animal enemies|동물형 적 {n}마리 처치
Obtain {n} Zoology item drops|동물 지식으로 아이템 {n}개 획득
Revive an incapacitated ally {n} times|전투 불능 아군 {n}회 부활
Use {n} healing symbols in one battle|한 전투에서 HP 회복 문장술 {n}회 사용
Escape from battle {n} times in a row|전투에서 {n}회 연속 도주
Fail to survive incapacitation via Fury {n} times in a row|근성으로 버티지 못하고 {n}회 연속 전투 불능
Get turned into a pumpkin in battle {n} times|전투 중 호박 상태 {n}회
Use Taunt {n} times|도발 {n}회 사용
Win with {n} HP remaining|남은 HP가 {n}인 상태로 승리
Defeat an enemy in one hit {n} times|일격에 적 처치 {n}회
Attack first {n} times|첫 공격 {n}회 성공
Win {n} consecutive battles|전투 {n}연승
Survive {n} surprise attacks|기습당한 전투에서 {n}회 승리
Obtain {n} Entomology item drops|곤충 지식으로 아이템 {n}개 획득
Win {n} battles in a row without taking damage|피해 없이 전투 {n}연승
Defeat an enemy in one hit {n} times in a row|일격에 적 처치 {n}회 연속 성공
Win {n} consecutive battles with no item drops|드롭 아이템 없이 전투 {n}연승
Deal at least {n} points of overkill damage|오버킬 피해 {n} 이상 주기
Defeat {n} cursed enemies|저주에 걸린 적 {n}마리 처치
Win {n} consecutive battles without healing|회복하지 않고 전투 {n}연승
Defeat {n} enemies while HP is at {n}% or less|HP가 {1}% 이하일 때 적 {0}마리 처치
'''.strip().splitlines():
    source,korean=line.split('|',1)
    assert source not in PATTERNS
    PATTERNS[source]=korean

NUMBER=re.compile(r'[0-9][0-9,]*(?:\.[0-9]+)?')
K={}
for row in json.loads((Path(__file__).parent/'source/0000_3_0.json').read_text(encoding='utf-8')):
    if not 50000<=row['id']<51000: continue
    source=row['source'].strip()
    template=NUMBER.sub('{n}',source)
    if template not in PATTERNS: continue
    numbers=NUMBER.findall(source); text=PATTERNS[template]
    if '{n}' in text:
        assert text.count('{n}')==len(numbers)
        for n in numbers:text=text.replace('{n}',n,1)
    else:text=text.format(*numbers)
    fixed_numbers=NUMBER.findall(re.sub(r'\{(?:n|\d+)\}','',PATTERNS[template]))
    assert sorted(NUMBER.findall(text))==sorted(numbers+fixed_numbers)
    K[row['id']]=text

# Share only whole, identical condition sentences between character lists.
from localization.battle_conditions_ko import K as INDIVIDUAL
assert not (set(INDIVIDUAL)&set(K)), 'Individual condition ID overlaps an already reviewed numeric condition'
rows=json.loads((Path(__file__).parent/'source/0000_3_0.json').read_text(encoding='utf-8'))
english_by_id={row['id']:row['source'] for row in rows}
authored={english_by_id[mid]:text for mid,text in INDIVIDUAL.items()}
for row in rows:
    if 50000<=row['id']<51000 and row['source'] in authored:K[row['id']]=authored[row['source']]
assert set(K)==set(range(50000,50901)), ('Unreviewed battle collection conditions remain',sorted(set(range(50000,50901))-set(K)))
