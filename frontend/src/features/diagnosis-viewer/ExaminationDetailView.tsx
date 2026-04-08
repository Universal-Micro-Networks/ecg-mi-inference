import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { EcgImagePanel } from "./components/EcgImagePanel";
import { ExaminationInfoCard } from "./components/ExaminationInfoCard";
import { JudgmentModal } from "./components/JudgmentModal";
import { PatientInfoCard } from "./components/PatientInfoCard";
import "./diagnosis-viewer.css";
import { apiFetch } from "../../lib/auth";
import { useDiagnosisDetail } from "./hooks/useDiagnosisDetail";
import { useEcgImage } from "./hooks/useEcgImage";
import { useInference } from "./hooks/useInference";
import type { InferenceDetail } from "./types";

type Props = {
	examinationId: string;
};

/** examinationId / キャッシュキーが変わるたびにフックをリセットし、読み込み中表示を一貫させる */
function ExaminationEcgSection({
	examinationId,
	cacheKey,
}: {
	examinationId: string;
	cacheKey: number;
}) {
	const { imageUrl, isLoading } = useEcgImage(examinationId, cacheKey);
	return (
		<EcgImagePanel
			examinationId={examinationId}
			cacheKey={cacheKey}
			imageUrl={imageUrl}
			isLoading={isLoading}
		/>
	);
}

export const ExaminationDetailView = ({ examinationId }: Props) => {
	const queryClient = useQueryClient();
	const { data, isLoading, isError, error, refetch } =
		useDiagnosisDetail(examinationId);
	const [ecgImageKey, setEcgImageKey] = useState(0);
	const [dialogOpen, setDialogOpen] = useState(false);
	const [judgmentModalOpen, setJudgmentModalOpen] = useState(false);

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
		<div className="viewer-page viewer-page--embedded viewer-page--with-judgment-fab">
			<PatientInfoCard patient={data.patient} />
			<ExaminationEcgSection
				key={`${examinationId}-${ecgImageKey}`}
				examinationId={examinationId}
				cacheKey={ecgImageKey}
			/>
			<ExaminationInfoCard
				collapsible
				examination={data}
				onExportWaveCsv={() => exportWaveMutation.mutate()}
				isExportingWave={exportWaveMutation.isPending}
				exportWaveError={
					exportWaveMutation.error
						? (exportWaveMutation.error as Error).message
						: null
				}
			/>
			<button
				type="button"
				className="judgment-fab"
				onClick={() => setJudgmentModalOpen(true)}
			>
				判定
			</button>
			<JudgmentModal
				open={judgmentModalOpen}
				onClose={() => setJudgmentModalOpen(false)}
				examinationId={examinationId}
				patientExternalId={data.patient.external_id}
				status={status}
				inference={data.inference}
				liveResult={result}
				onRequestRun={() => setDialogOpen(true)}
				isRunning={isRunning}
				isSubmitting={isSubmitting}
				error={
					inferenceError
						? String((inferenceError as Error).message || inferenceError)
						: null
				}
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
