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
