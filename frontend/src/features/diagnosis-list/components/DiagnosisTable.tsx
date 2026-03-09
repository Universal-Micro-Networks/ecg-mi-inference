import type { ExaminationSummary } from "../types";

type Props = {
	data: ExaminationSummary[];
	selectedId: string | null;
	sortBy: string;
	sortOrder: string;
	onSort: (column: string) => void;
	onSelect: (id: string) => void;
};

const SortIndicator = ({
	active,
	order,
}: { active: boolean; order: string }) => {
	if (!active) {
		return null;
	}
	return <span className="sort-indicator">{order === "asc" ? "▲" : "▼"}</span>;
};

export const DiagnosisTable = ({
	data,
	selectedId,
	sortBy,
	sortOrder,
	onSort,
	onSelect,
}: Props) => (
	<table className="diagnosis-table">
		<thead>
			<tr>
				<th>
					<button type="button" onClick={() => onSort("exam_date")}>
						検査日時
						<SortIndicator active={sortBy === "exam_date"} order={sortOrder} />
					</button>
				</th>
				<th>
					<button type="button" onClick={() => onSort("patient_id")}>
						患者ID
						<SortIndicator active={sortBy === "patient_id"} order={sortOrder} />
					</button>
				</th>
				<th>
					<button type="button" onClick={() => onSort("patient_name")}>
						氏名
						<SortIndicator
							active={sortBy === "patient_name"}
							order={sortOrder}
						/>
					</button>
				</th>
				<th>
					<span>性別</span>
				</th>
				<th>
					<button type="button" onClick={() => onSort("age")}>
						年齢
						<SortIndicator active={sortBy === "age"} order={sortOrder} />
					</button>
				</th>
			</tr>
		</thead>
		<tbody>
			{data.map((item) => (
				<tr
					key={item.id}
					className={item.id === selectedId ? "selected" : undefined}
				>
					<td>
						<button
							type="button"
							className="row-button"
							onClick={() => onSelect(item.id)}
						>
							{item.exam_date}
						</button>
					</td>
					<td>
						<button
							type="button"
							className="row-button"
							onClick={() => onSelect(item.id)}
						>
							{item.patient.external_id}
						</button>
					</td>
					<td>
						<button
							type="button"
							className="row-button"
							onClick={() => onSelect(item.id)}
						>
							{item.patient.name}
						</button>
					</td>
					<td>
						<button
							type="button"
							className="row-button"
							onClick={() => onSelect(item.id)}
						>
							{item.patient.gender}
						</button>
					</td>
					<td>
						<button
							type="button"
							className="row-button"
							onClick={() => onSelect(item.id)}
						>
							{item.patient.age}
						</button>
					</td>
				</tr>
			))}
		</tbody>
	</table>
);
