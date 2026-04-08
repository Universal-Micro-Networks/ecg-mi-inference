import type { KeyboardEvent } from "react";

type Props = {
	examDate: string;
	patientId: string;
	patientName: string;
	onExamDateChange: (value: string) => void;
	onExamDateToday: () => void;
	onExamDateAll: () => void;
	onPatientIdChange: (value: string) => void;
	onPatientNameChange: (value: string) => void;
	onPatientFiltersCommit: () => void;
};

export const FilterPanel = ({
	examDate,
	patientId,
	patientName,
	onExamDateChange,
	onExamDateToday,
	onExamDateAll,
	onPatientIdChange,
	onPatientNameChange,
	onPatientFiltersCommit,
}: Props) => {
	const commitOnEnter = (e: KeyboardEvent<HTMLInputElement>) => {
		if (e.key !== "Enter" || e.nativeEvent.isComposing) return;
		e.preventDefault();
		onPatientFiltersCommit();
	};

	return (
		<section className="filter-panel">
			<div className="filter-panel__row">
				<label className="field field-exam-date">
					<span>検査日</span>
					<div className="exam-date-row">
						<input
							type="date"
							value={examDate}
							onChange={(event) => onExamDateChange(event.target.value)}
						/>
						<button
							type="button"
							className="secondary"
							onClick={onExamDateToday}
						>
							今日
						</button>
						<button type="button" className="secondary" onClick={onExamDateAll}>
							全期間
						</button>
					</div>
				</label>
				<label className="field field-compact">
					<span>患者ID</span>
					<input
						type="text"
						value={patientId}
						onChange={(event) => onPatientIdChange(event.target.value)}
						onKeyDown={commitOnEnter}
						placeholder="例: P-001"
						autoComplete="off"
					/>
				</label>
				<label className="field field-compact">
					<span>氏名</span>
					<input
						type="text"
						value={patientName}
						onChange={(event) => onPatientNameChange(event.target.value)}
						onKeyDown={commitOnEnter}
						placeholder="例: 山田太郎"
						autoComplete="off"
					/>
				</label>
			</div>
			<p className="field-hint">
				患者ID・氏名は入力後、Enter（Return）キーで検索します。
				未指定（全期間）のとき、取り込んだ検査も検査日に関係なく一覧に含まれます。
			</p>
		</section>
	);
};
