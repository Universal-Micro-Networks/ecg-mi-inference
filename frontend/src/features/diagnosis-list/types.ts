export type PatientSummary = {
	id: string;
	external_id: string;
	name: string;
	gender: "男性" | "女性" | string;
	age: number;
};

export type ExaminationSummary = {
	id: string;
	exam_date: string;
	created_at?: string;
	patient: PatientSummary;
};

export type ExaminationsListResponse = {
	items: ExaminationSummary[];
	total: number;
};
