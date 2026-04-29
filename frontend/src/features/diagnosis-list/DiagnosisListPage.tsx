import {
	useCallback,
	useEffect,
	useLayoutEffect,
	useMemo,
	useState,
} from "react";
import { useSearchParams } from "react-router-dom";
import { formatDateTimeJa } from "../../lib/datetime";
import { DiagnosisDetailPanel } from "./components/DiagnosisDetailPanel";
import { DiagnosisTable } from "./components/DiagnosisTable";
import { EmptyState } from "./components/EmptyState";
import { ErrorState } from "./components/ErrorState";
import { FilterPanel } from "./components/FilterPanel";
import { ListPagination } from "./components/ListPagination";
import "./diagnosis-list.css";
import { useDiagnosisFilters } from "./hooks/useDiagnosisFilters";
import { useDiagnosisList } from "./hooks/useDiagnosisList";
import { useExaminationsSse } from "./hooks/useExaminationsSse";
import { useSortQueryParams } from "./hooks/useSortQueryParams";

export const DiagnosisListPage = () => {
	useExaminationsSse();
	const [searchParams, setSearchParams] = useSearchParams();
	const detailParam = searchParams.get("detail")?.trim() ?? "";

	const [renderId, setRenderId] = useState<string | null>(null);
	const [panelOpen, setPanelOpen] = useState(false);

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

	const handlePatientFiltersCommitted = useCallback(() => {
		setOffset(0);
	}, [setOffset]);

	const {
		patientIdInput,
		patientNameInput,
		committedPatientId,
		committedPatientName,
		setPatientIdInput,
		setPatientNameInput,
		commitPatientFilters,
	} = useDiagnosisFilters(handlePatientFiltersCommitted);

	const { data, isLoading, isError, error, isFetching, dataUpdatedAt } =
		useDiagnosisList({
			examDate,
			sortBy,
			sortOrder,
			patientId: committedPatientId,
			patientName: committedPatientName,
			limit,
			offset,
		});

	useLayoutEffect(() => {
		if (detailParam) {
			setRenderId(detailParam);
		}
	}, [detailParam]);

	useEffect(() => {
		if (renderId && detailParam === renderId) {
			const id = requestAnimationFrame(() => {
				requestAnimationFrame(() => setPanelOpen(true));
			});
			return () => cancelAnimationFrame(id);
		}
	}, [renderId, detailParam]);

	useEffect(() => {
		if (!detailParam && renderId && panelOpen) {
			setPanelOpen(false);
		}
	}, [detailParam, renderId, panelOpen]);

	const openDetail = useCallback(
		(id: string) => {
			const next = new URLSearchParams(searchParams);
			next.set("detail", id);
			setSearchParams(next);
		},
		[searchParams, setSearchParams],
	);

	const requestClosePanel = useCallback(() => setPanelOpen(false), []);

	const onPanelClosed = useCallback(() => {
		setRenderId(null);
		setSearchParams(
			(prev) => {
				const next = new URLSearchParams(prev);
				if (!next.get("detail")) {
					return prev;
				}
				next.delete("detail");
				return next;
			},
			{ replace: true },
		);
	}, [setSearchParams]);

	const items = data?.items ?? [];
	const total = data?.total ?? 0;

	const recordCountLabel = useMemo(() => {
		if (total === 0) {
			return "該当 0 件";
		}
		const from = offset + 1;
		const to = Math.min(offset + items.length, total);
		return `${from}〜${to} 件を表示 / 合計 ${total} 件`;
	}, [items.length, offset, total]);

	if (isLoading) {
		return <div className="state loading">読み込み中...</div>;
	}

	if (isError) {
		return <ErrorState message={(error as Error).message} />;
	}

	return (
		<div className="diagnosis-page">
			<header className="diagnosis-list-header">
				<FilterPanel
					examDate={examDate}
					patientId={patientIdInput}
					patientName={patientNameInput}
					onExamDateChange={setExamDate}
					onExamDateToday={() =>
						setExamDate(new Date().toISOString().slice(0, 10))
					}
					onExamDateAll={() => setExamDate("")}
					onPatientIdChange={setPatientIdInput}
					onPatientNameChange={setPatientNameInput}
					onPatientFiltersCommit={commitPatientFilters}
				/>
			</header>

			<main className="diagnosis-list-body">
				{items.length === 0 ? (
					<EmptyState message="該当する診察データがありません" />
				) : (
					<div className="diagnosis-table-wrap">
						<DiagnosisTable
							data={items}
							sortBy={sortBy}
							sortOrder={sortOrder}
							onSort={setSort}
							onOpenDetail={openDetail}
						/>
					</div>
				)}
			</main>

			<footer className="diagnosis-list-footer">
				<div className="diagnosis-list-footer__left">
					<span className="record-count">{recordCountLabel}</span>
					{dataUpdatedAt ? (
						<span className="last-updated-inline">
							最終更新:{" "}
							{formatDateTimeJa(new Date(dataUpdatedAt).toISOString())}
						</span>
					) : null}
				</div>
				<div className="diagnosis-list-footer__right">
					<ListPagination
						total={total}
						limit={limit}
						offset={offset}
						isBusy={isFetching}
						onOffsetChange={setOffset}
					/>
				</div>
			</footer>

			<DiagnosisDetailPanel
				renderId={renderId}
				panelOpen={panelOpen}
				onRequestClose={requestClosePanel}
				onPanelClosed={onPanelClosed}
			/>
		</div>
	);
};
