import { useCallback, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { DiagnosisTable } from "./components/DiagnosisTable";
import { EmptyState } from "./components/EmptyState";
import { ErrorState } from "./components/ErrorState";
import { FilterPanel } from "./components/FilterPanel";
import "./diagnosis-list.css";
import { apiFetch } from "../../lib/auth";
import { useDiagnosisFilters } from "./hooks/useDiagnosisFilters";
import { useDiagnosisList } from "./hooks/useDiagnosisList";
import { useRowSelection } from "./hooks/useRowSelection";
import { useSortQueryParams } from "./hooks/useSortQueryParams";

const formatUpdatedAt = (timestamp?: number) => {
	if (!timestamp) {
		return "";
	}
	const date = new Date(timestamp);
	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(
		2,
		"0",
	)}-${String(date.getDate()).padStart(2, "0")} ${String(
		date.getHours(),
	).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
};

export const DiagnosisListPage = () => {
	const {
		examDate,
		sortBy,
		sortOrder,
		limit,
		offset,
		setExamDate,
		setSort,
		setOffset,
	} = useSortQueryParams();

	const handleFilterDebounced = useCallback(() => {
		setOffset(0);
	}, [setOffset]);

	const {
		patientId,
		patientName,
		debouncedPatientId,
		debouncedPatientName,
		setPatientId,
		setPatientName,
		resetFilters,
	} = useDiagnosisFilters(handleFilterDebounced);

	const {
		data,
		isLoading,
		isError,
		error,
		refetch,
		isFetching,
		dataUpdatedAt,
	} = useDiagnosisList({
		examDate,
		sortBy,
		sortOrder,
		patientId: debouncedPatientId,
		patientName: debouncedPatientName,
		limit,
		offset,
	});
	const { selectedId, selectRow } = useRowSelection();
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [submitError, setSubmitError] = useState<string | null>(null);

	const items = data?.items ?? [];
	const total = data?.total ?? 0;

	const rangeLabel = useMemo(() => {
		if (total === 0) {
			return "0 件";
		}
		const from = offset + 1;
		const to = Math.min(offset + items.length, total);
		return `${from}〜${to} 件 / 全 ${total} 件`;
	}, [items.length, offset, total]);

	const handleClear = () => {
		resetFilters();
		setExamDate(new Date().toISOString().slice(0, 10));
		setOffset(0);
	};

	const canPrev = offset > 0;
	const canNext = offset + items.length < total;

	if (isLoading) {
		return <div className="state loading">読み込み中...</div>;
	}

	if (isError) {
		return <ErrorState message={(error as Error).message} />;
	}

	const handleRunInference = async () => {
		if (!selectedId) {
			return;
		}
		try {
			setIsSubmitting(true);
			setSubmitError(null);
			const response = await apiFetch("/api/inferences", {
				method: "POST",
				body: JSON.stringify({ examination_id: selectedId }),
			});
			if (!response.ok) {
				throw new Error("推論実行に失敗しました");
			}
		} catch (submitError) {
			setSubmitError((submitError as Error).message);
		} finally {
			setIsSubmitting(false);
		}
	};

	return (
		<div className="diagnosis-page">
			<header>
				<h1>診察一覧</h1>
			</header>
			<FilterPanel
				examDate={examDate}
				patientId={patientId}
				patientName={patientName}
				onExamDateChange={setExamDate}
				onPatientIdChange={setPatientId}
				onPatientNameChange={setPatientName}
				onClear={handleClear}
				onRefresh={refetch}
				isRefreshing={isFetching}
			/>
			<div className="pagination-bar">
				<span className="pagination-range">{rangeLabel}</span>
				<div className="pagination-controls">
					<button
						type="button"
						className="secondary"
						disabled={!canPrev || isFetching}
						onClick={() => setOffset(Math.max(0, offset - limit))}
					>
						前へ
					</button>
					<button
						type="button"
						className="secondary"
						disabled={!canNext || isFetching}
						onClick={() => setOffset(offset + limit)}
					>
						次へ
					</button>
				</div>
			</div>
			{items.length === 0 ? (
				<EmptyState message="該当する診察データがありません" />
			) : (
				<DiagnosisTable
					data={items}
					selectedId={selectedId}
					sortBy={sortBy}
					sortOrder={sortOrder}
					onSort={setSort}
					onSelect={selectRow}
				/>
			)}
			{selectedId && (
				<div className="action-bar">
					<Link to={`/diagnoses/${selectedId}`}>診察詳細を開く</Link>
					<button
						type="button"
						onClick={handleRunInference}
						disabled={isSubmitting}
					>
						{isSubmitting ? "推論中..." : "推論実行"}
					</button>
				</div>
			)}
			{submitError && <ErrorState message={submitError} />}
			<footer className="last-updated">
				{dataUpdatedAt ? `最終更新: ${formatUpdatedAt(dataUpdatedAt)}` : ""}
			</footer>
		</div>
	);
};
