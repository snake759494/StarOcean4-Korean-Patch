"""Authored full-sentence effect templates; only numeric values are substituted."""
import json,re
from pathlib import Path
from .skills_ko import K as SKILLS
NUMBER=re.compile(r'\d+(?:[.,]\d+)*')
P={}
for en,ko in [('poison','독'),('stun status','기절'),('frozen status','동결'),('paralysis','마비'),('silence','침묵'),('fog status','안개'),('curse status','저주'),('pumpkin status','호박'),('void status','보이드')]:
    P['Cures '+en]=ko+' 치료'
    P['Cures '+en+' (party)']='아군 전원의 '+ko+' 치료'
    P['Grants immunity to '+en]=ko+' 무효'
    P['{n}% immunity to '+en]='{0}% 확률로 '+ko+' 무효'
    P['Adds '+en.replace(' status','')+' effect to attacks']='공격에 '+ko+' 효과 추가'
for en,ko in [('earth','땅'),('water','물'),('fire','불'),('wind','바람'),('thunder','번개'),('light','빛'),('darkness','어둠')]:
    P['Adds '+en+' element to attacks']='공격에 '+ko+' 속성 부여'
    P['Absorbs '+en+'-based HP damage']=ko+' 속성 HP 피해 흡수'
    P['Recovers {n}% of '+en+'-based damage as MP']=ko+' 속성 피해의 {0}%만큼 MP 회복'
    P['+{n}% damage for '+en+' symbols']=ko+' 속성 문장술 피해 +{0}%'
    P['Nullifies '+en+' symbols {n}% of the time']='{0}% 확률로 '+ko+' 속성 문장술 무효'
for stat in ['ATK','DEF','GRD','HIT','INT','Maximum HP','Maximum MP','Maximum HP/MP','ATK/INT/DEF/HIT/GRD']:
    korean=stat.replace('Maximum','최대')
    for sign in ['+','-']:
        for unit in ['','%']:
            P[stat+' '+sign+'{n}'+unit]=korean+' '+sign+'{0}'+unit
    P[stat+' +{n} (permanent)']=korean+' 영구 +{0}'
for stat in ['ATK','INT','DEF']:
    P[stat+' +{n}% for {n} seconds']='{1}초 동안 '+stat+' +{0}%'
    P['Enemy '+stat+' -{n}% for {n} seconds']='{1}초 동안 적의 '+stat+' -{0}%'
    P['Enemy '+stat+' +{n}%']='적의 '+stat+' +{0}%'
    P[stat+' +{n}% for five battles']='5회 전투 동안 '+stat+' +{0}%'
for en,ko in [('HP','HP'),('MP','MP'),('HP/MP','HP/MP')]:
    P['Restores {n}% of '+en]=ko+' {0}% 회복'
    P['Restores {n}% of '+en+' (party)']='아군 전원의 '+ko+' {0}% 회복'
    P['Restores {n}% '+en+' (usable once every five battles)']=ko+' {0}% 회복 (5회 전투마다 사용 가능)'
    P[en+' damage +{n}%']=ko+' 피해 +{0}%'
    P['Nullifies '+en+' damage {n}% of the time']='{0}% 확률로 '+ko+' 피해 무효'
    P['Restores {n}% of '+en+' periodically in battle']='전투 중 일정 시간마다 '+ko+' {0}% 회복'
    P['Drains '+en+' periodically in battle']='전투 중 일정 시간마다 '+ko+' 감소'
for en,ko in [('humanoids','인간'),('plants','식물'),('insects','곤충'),('undead','사령'),('mechs','기계'),('birds','조류'),('demons','마물'),('animals','동물')]:
    P['Nullifies damage from '+en+' {n}% of the time']='{0}% 확률로 '+ko+'형 적에게 받는 피해 무효'
    P['+{n}% damage to '+en]=ko+'형 적에게 주는 피해 +{0}%'
