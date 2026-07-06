const path = require("path");
const sharp = require("sharp");

const SRC = path.join(__dirname, "..", "public", "body-human.png.png");
const OUT_DIR = path.join(__dirname, "..", "public");

// 절반으로 나눈 뒤에도 인물이 각 절반 안에서 한쪽으로 치우쳐 있어(빈 여백이 비대칭),
// 실루엣 바운딩 박스 중심을 기준으로 다시 타이트하게 크롭해 두 이미지의 인물 비중을 맞춘다.
const CROP_W = 380;
const CROP_H = 740;
const FRONT_LOCAL_CENTER = { x: 493, y: 383.5 };
const BACK_LOCAL_CENTER = { x: 196, y: 383 };

function cropRect(center, halfW, halfH) {
  const left = Math.round(Math.min(Math.max(center.x - CROP_W / 2, 0), halfW - CROP_W));
  const top = Math.round(Math.min(Math.max(center.y - CROP_H / 2, 0), halfH - CROP_H));
  return { left, top, width: CROP_W, height: CROP_H };
}

async function main() {
  const { width, height } = await sharp(SRC).metadata();
  const halfWidth = Math.floor(width / 2);

  await sharp(SRC)
    .extract({ left: 0, top: 0, width: halfWidth, height })
    .extract(cropRect(FRONT_LOCAL_CENTER, halfWidth, height))
    .toFile(path.join(OUT_DIR, "body-front.png"));

  await sharp(SRC)
    .extract({ left: halfWidth, top: 0, width: width - halfWidth, height })
    .extract(cropRect(BACK_LOCAL_CENTER, width - halfWidth, height))
    .toFile(path.join(OUT_DIR, "body-back.png"));

  console.log(`split ${width}x${height} -> body-front.png, body-back.png (${CROP_W}x${CROP_H}, tight crop)`);
}

main();
