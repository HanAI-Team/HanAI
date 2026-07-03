// public/acupoints.json 소비용 타입.
// 좌표 데이터를 실측 데이터로 교체할 때는 이 타입 형태(shape)만 유지하면
// public/acupoints.json 파일만 바꿔치기해도 됨 (코드 변경 불필요).

export type AcupointView = "front" | "back"
export type AcupointRegion = "head" | "hand" | "foot" | "leg" | "back" | "abdomen"
export type AcupointSide = "left" | "right" | null

export type AcupointRecord = {
  code: string
  name: string
  meridian: string
  meridianName: string
  view: AcupointView
  region: AcupointRegion
  side: AcupointSide
  x: number
  y: number
}

export type AcupointsFile = {
  viewBox: { width: number; height: number }
  source: string
  note: string
  points: AcupointRecord[]
}
