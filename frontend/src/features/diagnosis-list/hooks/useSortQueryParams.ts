import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

const DEFAULT_PAGE_SIZE = 20;

const clampLimit = (n: number) =>
	Number.isFinite(n)
		? Math.min(500, Math.max(1, Math.floor(n)))
		: DEFAULT_PAGE_SIZE;

const clampOffset = (n: number) =>
	Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0;

export const useSortQueryParams = () => {
	const [searchParams, setSearchParams] = useSearchParams();

	const examDate = useMemo(() => {
		return searchParams.get("exam_date") ?? "";
	}, [searchParams]);

	const sortBy = searchParams.get("sort_by") ?? "exam_date";
	const sortOrder = searchParams.get("sort_order") ?? "desc";

	const limit = useMemo(() => {
		const raw = Number.parseInt(
			searchParams.get("limit") ?? String(DEFAULT_PAGE_SIZE),
			10,
		);
		return clampLimit(raw);
	}, [searchParams]);

	const offset = useMemo(() => {
		const raw = Number.parseInt(searchParams.get("offset") ?? "0", 10);
		return clampOffset(raw);
	}, [searchParams]);

	const setExamDate = (value: string) => {
		const next = new URLSearchParams(searchParams);
		if (!value) {
			next.delete("exam_date");
		} else {
			next.set("exam_date", value);
		}
		next.set("offset", "0");
		setSearchParams(next);
	};

	const setSort = (nextSortBy: string) => {
		const next = new URLSearchParams(searchParams);
		const currentSortBy = next.get("sort_by") ?? "exam_date";
		const currentSortOrder = next.get("sort_order") ?? "desc";

		const order =
			currentSortBy === nextSortBy && currentSortOrder === "desc"
				? "asc"
				: "desc";

		next.set("sort_by", nextSortBy);
		next.set("sort_order", order);
		next.set("offset", "0");
		setSearchParams(next);
	};

	const setOffset = useCallback(
		(value: number) => {
			const next = new URLSearchParams(searchParams);
			next.set("offset", String(clampOffset(value)));
			setSearchParams(next);
		},
		[searchParams, setSearchParams],
	);

	const setLimit = useCallback(
		(value: number) => {
			const next = new URLSearchParams(searchParams);
			next.set("limit", String(clampLimit(value)));
			next.set("offset", "0");
			setSearchParams(next);
		},
		[searchParams, setSearchParams],
	);

	return {
		examDate,
		sortBy,
		sortOrder,
		limit,
		offset,
		setExamDate,
		setSort,
		setOffset,
		setLimit,
	};
};
