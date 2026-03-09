import { useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

const formatDate = (date: Date) => {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, "0");
	const day = String(date.getDate()).padStart(2, "0");
	return `${year}-${month}-${day}`;
};

export const useSortQueryParams = () => {
	const [searchParams, setSearchParams] = useSearchParams();

	const examDate = useMemo(() => {
		return searchParams.get("exam_date") ?? "";
	}, [searchParams]);

	const sortBy = searchParams.get("sort_by") ?? "exam_date";
	const sortOrder = searchParams.get("sort_order") ?? "desc";

	useEffect(() => {
		if (!examDate) {
			const next = new URLSearchParams(searchParams);
			next.set("exam_date", formatDate(new Date()));
			setSearchParams(next, { replace: true });
		}
	}, [examDate, searchParams, setSearchParams]);

	const setExamDate = (value: string) => {
		const next = new URLSearchParams(searchParams);
		next.set("exam_date", value);
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
		setSearchParams(next);
	};

	return {
		examDate: examDate || formatDate(new Date()),
		sortBy,
		sortOrder,
		setExamDate,
		setSort,
	};
};
