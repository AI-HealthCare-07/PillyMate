/**
 * 복약 체크 API — 그날 그 먹는 때에 약을 먹였는지.
 * GET /children/{id}/doses: [{ prescription_id, medication_id, medication_name, dose_date, slot, is_taken }]
 *   기록이 없는 먹는 때는 목록에 없어요('기록 없음'). is_taken=false는 '안 먹였어요'.
 * PUT /prescriptions/{id}/doses: { dose_date, items: [{ medication_id, slot, is_taken }] } — 덮어써요.
 */
import { request } from './medicationAlarms.js';

/** 아이의 복약 체크 기록 전체 */
export const fetchChildDoses = (childId) =>
  request(`/children/${encodeURIComponent(childId)}/doses`, { fallback: '복약 기록을 불러오지 못했어요.' });

/** 그날 먹인 약 체크·취소 저장 */
export const saveDoses = (prescriptionId, body) =>
  request(`/prescriptions/${encodeURIComponent(prescriptionId)}/doses`, { method: 'PUT', body, fallback: '복약 체크를 저장하지 못했어요.' });
