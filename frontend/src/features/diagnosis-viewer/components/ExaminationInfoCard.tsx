import { formatDateTimeJa } from "../../../lib/datetime";
import type { ExaminationDetail } from "../types";

type Props = {
	examination: ExaminationDetail;
	onExportWaveCsv?: () => void;
	isExportingWave?: boolean;
	exportWaveError?: string | null;
	/** 折りたたみ可能にし、初期は閉じる（詳細パネル用） */
	collapsible?: boolean;
};

type BodyProps = Omit<Props, "collapsible">;

const ExaminationInfoBody = ({
	examination,
	onExportWaveCsv,
	isExportingWave,
	exportWaveError,
}: BodyProps) => (
	<>
		{onExportWaveCsv ? (
			<div className="card-header card-header--end examination-info-header">
				<button
					type="button"
					className="secondary"
					onClick={onExportWaveCsv}
					disabled={isExportingWave}
				>
					{isExportingWave ? "出力中..." : "MFERから波形CSVを出力"}
				</button>
			</div>
		) : null}
		<div className="card-grid">
			<div>
				<span className="label">検査日時</span>
				<span>{formatDateTimeJa(examination.exam_date)}</span>
			</div>
			<div>
				<span className="label">登録日時</span>
				<span>
					{examination.created_at
						? formatDateTimeJa(examination.created_at)
						: "—"}
				</span>
			</div>
			<div>
				<span className="label">診察ID</span>
				<span>{examination.id}</span>
			</div>
			<div className="card-grid-full">
				<span className="label">MFER ファイル</span>
				<span className="path-line">{examination.mfer_file_path ?? "—"}</span>
			</div>
			<div className="card-grid-full">
				<span className="label">波形データ（CSV パス）</span>
				<span className="path-line">{examination.csv_file_path ?? "—"}</span>
			</div>
		</div>
		{exportWaveError ? (
			<div className="state error inline-error">{exportWaveError}</div>
		) : null}
	</>
);

export const ExaminationInfoCard = (props: Props) => {
	const { collapsible, ...bodyProps } = props;

	if (collapsible) {
		return (
			<details className="card examination-info-details">
				<summary className="examination-info-summary">
					<span className="examination-info-summary__label">詳細</span>
				</summary>
				<div className="examination-info-details__body">
					<ExaminationInfoBody {...bodyProps} />
				</div>
			</details>
		);
	}

	return (
		<section className="card">
			<ExaminationInfoBody {...bodyProps} />
		</section>
	);
};
