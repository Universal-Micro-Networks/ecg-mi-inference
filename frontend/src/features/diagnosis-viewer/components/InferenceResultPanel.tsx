import type { InferenceDetail, InferenceStatusResponse } from "../types";

type Props = {
	status: InferenceDetail["status"];
	inference?: InferenceDetail | null;
	liveResult?: InferenceStatusResponse | null;
	onRun: () => void;
	isRunning: boolean;
	isSubmitting: boolean;
};

const badgeClass = (level?: string) => {
	switch (level) {
		case "高":
			return "badge high";
		case "中":
			return "badge medium";
		case "低":
			return "badge low";
		default:
			return "badge";
	}
};

export const InferenceResultPanel = ({
	status,
	inference,
	liveResult,
	onRun,
	isRunning,
	isSubmitting,
}: Props) => {
	const merged = {
		...inference,
		...liveResult,
	};

	return (
		<section className="card">
			<div className="card-header">
				<h2>推論結果</h2>
				{status !== "完了" && (
					<button
						type="button"
						onClick={onRun}
						disabled={isRunning || isSubmitting}
					>
						{isSubmitting ? "実行中..." : "推論実行"}
					</button>
				)}
			</div>
			<div className="status-row">
				<span>ステータス</span>
				<strong>{status}</strong>
			</div>
			{status === "完了" && (
				<div className="result-grid">
					<div>
						<span className="label">リスクスコア</span>
						<span>{merged.risk_score ?? "-"}%</span>
					</div>
					<div>
						<span className="label">リスクレベル</span>
						<span className={badgeClass(merged.risk_level)}>
							{merged.risk_level ?? "-"}
						</span>
					</div>
					<div>
						<span className="label">推論実行日時</span>
						<span>{merged.executed_at ?? "-"}</span>
					</div>
				</div>
			)}
			{isRunning && <div className="progress">推論中...</div>}
		</section>
	);
};
