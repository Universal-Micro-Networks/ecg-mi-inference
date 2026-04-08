import {
	type ReactNode,
	useCallback,
	useEffect,
	useMemo,
	useState,
} from "react";
import type { InferenceDetail, InferenceStatusResponse } from "../types";

type Props = {
	open: boolean;
	onClose: () => void;
	examinationId: string;
	patientExternalId?: string;
	status: InferenceDetail["status"];
	inference?: InferenceDetail | null;
	liveResult?: InferenceStatusResponse | null;
	onRequestRun: () => void;
	isRunning: boolean;
	isSubmitting: boolean;
	error?: string | null;
};

const CopyIcon = () => (
	<svg
		className="judgment-modal__copy-icon"
		width="16"
		height="16"
		viewBox="0 0 24 24"
		aria-hidden
	>
		<title>コピー</title>
		<rect
			x="9"
			y="9"
			width="13"
			height="13"
			rx="2"
			fill="none"
			stroke="currentColor"
			strokeWidth="2"
		/>
		<path
			d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
			fill="none"
			stroke="currentColor"
			strokeWidth="2"
		/>
	</svg>
);

const WarningIcon = () => (
	<svg
		className="judgment-modal__hero-icon-svg"
		viewBox="0 0 24 24"
		width="36"
		height="36"
		aria-hidden
	>
		<title>注意</title>
		<path
			fill="currentColor"
			d="M12 2L2 20h20L12 2zm0 3.2L17.5 18h-11L12 5.2zM11 9h2v6h-2V9zm0 8h2v2h-2v-2z"
		/>
	</svg>
);

const SuccessIcon = () => (
	<svg
		className="judgment-modal__hero-icon-svg judgment-modal__hero-icon-svg--success"
		viewBox="0 0 24 24"
		width="40"
		height="40"
		aria-hidden
	>
		<title>完了</title>
		<path
			fill="currentColor"
			d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm-1 14l-4-4 1.4-1.4L11 12.2l5.6-5.6L18 8l-7 8z"
		/>
	</svg>
);

function buildClipboardText(
	examinationId: string,
	patientExternalId: string | undefined,
	merged: Record<string, unknown>,
): string {
	const lines = [
		`診察ID: ${examinationId}`,
		`患者ID: ${patientExternalId ?? "-"}`,
		`ステータス: ${merged.status ?? "-"}`,
		`リスクスコア: ${merged.risk_score != null ? `${merged.risk_score}%` : "-"}`,
		`リスクレベル: ${merged.risk_level ?? "-"}`,
		`推論実行日時: ${merged.executed_at ?? "-"}`,
	];
	return lines.join("\n");
}

