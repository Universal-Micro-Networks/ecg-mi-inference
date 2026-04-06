import type { ExaminationDetail } from "../types";

const formatDateTime = (value: string) => value;

type Props = {
	examination: ExaminationDetail;
	onExportWaveCsv?: () => void;
	isExportingWave?: boolean;
	exportWaveError?: string | null;
};

export const ExaminationInfoCard = ({
	examination,
	onExportWaveCsv,
	isExportingWave,
	exportWaveError,
}: Props) => (
	<section className="card">
		<div className="card-header examination-info-header">
			<h2>診察情報</h2>
			{onExportWaveCsv ? (
				<button
					type="button"
					className="secondary"
					onClick={onExportWaveCsv}
					disabled={isExportingWave}
				>
					{isExportingWave ? "出力中..." : "MFERから波形CSVを出力"}
				</button>
			) : null}
		</div>
		<div className="card-grid">
			<div>
				<span className="label">検査日時</span>
				<span>{formatDateTime(examination.exam_date)}</span>
			</div>
			<div>
				<span className="label">登録日時</span>
				<span>
					{examination.created_at
						? formatDateTime(examination.created_at)
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
	</section>
);
