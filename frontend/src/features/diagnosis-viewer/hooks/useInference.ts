import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import type { InferenceDetail, InferenceStatusResponse } from "../types";

import { apiFetch } from "../../../lib/auth";

const fetchInferenceStatus = async (examinationId: string) => {
	const response = await apiFetch(`/api/inferences/${examinationId}`);

	if (!response.ok) {
		throw new Error("推論ステータスの取得に失敗しました");
	}

	return (await response.json()) as InferenceStatusResponse;
};

const runInferenceRequest = async (examinationId: string) => {
	const response = await apiFetch("/api/inferences", {
		method: "POST",
		body: JSON.stringify({ examination_id: examinationId }),
	});

	if (!response.ok) {
		throw new Error("推論の実行に失敗しました");
	}

	return (await response.json()) as InferenceStatusResponse;
};

export const useInference = (
	examinationId: string,
	initial?: InferenceDetail | null,
) => {
	const [status, setStatus] = useState<InferenceDetail["status"]>(
		initial?.status ?? "未実行",
	);
	const [result, setResult] = useState<InferenceStatusResponse | null>(null);

	useEffect(() => {
		if (initial?.status) {
			setStatus(initial.status);
		}
	}, [initial?.status]);

	const inferenceQuery = useQuery({
		queryKey: ["inference-status", examinationId],
		queryFn: () => fetchInferenceStatus(examinationId),
		enabled: Boolean(examinationId) && status === "実行中",
		refetchInterval: status === "実行中" ? 5000 : false,
	});

	useEffect(() => {
		if (inferenceQuery.data) {
			setResult(inferenceQuery.data);
			setStatus(inferenceQuery.data.status);
		}
	}, [inferenceQuery.data]);

	const runMutation = useMutation({
		mutationFn: () => runInferenceRequest(examinationId),
		onSuccess: (data) => {
			setStatus(data.status);
			setResult(data);
		},
	});

	const runInference = async () => {
		await runMutation.mutateAsync();
	};

	return {
		status,
		result,
		isRunning: status === "実行中",
		runInference,
		isSubmitting: runMutation.isPending,
		error: runMutation.error ?? inferenceQuery.error,
	};
};