export const JudgmentModal = ({
	open,
	onClose,
	examinationId,
	patientExternalId,
	status,
	inference,
	liveResult,
	onRequestRun,
	isRunning,
	isSubmitting,
	error,
}: Props) => {
	const merged = useMemo(
		() => ({
			...inference,
			...liveResult,
		}),
		[inference, liveResult],
	);

	const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

	const isComplete = status === "完了";
	const riskLevel = merged.risk_level;
	const isPositive = isComplete && (riskLevel === "高" || riskLevel === "中");
	const isNegative = isComplete && riskLevel === "低";

	const clipboardText = useMemo(
		() =>
			buildClipboardText(
				examinationId,
				patientExternalId,
				merged as Record<string, unknown>,
			),
		[examinationId, patientExternalId, merged],
	);

	const copyToClipboard = useCallback(async () => {
		try {
			await navigator.clipboard.writeText(clipboardText);
			setCopyFeedback("コピーしました");
			window.setTimeout(() => setCopyFeedback(null), 2000);
		} catch {
			setCopyFeedback("コピーに失敗しました");
			window.setTimeout(() => setCopyFeedback(null), 2500);
		}
	}, [clipboardText]);

	useEffect(() => {
		if (!open) {
			setCopyFeedback(null);
		}
	}, [open]);

	useEffect(() => {
		if (!open) {
			return;
		}
		const onKeyDown = (e: KeyboardEvent) => {
			if (e.key === "Escape") {
				e.preventDefault();
				onClose();
			}
		};
		window.addEventListener("keydown", onKeyDown);
		return () => window.removeEventListener("keydown", onKeyDown);
	}, [open, onClose]);

	if (!open) {
		return null;
	}

	const mainTitleId = "judgment-modal-title";
	let hero: ReactNode;
	let bodyText: ReactNode;

	if (error) {
		hero = (
			<div
				className="judgment-modal__icon-circle judgment-modal__icon-circle--error"
				aria-hidden
			>
				<WarningIcon />
			</div>
		);
		bodyText = (
			<>
				<h2 id={mainTitleId} className="judgment-modal__title">
					エラー
				</h2>
				<p className="judgment-modal__description">{error}</p>
			</>
		);
	} else if (isRunning || isSubmitting) {
		hero = <div className="judgment-modal__spinner" aria-hidden />;
		bodyText = (
			<>
				<h2 id={mainTitleId} className="judgment-modal__title">
					推論実行中
				</h2>
				<p className="judgment-modal__description">
					推論を実行しています。しばらくお待ちください。
				</p>
			</>
		);
	} else if (!isComplete) {
		hero = null;
		bodyText = (
			<>
				<h2 id={mainTitleId} className="judgment-modal__title">
					判定
				</h2>
				<p className="judgment-modal__description">
					推論を実行すると、リスクの有無を表示します。
				</p>
			</>
		);
	} else if (isPositive) {
		hero = (
			<div
				className="judgment-modal__icon-circle judgment-modal__icon-circle--warning"
				aria-hidden
			>
				<WarningIcon />
			</div>
		);
		bodyText = (
			<>
				<h2 id={mainTitleId} className="judgment-modal__title">
					リスクあり（陽性）
				</h2>
				<p className="judgment-modal__description">
					心不全のリスクが検出されました。医師による確認をお願いします。
				</p>
			</>
		);
	} else if (isNegative) {
		hero = (
			<div
				className="judgment-modal__icon-circle judgment-modal__icon-circle--success"
				aria-hidden
			>
				<SuccessIcon />
			</div>
		);
		bodyText = (
			<>
				<h2 id={mainTitleId} className="judgment-modal__title">
					リスク低（陰性）
				</h2>
				<p className="judgment-modal__description">
					目立ったリスクは検出されませんでした。結果は参考情報です。
				</p>
			</>
		);
	} else {
		hero = null;
		bodyText = (
			<>
				<h2 id={mainTitleId} className="judgment-modal__title">
					判定結果
				</h2>
				<p className="judgment-modal__description">
					リスクスコア {merged.risk_score ?? "-"}%／リスクレベル{" "}
					{merged.risk_level ?? "-"}
				</p>
				{merged.executed_at ? (
					<p className="judgment-modal__meta">実行日時: {merged.executed_at}</p>
				) : null}
			</>
		);
	}

	return (
		<div className="judgment-modal-backdrop" data-prevent-panel-escape="true">
			<button
				type="button"
				className="judgment-modal-backdrop__dismiss"
				onClick={onClose}
				aria-label="閉じる"
			/>
			<div
				className="judgment-modal judgment-modal--v2"
				role="dialog"
				aria-modal="true"
				aria-labelledby={mainTitleId}
			>
				<div className="judgment-modal__main">
					{hero}
					<div className="judgment-modal__main-text">{bodyText}</div>
					{copyFeedback ? (
						<p className="judgment-modal__copy-feedback" role="status">
							{copyFeedback}
						</p>
					) : null}
				</div>
				<div className="judgment-modal__footer">
					<div className="judgment-modal__footer-actions">
						{isComplete && !error ? (
							<button
								type="button"
								className="judgment-modal__btn judgment-modal__btn--secondary"
								onClick={() => void copyToClipboard()}
							>
								<CopyIcon />
								判定結果をクリップボードにコピー
							</button>
						) : null}
						{!isComplete && !isRunning && !isSubmitting && !error ? (
							<button
								type="button"
								className="judgment-modal__btn judgment-modal__btn--secondary"
								onClick={onRequestRun}
								disabled={isSubmitting}
							>
								推論を実行
							</button>
						) : null}
						<button
							type="button"
							className="judgment-modal__btn judgment-modal__btn--primary"
							onClick={onClose}
							disabled={isSubmitting}
						>
							閉じる
						</button>
					</div>
				</div>
			</div>
		</div>
	);
};
