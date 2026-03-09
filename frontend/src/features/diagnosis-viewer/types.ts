export type PatientDetail = {
	id: string;
	external_id: string;
	name: string;
	gender: "男性" | "女性" | string;
	birth_date: string;
};

export type InferenceDetail = {
	status: "未実行" | "実行中" | "完了" | "エラー" | string;
	risk_score?: number;
	risk_level?: "低" | "中" | "高" | string;
	executed_at?: string;
};

export type ExaminationDetail = {
	id: string;
	exam_date: string;
	created_at: string;
	mfer_file_path?: string;
	csv_file_path?: string;
	patient: PatientDetail;
	inference?: InferenceDetail | null;
};

export type ExaminationDetailResponse = ExaminationDetail | null;

export type InferenceStatusResponse = {
	status: InferenceDetail["status"];
	risk_score?: number;
	risk_level?: InferenceDetail["risk_level"];
	executed_at?: string;
};
