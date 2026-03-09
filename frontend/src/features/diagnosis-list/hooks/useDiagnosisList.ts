import { useQuery } from "@tanstack/react-query";
import type { ExaminationsResponse } from "../types";

type Params = {
	examDate: string;
	sortBy: string;
	sortOrder: string;
};

type HeadersRecord = Record<string, string>;

const getAuthHeader = (): HeadersRecord => {
	const token = localStorage.getItem("auth_token");
	const headers: HeadersRecord = {
		"Content-Type": "application/json",
	};
	if (token) {
		headers.Authorization = `Bearer ${token}`;
	}
	return headers;
};

const fetchExaminations = async ({ examDate, sortBy, sortOrder }: Params) => {
	const params = new URLSearchParams({
		exam_date: examDate,
		sort_by: sortBy,
		sort_order: sortOrder,
	});
	const response = await fetch(`/api/examinations?${params.toString()}`, {
		headers: getAuthHeader(),
	});

	if (!response.ok) {
		throw new Error("診察一覧の取得に失敗しました");
	}

	return (await response.json()) as ExaminationsResponse;
};

export const useDiagnosisList = ({ examDate, sortBy, sortOrder }: Params) =>
	useQuery({
		queryKey: ["examinations", examDate, sortBy, sortOrder],
		queryFn: () => fetchExaminations({ examDate, sortBy, sortOrder }),
		refetchOnWindowFocus: true,
	});
