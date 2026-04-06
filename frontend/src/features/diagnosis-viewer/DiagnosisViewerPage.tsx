import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { BackToListButton } from "./components/BackToListButton";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { EcgImagePanel } from "./components/EcgImagePanel";
import { ExaminationInfoCard } from "./components/ExaminationInfoCard";
import { InferenceResultPanel } from "./components/InferenceResultPanel";
import { PatientInfoCard } from "./components/PatientInfoCard";
import "./diagnosis-viewer.css";
import { apiFetch } from "../../lib/auth";
import { useDiagnosisDetail } from "./hooks/useDiagnosisDetail";
import { useEcgImage } from "./hooks/useEcgImage";
import { useInference } from "./hooks/useInference";
import type { InferenceDetail } from "./types";

export const DiagnosisViewerPage = () => {
	const { id } = useParams();
	const examinationId = id ?? "";
	const queryClient = useQueryClient();
	const { data, isLoading, isError, error, refetch } =
		useDiagnosisDetail(examinationId);
	const [ecgImageKey, setEcgImageKey] = useState(0);
	const {
		imageUrl,
		isLoading: isImageLoading,
		error: imageError,
	} = useEcgImage(examinationId, ecgImageKey);
	const [dialogOpen, setDialogOpen] = useState(false);

	const exportWaveMutation = useMutation({
		mutationFn: async () => {
			const response = await apiFetch(
				`/api/examinations/${examinationId}/export-wave-csv`,
				{ method: "POST" },
			);
			if (!response.ok) {
				const body = (await response.json().catch(() => ({}))) as {
					detail?: string | { msg?: string }[];
				};
				const d = body.detail;
				const msg =
					typeof d === "string"
						? d
						: Array.isArray(d)
							? d.map((x) => (typeof x === "object" ? x.msg : x)).join(", ")
							: "波形 CSV の出力に失敗しました";
				throw new Error(msg);
			}
			return response.json() as Promise<{ csv_file_path: string }>;
		},
		onSuccess: async () => {
			await queryClient.invalidateQueries({
				queryKey: ["examination", examinationId],
			});
			setEcgImageKey((k) => k + 1);
		},
	});

	const initialInference: InferenceDetail | null = useMemo(
		() => data?.inference ?? null,
		[data?.inference],
	);

	const {
		status,
		result,
		isRunning,
		runInference,
		isSubmitting,
		error: inferenceError,
	} = useInference(examinationId, initialInference);

	useEffect(() => {
		if (status === "完了") {
			refetch();
		}
	}, [status, refetch]);

	if (isLoading) {
		return <div className="state loading">読み込み中...</div>;
	}

	if (isError) {
		return <div className="state error">{(error as Error).message}</div>;
	}

	if (!data) {
		return <div className="state empty">診察データが見つかりません</div>;
	}

	return (
		<div className="viewer-page">
			<header className="viewer-header">
				<BackToListButton />
				<h1>診察詳細</h1>
			</header>
			<PatientInfoCard patient={data.patient} />
			<ExaminationInfoCard
				examination={data}
				onExportWaveCsv={() => exportWaveMutation.mutate()}
				isExportingWave={exportWaveMutation.isPending}
				exportWaveError={
					exportWaveMutation.error
						? (exportWaveMutation.error as Error).message
						: null
				}
			/>
			<InferenceResultPanel
				status={status}
				inference={data.inference}
				liveResult={result}
				onRun={() => setDialogOpen(true)}
				isRunning={isRunning}
				isSubmitting={isSubmitting}
			/>
			{inferenceError && (
				<div className="state error">{(inferenceError as Error).message}</div>
			)}
			<EcgImagePanel
				imageUrl={imageUrl}
				isLoading={isImageLoading}
				error={imageError}
			/>
			<ConfirmDialog
				open={dialogOpen}
				title="推論を実行しますか？"
				description="推論実行中は画面を閉じずにお待ちください。"
				onCancel={() => setDialogOpen(false)}
				onConfirm={async () => {
					setDialogOpen(false);
					await runInference();
				}}
			/>
		</div>
	);
};
