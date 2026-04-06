import type { ExaminationDetail } from "../types";

const formatDateTime = (value: string) => value;

type Props = {
	examination: ExaminationDetail;
};

export const ExaminationInfoCard = ({ examination }: Props) => (
	<section className="card">
		<h2>診察情報</h2>
		<div className="card-grid">
			<div>
				<span className="label">検査日時</span>
				<span>{formatDateTime(examination.exam_date)}</span>
			</div>
			<div>
				<span className="label">登録日時</span>
				<span>{formatDateTime(examination.created_at)}</span>
			</div>
			<div>
				<span className="label">診察ID</span>
				<span>{examination.id}</span>
			</div>
		</div>
	</section>
);
