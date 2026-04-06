import { useQuery } from "@tanstack/react-query";
import type { ExaminationsListResponse } from "../types";

import { apiFetch } from "../../../lib/auth";

type Params = {
	examDate: string;
	sortBy: string;
	sortOrder: string;
	patientId: string;
	patientName: string;
	limit: number;
	offset: number;
};

const fetchExaminations = async ({
	examDate,
	sortBy,
	sortOrder,
	patientId,
	patientName,
	limit,
	offset,
}: Params) => {
	const params = new URLSearchParams({
		exam_date: examDate,
		sort_by: sortBy,
		sort_order: sortOrder,
		limit: String(limit),
		offset: String(offset),
	});
	const id = patientId.trim();
	const name = patientName.trim();
	if (id) {
		params.set("patient_id", id);
	}
	if (name) {
		params.set("patient_name", name);
	}
	const response = await apiFetch(`/api/examinations?${params.toString()}`);

	if (!response.ok) {
		throw new Error("診察一覧の取得に失敗しました");
	}

	return (await response.json()) as ExaminationsListResponse;
};

export const useDiagnosisList = (p: Params) =>
	useQuery({
		queryKey: [
			"examinations",
			p.examDate,
			p.sortBy,
			p.sortOrder,
			p.patientId,
			p.patientName,
			p.limit,
			p.offset,
		],
		queryFn: () => fetchExaminations(p),
		refetchOnWindowFocus: true,
	});
