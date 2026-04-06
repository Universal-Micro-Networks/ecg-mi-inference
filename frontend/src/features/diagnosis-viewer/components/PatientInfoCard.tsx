import type { PatientDetail } from "../types";

type Props = {
	patient: PatientDetail;
};

export const PatientInfoCard = ({ patient }: Props) => (
	<section className="card">
		<h2>患者情報</h2>
		<div className="card-grid">
			<div>
				<span className="label">氏名</span>
				<span>{patient.name}</span>
			</div>
			<div>
				<span className="label">患者ID</span>
				<span>{patient.external_id}</span>
			</div>
			<div>
				<span className="label">性別</span>
				<span>{patient.gender}</span>
			</div>
			<div>
				<span className="label">生年月日</span>
				<span>{patient.birth_date}</span>
			</div>
		</div>
	</section>
);
