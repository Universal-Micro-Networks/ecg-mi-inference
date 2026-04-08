import { formatDateTimeJa } from "../../../lib/datetime";
import type { ExaminationSummary } from "../types";

type Props = {
	data: ExaminationSummary[];
	sortBy: string;
	sortOrder: string;
	onSort: (column: string) => void;
	onOpenDetail: (examinationId: string) => void;
};

const SortIndicator = ({
	active,
	order,
}: {
	active: boolean;
	order: string;
}) => {
	if (!active) {
		return null;
	}
	return <span className="sort-indicator">{order === "asc" ? "▲" : "▼"}</span>;
};

export const DiagnosisTable = ({
	data,
	sortBy,
	sortOrder,
	onSort,
	onOpenDetail,
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
					<button type="button" onClick={() => onSort("patient_name")}>
						氏名
						<SortIndicator
							active={sortBy === "patient_name"}
							order={sortOrder}
						/>
					</button>
				</th>
				<th>
					<button type="button" onClick={() => onSort("patient_id")}>
						患者ID
						<SortIndicator active={sortBy === "patient_id"} order={sortOrder} />
					</button>
				</th>
				<th>
					<button type="button" onClick={() => onSort("age")}>
						年齢
						<SortIndicator active={sortBy === "age"} order={sortOrder} />
					</button>
				</th>
				<th>
					<span>性別</span>
				</th>
			</tr>
		</thead>
		<tbody>
			{data.map((item) => {
				const rowLabel = `診察詳細: ${item.patient.name} ${formatDateTimeJa(
					item.exam_date,
				)}`;
				return (
					<tr key={item.id}>
						<td>
							<button
								type="button"
								className="diagnosis-row-link"
								aria-label={rowLabel}
								onClick={() => onOpenDetail(item.id)}
							>
								{formatDateTimeJa(item.exam_date)}
							</button>
						</td>
						<td>
							<button
								type="button"
								className="diagnosis-row-link"
								aria-label={rowLabel}
								onClick={() => onOpenDetail(item.id)}
							>
								{item.patient.name}
							</button>
						</td>
						<td>
							<button
								type="button"
								className="diagnosis-row-link"
								aria-label={rowLabel}
								onClick={() => onOpenDetail(item.id)}
							>
								{item.patient.external_id}
							</button>
						</td>
						<td>
							<button
								type="button"
								className="diagnosis-row-link"
								aria-label={rowLabel}
								onClick={() => onOpenDetail(item.id)}
							>
								{item.patient.age}
							</button>
						</td>
						<td>
							<button
								type="button"
								className="diagnosis-row-link"
								aria-label={rowLabel}
								onClick={() => onOpenDetail(item.id)}
							>
								{item.patient.gender}
							</button>
						</td>
					</tr>
				);
			})}
		</tbody>
	</table>
);
