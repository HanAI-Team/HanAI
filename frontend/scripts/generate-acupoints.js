const fs = require("fs");
const path = require("path");

// 시각적 참고용 근사 좌표 생성기 (임상적으로 정확한 취혈 위치가 아님).
// 사용자가 지정한 7.5등신 인체 비율 랜드마크(세로 %, VIEW_H 기준)를 기준으로
// 14경락 361혈의 좌표를 선형 보간해 생성한다.
// 출력: frontend/public/acupoints.json (좌표 체계는 viewBox 필드에 함께 저장되어,
// 나중에 실측 데이터로 파일만 교체해도 소비하는 쪽 코드를 바꿀 필요가 없다)

const VIEW_W = 380;
const VIEW_H = 740;
const CENTER_X = VIEW_W / 2;

// 사용자 지정 랜드마크 (%, 정수리=0 ~ 발바닥=100)
const LANDMARK_Y_PCT = {
  crown: 0,
  chin: 13,
  neckBase: 17,
  shoulder: 23,
  elbow: 40,
  wrist: 55,
  navel: 60,
  knee: 75,
  ankle: 90,
  sole: 100,
};

// 위 랜드마크만으로는 팔/다리 말단, 고관절 등 구간을 나누기에 해상도가 부족해
// 최소한으로 보간해 파생시킨 랜드마크 (모두 위 표에서 산식으로 유도됨)
const DERIVED_Y_PCT = {
  hip: LANDMARK_Y_PCT.navel + (LANDMARK_Y_PCT.knee - LANDMARK_Y_PCT.navel) * 0.35,
  handEnd: LANDMARK_Y_PCT.wrist + (LANDMARK_Y_PCT.wrist - LANDMARK_Y_PCT.elbow) * 0.6,
};

const MERIDIAN_NAMES = {
  LU: "폐경", LI: "대장경", ST: "위경", SP: "비경", HT: "심경",
  SI: "소장경", BL: "방광경", KI: "신경", PC: "심포경", TE: "삼초경",
  GB: "담경", LR: "간경", GV: "독맥", CV: "임맥",
};

