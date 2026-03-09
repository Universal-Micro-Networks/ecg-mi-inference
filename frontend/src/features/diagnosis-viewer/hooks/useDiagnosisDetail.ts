import { useQuery } from "@tanstack/react-query";
import type { ExaminationDetailResponse } from "../types";

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

const fetchExaminationDetail = async (id: string) => {
	const response = await fetch(`/api/examinations/${id}`, {
		headers: getAuthHeader(),
	});

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
