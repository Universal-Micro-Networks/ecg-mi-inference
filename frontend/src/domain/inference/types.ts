// 推論ドメインの型定義
export interface InferenceResult {
  id: string;
  ecgRecordId: string;
  riskScore: number;
  riskLevel: 'low' | 'medium' | 'high';
  createdAt: string;
}