// segments: 경혈 순번(코드 숫자) 순서대로 지나가는 구간들.
// from/to는 y%(랜드마크 이름 또는 숫자), count는 해당 구간에 속하는 혈 개수,
// offsetPx는 정중선(CENTER_X) 기준 좌우 거리(px, 0=정중선). 각 구간 내부는 선형 보간.
const MERIDIANS = [
  {
    code: "LU", view: "front", side: "right",
    segments: [
      { region: "abdomen", from: "neckBase", to: "shoulder", count: 2, offsetPx: 60 },
      { region: "hand", from: "shoulder", to: "handEnd", count: 9, offsetPx: 150 },
    ],
    names: ["중부", "운문", "천부", "협백", "척택", "공최", "열결", "경거", "태연", "어제", "소상"],
  },
  {
    code: "LI", view: "back", side: "right",
    segments: [
      { region: "hand", from: "handEnd", to: "shoulder", count: 16, offsetPx: 150 },
      { region: "head", from: "neckBase", to: 10, count: 4, offsetPx: 25 },
    ],
    names: ["상양", "이간", "삼간", "합곡", "양계", "편력", "온류", "하렴", "상렴", "수삼리", "곡지", "주료", "수오리", "비노", "견우", "거골", "천정", "부돌", "화료", "영향"],
  },
  {
    code: "ST", view: "front", side: "right",
    segments: [
      { region: "head", from: 8, to: 20, count: 12, offsetPx: 25 },
      { region: "abdomen", from: "shoulder", to: 34, count: 6, offsetPx: 45 },
      { region: "abdomen", from: 34, to: "navel", count: 12, offsetPx: 38 },
      { region: "leg", from: "hip", to: "ankle", count: 10, offsetPx: 38 },
      { region: "foot", from: "ankle", to: 95, count: 5, offsetPx: 34 },
    ],
    names: ["승읍", "사백", "거료", "지창", "대영", "협거", "하관", "두유", "인영", "수돌", "기사", "결분", "기호", "고방", "옥예", "응창", "유중", "유근", "불용", "승만", "양문", "관문", "태을", "활육문", "천추", "외릉", "대거", "수도", "귀래", "기충", "비관", "복토", "음시", "양구", "독비", "족삼리", "상거허", "조구", "하거허", "풍륭", "해계", "충양", "함곡", "내정", "여태"],
  },
  {
    code: "SP", view: "front", side: "left",
    segments: [
      { region: "foot", from: 95, to: "ankle", count: 5, offsetPx: 26 },
      { region: "leg", from: "ankle", to: "hip", count: 6, offsetPx: 22 },
      { region: "abdomen", from: "hip", to: 25, count: 10, offsetPx: 55 },
    ],
    names: ["은백", "대도", "태백", "공손", "상구", "삼음교", "누곡", "지기", "음릉천", "혈해", "기문", "충문", "부사", "복결", "대횡", "복애", "식두", "천계", "흉향", "주영", "대포"],
  },
  {
    code: "HT", view: "front", side: "left",
    segments: [
      { region: "hand", from: "shoulder", to: "handEnd", count: 9, offsetPx: 130 },
    ],
    names: ["극천", "청령", "소해", "영도", "통리", "음극", "신문", "소부", "소충"],
  },
  {
    code: "SI", view: "back", side: "right",
    segments: [
      { region: "hand", from: "handEnd", to: "elbow", count: 8, offsetPx: 130 },
      { region: "back", from: "shoulder", to: 30, count: 7, offsetPx: 55 },
      { region: "head", from: "neckBase", to: 8, count: 4, offsetPx: 25 },
    ],
    names: ["소택", "전곡", "후계", "완골", "양곡", "양로", "지정", "소해", "견정", "노유", "천종", "병풍", "곡원", "견외유", "견중유", "천창", "천용", "관료", "청궁"],
  },
  {
    code: "BL", view: "back", side: "right", alternate: true,
    segments: [
      { region: "head", from: 5, to: "neckBase", count: 10, offsetPx: 25 },
      { region: "back", from: "shoulder", to: "hip", count: 25, offsetPx: 40 },
      { region: "leg", from: "hip", to: "knee", count: 5, offsetPx: 28 },
      { region: "back", from: "shoulder", to: "hip", count: 14, offsetPx: 65 },
      { region: "leg", from: "knee", to: "ankle", count: 5, offsetPx: 32 },
      { region: "foot", from: "ankle", to: 98, count: 8, offsetPx: 30 },
    ],
    names: ["정명", "찬죽", "미충", "곡차", "오처", "승광", "통천", "낙각", "옥침", "천주", "대저", "풍문", "폐유", "궐음유", "심유", "독유", "격유", "간유", "담유", "비유", "위유", "삼초유", "신유", "기해유", "대장유", "관원유", "소장유", "방광유", "중려유", "백환유", "상료", "차료", "중료", "하료", "회양", "승부", "은문", "부극", "위양", "위중", "부분", "백호", "고황", "신당", "의희", "격관", "혼문", "양강", "의사", "위창", "황문", "지실", "포황", "질변", "합양", "승근", "승산", "비양", "부양", "곤륜", "복삼", "신맥", "금문", "경골", "속골", "족통곡", "지음"],
  },
  {
    code: "KI", view: "front", side: "left",
    segments: [
      { region: "foot", from: 98, to: "ankle", count: 6, offsetPx: 38 },
      { region: "leg", from: 88, to: "knee", count: 4, offsetPx: 28 },
      { region: "abdomen", from: 62, to: 25, count: 17, offsetPx: 15 },
    ],
    names: ["용천", "연곡", "태계", "대종", "수천", "조해", "부류", "교신", "축빈", "음곡", "횡골", "대혁", "기혈", "사만", "중주", "황유", "상곡", "석관", "음도", "복통곡", "유문", "보랑", "신봉", "영허", "신장", "욱중", "수부"],
  },
  {
    code: "PC", view: "front", side: "right",
    segments: [
      { region: "abdomen", from: 27, to: 27, count: 1, offsetPx: 50 },
      { region: "hand", from: 27, to: "handEnd", count: 8, offsetPx: 145 },
    ],
    names: ["천지", "천천", "곡택", "극문", "간사", "내관", "대릉", "노궁", "중충"],
  },
  {
    code: "TE", view: "back", side: "left",
    segments: [
      { region: "hand", from: "handEnd", to: 27, count: 13, offsetPx: 130 },
      { region: "back", from: "shoulder", to: 27, count: 2, offsetPx: 60 },
      { region: "head", from: "neckBase", to: 8, count: 8, offsetPx: 25 },
    ],
    names: ["관충", "액문", "중저", "양지", "외관", "지구", "회종", "삼양락", "사독", "천정", "청랭연", "소락", "노회", "견료", "천료", "천유", "예풍", "계맥", "노식", "각손", "이문", "화료", "사죽공"],
  },
  {
    code: "GB", view: "back", side: "right", alternate: true,
    segments: [
      { region: "head", from: 8, to: "neckBase", count: 20, offsetPx: 35 },
      { region: "back", from: "shoulder", to: 40, count: 8, offsetPx: 70 },
      { region: "leg", from: "hip", to: 88, count: 11, offsetPx: 48 },
      { region: "foot", from: "ankle", to: 98, count: 5, offsetPx: 44 },
    ],
    names: ["동자료", "청회", "상관", "함염", "현로", "현리", "곡빈", "솔곡", "천충", "부백", "두규음", "완골", "본신", "양백", "두임읍", "목창", "정영", "승령", "뇌공", "풍지", "견정", "연액", "첩근", "일월", "경문", "대맥", "오추", "유도", "거료", "환도", "풍시", "중독", "슬양관", "양릉천", "양교", "외구", "광명", "양보", "현종", "구허", "족임읍", "지오회", "협계", "족규음"],
  },
  {
    code: "LR", view: "front", side: "left",
    segments: [
      { region: "foot", from: 98, to: "ankle", count: 4, offsetPx: 42 },
      { region: "leg", from: 88, to: "hip", count: 7, offsetPx: 34 },
      { region: "abdomen", from: "hip", to: 32, count: 3, offsetPx: 60 },
    ],
    names: ["대돈", "행간", "태충", "중봉", "여구", "중도", "슬관", "곡천", "음포", "족오리", "음렴", "급맥", "장문", "기문"],
  },
  {
    code: "GV", view: "back", side: null,
    segments: [
      { region: "back", from: "hip", to: "shoulder", count: 14, offsetPx: 0 },
      { region: "head", from: "neckBase", to: "crown", count: 6, offsetPx: 0 },
      { region: "head", from: "crown", to: 13, count: 8, offsetPx: 0 },
    ],
    names: ["장강", "요유", "요양관", "명문", "현추", "척중", "중추", "근축", "지양", "영대", "신도", "신주", "도도", "대추", "아문", "풍부", "뇌호", "강간", "후정", "백회", "전정", "신회", "상성", "신정", "소료", "인중", "태단", "은교"],
  },
  {
    code: "CV", view: "front", side: null,
    segments: [
      { region: "abdomen", from: 72, to: "navel", count: 8, offsetPx: 0 },
      { region: "abdomen", from: "navel", to: 32, count: 6, offsetPx: 0 },
      { region: "abdomen", from: 30, to: "neckBase", count: 8, offsetPx: 0 },
      { region: "head", from: 13, to: 10, count: 2, offsetPx: 0 },
    ],
    names: ["회음", "곡골", "중극", "관원", "석문", "기해", "음교", "신궐", "수분", "하완", "건리", "중완", "상완", "거궐", "구미", "중정", "전중", "옥당", "자궁", "화개", "선기", "천돌", "염천", "승장"],
  },
];

