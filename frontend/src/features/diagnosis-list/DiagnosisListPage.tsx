import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { DiagnosisTable } from "./components/DiagnosisTable";
import { EmptyState } from "./components/EmptyState";
import { ErrorState } from "./components/ErrorState";
import { FilterPanel } from "./components/FilterPanel";
import "./diagnosis-list.css";
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

type HeadersRecord = Record<string, string>;

const getAuthHeader = (): HeadersRecord => {
	const token = localStorage.getItem("auth_token");
	const headers: HeadersRecord = {
		"Content-Type": "application/json",
	};
	if (token) {
		headers.Authorization = `Bearer ${token}`;
	}
	return headers;
};

export const DiagnosisListPage = () => {
	const { examDate, sortBy, sortOrder, setExamDate, setSort } =
		useSortQueryParams();
	const {
		data = [],
		isLoading,
		isError,
		error,
		refetch,
		isFetching,
		dataUpdatedAt,
	} = useDiagnosisList({ examDate, sortBy, sortOrder });
	const { selectedId, selectRow } = useRowSelection();
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [submitError, setSubmitError] = useState<string | null>(null);
	const {
		patientId,
		patientName,
		setPatientId,
		setPatientName,
		resetFilters,
		filtered,
	} = useDiagnosisFilters(data);

	const visibleRows = useMemo(() => filtered, [filtered]);

	const handleClear = () => {
		resetFilters();
		setExamDate(new Date().toISOString().slice(0, 10));
	};

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
			const response = await fetch("/api/inferences", {
				method: "POST",
				headers: getAuthHeader(),
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
			{visibleRows.length === 0 ? (
				<EmptyState message="該当する診察データがありません" />
			) : (
				<DiagnosisTable
					data={visibleRows}
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
