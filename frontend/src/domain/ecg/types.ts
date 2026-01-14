// 心電図ドメインの型定義
export interface EcgRecord {
  id: string;
  patientId: string;
  recordedAt: string;
  createdAt: string;
}
