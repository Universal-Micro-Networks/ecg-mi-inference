// 検査一覧機能の型定義

export interface ExamListItem {
  id: string;
  examDateTime: string; // ISO 8601形式 (例: "2025-12-07T14:30:00Z")
  patientId: string; // 患者ID（例: "P-001"）
  patientName: string; // 患者氏名
  gender: 'male' | 'female'; // 性別
  age: number; // 年齢
}
