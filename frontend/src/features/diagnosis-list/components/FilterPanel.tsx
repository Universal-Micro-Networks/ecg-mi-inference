type Props = {
	examDate: string;
	patientId: string;
	patientName: string;
	onExamDateChange: (value: string) => void;
	onPatientIdChange: (value: string) => void;
	onPatientNameChange: (value: string) => void;
	onClear: () => void;
	onRefresh: () => void;
	isRefreshing: boolean;
};

export const FilterPanel = ({
	examDate,
	patientId,
	patientName,
	onExamDateChange,
	onPatientIdChange,
	onPatientNameChange,
	onClear,
	onRefresh,
	isRefreshing,
}: Props) => (
	<section className="filter-panel">
		<label className="field">
			<span>検査日</span>
			<input
				type="date"
				value={examDate}
				onChange={(event) => onExamDateChange(event.target.value)}
			/>
		</label>
		<label className="field">
			<span>患者ID</span>
			<input
				type="text"
				value={patientId}
				onChange={(event) => onPatientIdChange(event.target.value)}
				placeholder="例: P-001"
			/>
		</label>
		<label className="field">
			<span>氏名</span>
			<input
				type="text"
				value={patientName}
				onChange={(event) => onPatientNameChange(event.target.value)}
				placeholder="例: 山田太郎"
			/>
		</label>
		<div className="filter-actions">
			<button type="button" onClick={onClear} className="secondary">
				クリア
			</button>
			<button type="button" onClick={onRefresh} disabled={isRefreshing}>
				{isRefreshing ? "更新中..." : "更新"}
			</button>
		</div>
	</section>
);
