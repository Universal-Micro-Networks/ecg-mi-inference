// 患者ドメインの型定義
export interface Patient {
  id: string;
  name: string;
  birthDate?: string;
  createdAt: string;
  updatedAt: string;
}

export interface PatientId {
  value: string;
}