const EXPECTED_COUNT = {
  LU: 11, LI: 20, ST: 45, SP: 21, HT: 9, SI: 19, BL: 67, KI: 27,
  PC: 9, TE: 23, GB: 44, LR: 14, GV: 28, CV: 24,
};

function resolveYPct(v) {
  if (typeof v === "number") return v;
  if (v in LANDMARK_Y_PCT) return LANDMARK_Y_PCT[v];
  if (v in DERIVED_Y_PCT) return DERIVED_Y_PCT[v];
  throw new Error(`알 수 없는 랜드마크: ${v}`);
}

function generate() {
  const points = [];

  for (const m of MERIDIANS) {
    const segCount = m.segments.reduce((sum, seg) => sum + seg.count, 0);
    if (segCount !== m.names.length) {
      throw new Error(`${m.code}: segments 합계(${segCount}) !== names 길이(${m.names.length})`);
    }
    if (segCount !== EXPECTED_COUNT[m.code]) {
      throw new Error(`${m.code}: 총 개수(${segCount})가 표준 혈수(${EXPECTED_COUNT[m.code]})와 다름`);
    }

    let nameIdx = 0;
    for (const seg of m.segments) {
      const yFrom = resolveYPct(seg.from);
      const yTo = resolveYPct(seg.to);
      const isSided = seg.region === "hand" || seg.region === "foot";

      for (let i = 0; i < seg.count; i++) {
        const t = seg.count === 1 ? 0.5 : i / (seg.count - 1);
        const yPct = yFrom + (yTo - yFrom) * t;
        // alternate: 경락 전체를 한쪽에 몰아주는 대신, 점 순서를 좌우로 번갈아 배치해
        // 척추/체측 양쪽에 고르게 분포시킨다 (BL/GB처럼 원래 좌우 대칭인 경락용)
        const pointSide = m.alternate ? (i % 2 === 0 ? "right" : "left") : m.side;
        const dir = pointSide === "left" ? -1 : 1;
        const x = seg.offsetPx === 0 ? CENTER_X : CENTER_X + dir * seg.offsetPx;

        points.push({
          code: `${m.code}${nameIdx + 1}`,
          name: m.names[nameIdx],
          meridian: m.code,
          meridianName: MERIDIAN_NAMES[m.code],
          view: m.view,
          region: seg.region,
          side: isSided && pointSide ? pointSide : null,
          x: Math.round(x),
          y: Math.round((yPct / 100) * VIEW_H),
        });
        nameIdx++;
      }
    }
  }

  return points;
}

const points = generate();
if (points.length !== 361) {
  throw new Error(`총 혈위 개수가 361이 아님: ${points.length}`);
}

const output = {
  viewBox: { width: VIEW_W, height: VIEW_H },
  source: "generated-approximate",
  note: "WHO 표준 비율(cun) 및 세로 랜드마크 기반 선형 보간으로 생성한 시각적 참고용 근사 좌표입니다. 실제 취혈 위치와 정확히 일치하지 않으며, 임상 목적으로 사용할 수 없습니다.",
  landmarks: { ...LANDMARK_Y_PCT, ...DERIVED_Y_PCT },
  points,
};

const outPath = path.join(__dirname, "..", "public", "acupoints.json");
fs.writeFileSync(outPath, JSON.stringify(output, null, 2) + "\n");

const perMeridian = MERIDIANS.map((m) => `${m.code}:${m.names.length}`).join(" ");
console.log(`${points.length}개 혈위 생성 완료 -> ${path.relative(process.cwd(), outPath)}`);
console.log(perMeridian);