for en,ko in [('fire','불꽃'),('wind','바람'),('lightning','번개'),('light energy','빛'),('earth','바위'),('ice','얼음'),('mystic energy','신비한 기운'),('dark energy','어둠')]:
    for action,verb in [('guarding','가드'),('attacking','공격')]:
        P['Shoots a blast of '+en+' when '+action]=verb+' 시 '+ko+' 발사'
        P['Shoots blasts of '+en+' when '+action]=verb+' 시 '+ko+' 연속 발사'
for line in '''Cures all status ailments|모든 상태 이상 치료
Cures all status ailments (party)|아군 전원의 모든 상태 이상 치료
{n}% immunity to all status ailments|{0}% 확률로 모든 상태 이상 무효
Revives from incap and restores {n}% HP/MP|전투 불능 회복, HP/MP {0}% 회복
Revives from incap (usable once every five battles)|전투 불능 회복 (5회 전투마다 사용 가능)
Revives from incap and restores {n}% HP/MP (party)|아군 전원의 전투 불능 회복, HP/MP {0}% 회복
Required to use the Pickpocket command|소매치기 사용에 필요
(Gone)|소멸
+{n}% Fol for three battles|3회 전투 동안 획득 FOL +{0}%
+{n}% EXP for three battles|3회 전투 동안 획득 EXP +{0}%
Elemental resistance +{n} for five battles|5회 전투 동안 방어 속성 +{0}
DEF +{n}% for {n} battles|{1}회 전투 동안 DEF +{0}%
MP cost -{n}% for {n} battles|{1}회 전투 동안 소비 MP -{0}%
Prevents enemy targeting for {n} battles|{0}회 전투 동안 적의 표적이 되지 않음
Grants "Convert" status for {n} seconds|{0}초 동안 컨버트 상태
Grants "Focus" status for {n} seconds|{0}초 동안 정신 집중 상태
Grants "Berserk" status for {n} seconds|{0}초 동안 버서크 상태
Grants "Mindflare" status for {n} seconds|{0}초 동안 번 스피릿 상태
Grants "Symbolic Weapon" status for {n} seconds|{0}초 동안 매직 웨폰 상태
Skills cost {n} MP for {n} seconds|{1}초 동안 스킬 소비 MP가 {0}
Elemental resistance +{n} for {n} seconds|{1}초 동안 방어 속성 +{0}
All parameters +{n}% for {n} seconds|{1}초 동안 모든 능력치 +{0}%
Enemy elemental resistance -{n} for {n} seconds|{1}초 동안 적의 방어 속성 -{0}
Invincible but can't act for {n} seconds|{0}초 동안 무적 및 기절 상태
ATK doubled but maximum HP halved|ATK 2배, 최대 HP 절반
ATK doubled but maximum MP halved|ATK 2배, 최대 MP 절반
INT doubled but maximum HP halved|INT 2배, 최대 HP 절반
INT doubled but maximum MP halved|INT 2배, 최대 MP 절반
Increases chance of surviving incap via Fury|근성으로 살아남을 확률 증가
Restores {n}% of HP; sometimes causes poison|HP {0}% 회복, 확률적으로 독 발생
Restores all HP or causes incapacitation|HP 완전 회복 또는 전투 불능
Randomly restores HP, but sometimes reduces it|무작위로 HP 회복, 때로는 감소
INT/DEF/GRD up (only for a certain character)|특정 캐릭터의 INT/DEF/GRD 상승
MP cost -{n}% in battle|전투 중 소비 MP -{0}%
Grants MP protection in battle (HP cost: {n}%)|전투 중 MP 보호 (HP {0}% 소비)
Allows instant escape from battles|전투에서 즉시 도주
Silences all sound|모든 소리를 없앰
Creates a shockwave when guarding|가드 시 충격파 발생
Detonates a wide-area explosion in one minute|1분 뒤 광범위 폭발
Increases critical hit chance|크리티컬 발생 확률 증가
{n} HP wide-area damage|광범위에 HP 피해 {0}
Prevents surprise attacks|기습 방지
Causes the user to self-destruct|사용자 자폭
Generates a seed when used|사용하면 씨앗 생성
All time stops for one second|1초 동안 모든 시간 정지
Causes permanent rage during battle; DEF halved|전투 중 항상 분노 상태, DEF 절반
Automatically revives from incap once per battle|전투마다 한 번 자동 소생
Automatically revives from incap, then vanishes|자동 소생 후 소멸
Instantly kills scumbags {n}% of the time|{0}% 확률로 친케형 적 즉사
Adds one hit chance per attack|공격마다 추가 타격 1회
Adds two hit chances per attack|공격마다 추가 타격 2회
Absorbs HP from an enemy|적의 HP 흡수
Absorbs MP from an enemy|적의 MP 흡수
Silences an enemy|적을 침묵 상태로 만듦
Curses an enemy|적에게 저주 부여
Poisons an enemy|적에게 독 부여
Stuns an enemy|적을 기절시킴
Freezes an enemy|적을 동결시킴
Enemy ATK/INT +{n}%|적의 ATK/INT +{0}%
{n} HP damage to target and nearby enemies|대상과 주변 적에게 HP 피해 {0}
Causes attacks to damage allies as well|공격 시 아군에게도 피해를 줌
Silences enemies in a wide area|광범위의 적을 침묵 상태로 만듦
Curses enemies in a wide area|광범위의 적에게 저주 부여
Poisons enemies in a wide area|광범위의 적에게 독 부여
Stuns enemies in a wide area|광범위의 적을 기절시킴
Freezes enemies in a wide area|광범위의 적을 동결시킴
...Makes the user look bad to others|동료 전원의 호감도 하락
Makes the user look good to others|동료 전원의 호감도 상승
Places drinker in poison status|마신 사람이 독 상태가 됨
Places drinker in pumpkin status|마신 사람이 호박 상태가 됨
Places drinker in silence status|마신 사람이 침묵 상태가 됨
Places drinker in frozen status|마신 사람이 동결 상태가 됨
Places drinker in curse status|마신 사람이 저주 상태가 됨
Places drinker in fog status|마신 사람이 안개 상태가 됨
Places drinker in paralyzed status|마신 사람이 마비 상태가 됨
Sets drinker's HP to {n}|마신 사람의 HP가 {0}이 됨
+{n}% EXP after each battle|전투 후 획득 EXP +{0}%
+{n}% Fol after each battle|전투 후 획득 FOL +{0}%
Rush Gauge charge rate +{n}|러시 게이지 상승률 +{0}
Reduces symbol casting time by half|문장술 시전 시간 절반
Reduces symbol casting time to zero|문장술 즉시 시전
Grants "No Guard" status|가드리스 상태 부여'''.splitlines():
    en,ko=line.split('|');P[en]=ko

_source=json.loads((Path(__file__).parent/'source/0000_3_0.json').read_text(encoding='utf-8'))
_skill_en={r['source']:SKILLS[r['id']] for r in _source if r['id'] in SKILLS}
for en,ko in _skill_en.items():
    P['Casts "'+en+'" at level {n}']='레벨 {0} '+ko+' 발동'
    P['Casts "'+en+'"']=ko+' 발동'
    P['Teaches the "'+en+'" skill']=ko+' 스킬 습득'
    P['Teaches the "'+en+'" symbol']=ko+' 문장술 습득'
    P['Teaches the "'+en+'" attack']=ko+' 필살기 습득'
K={}
UNMATCHED=[]
for row in _source:
    if not 30000<=row['id']<31000:continue
    source=row['source'].strip();key=NUMBER.sub('{n}',source)
    if key in P:K[row['id']]=P[key].format(*NUMBER.findall(source))
    elif source and not source.isdigit():UNMATCHED.append((row['id'],source))
