"""Location and spacecraft names checked against Japanese glyph proofs."""
_locations='''배틀 시뮬레이터
행성 에이오스
우르즈 폭포 동굴
해저 동굴
행성 에이오스 남부
미가의 벌레굴
행성 레무릭 탈레이아 평원
행성 레무릭 반엘름 지구
아라네아 성채
별의 배
칼디아논 함내 통로
생체 연구소
칼디아논 모함 지하 도시
제어 타워
비상 우회로
군 시설
행성 로크 아스트랄 대륙
퍼지 신전
아스트랄 동굴
칠성의 동굴
성역으로 가는 옛길
En II 성역
원더링 던전
암흑 행성 바로크다크
창생 궁전
이공간'''.splitlines()
_ships='''SRF003 칼나스
칼나스 Ver.II (E 개량형)
칼나스 Ver.III (무장 강화형)
SRF001 아퀼라
아퀼라 Ver.B (고속 순항함)
SRF002 발레나
SRF004 댄딜라이언
SRF005 엘레미아
팬텀함 (SRF 실루엣)
USTA 워프십
USTA 수송함 칼나스
엘더 순양함 자그자겔
엘더 구축함 잠자기엘
엘더 이민함 도미니온
엘더 전투 전용함 암자니
엘더 소형정 솔
모피스 전투기
모피스 소형 탐사함
모피스 탈출 포드
칼디아논 상륙함
칼디아논 요새 모함
칼디아논 전투정'''.splitlines()
assert len(_locations)==26 and len(_ships)==22
K={**dict(enumerate(_locations,44000)),**dict(enumerate(_ships,60000))}
