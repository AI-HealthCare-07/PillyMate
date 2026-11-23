/** FE-2 화면 간 임시 데이터. 새로고침하면 초기화됩니다.
 * TODO(API): 백엔드의 처방 업로드 응답(처방 ID, OCR 필드, 이미지 URL)을
 * 확정한 뒤 서버 상태/요청 캐시로 교체하세요. 실제 의료정보를 localStorage에 저장하지 마세요.
 */
let draft = null;
export function setPrescriptionDraft(next) {
  if (draft?.previewUrl && draft.previewUrl !== next?.previewUrl) URL.revokeObjectURL(draft.previewUrl);
  draft = next;
}
export function getPrescriptionDraft() { return draft; }
export function clearPrescriptionDraft() {
  if (draft?.previewUrl) URL.revokeObjectURL(draft.previewUrl);
  draft = null;
}

/**
 * 건강기록의 '확인 전' 처방을 확인하러 갈 때 — 그 기록의 병원·날짜·병명·읽어 둔 약을 임시 데이터로 채워요.
 * 확인을 마치면 같은 아이·날짜·병원의 기록으로 저장돼서 '확인 전' 기록을 대신해요.
 */
export function draftFromVisit(visit) {
  const ocrMeds =
    visit.ocrMeds ??
    visit.meds.map((m, i) => ({
      id: `${visit.id}m${i}`, name: m.name, dose: { value: '' }, perDay: { value: '' }, days: { value: m.days ?? '' }, timing: { value: '' },
    }));
  setPrescriptionDraft({
    childId: visit.childId,
    disease: visit.title,
    note: visit.note ?? '',
    status: 'pending-visit',
    visitId: visit.id,
    ocr: { hospital: visit.hospital, date: visit.date, disease: visit.title },
    ocrMeds: ocrMeds.map((m) => ({ ...m })),
    guideReady: false,
  });
}
