import { useQuery } from "@tanstack/react-query";
import type { ExaminationDetailResponse } from "../types";

import { apiFetch } from "../../../lib/auth";

const fetchExaminationDetail = async (id: string) => {
	const response = await apiFetch(`/api/examinations/${id}`);

	if (response.status === 404) {
		return null;
	}

	if (!response.ok) {
		throw new Error("診察詳細の取得に失敗しました");
	}

	return (await response.json()) as ExaminationDetailResponse;
};

export const useDiagnosisDetail = (id: string) =>
	useQuery({
		queryKey: ["examination", id],
		queryFn: () => fetchExaminationDetail(id),
		refetchOnWindowFocus: true,
	});
