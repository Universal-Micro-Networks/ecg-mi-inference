type Props = {
	total: number;
	limit: number;
	offset: number;
	isBusy: boolean;
	onOffsetChange: (nextOffset: number) => void;
};

/** 現在ページ周辺・両端を含むページ番号列（ギャップは ellipsis） */
type PageItem =
	| { kind: "page"; page: number }
	| { kind: "ellipsis"; key: string };

function buildPageItems(currentPage: number, totalPages: number): PageItem[] {
	if (totalPages <= 1) {
		return totalPages === 1 ? [{ kind: "page", page: 1 }] : [];
	}
	if (totalPages <= 9) {
		return Array.from({ length: totalPages }, (_, i) => ({
			kind: "page",
			page: i + 1,
		}));
	}

	const set = new Set<number>();
	set.add(1);
	set.add(totalPages);
	for (let d = -2; d <= 2; d++) {
		const p = currentPage + d;
		if (p >= 1 && p <= totalPages) {
			set.add(p);
		}
	}
	const sorted = [...set].sort((a, b) => a - b);
	const out: PageItem[] = [];
	for (let i = 0; i < sorted.length; i++) {
		if (i > 0 && sorted[i] - sorted[i - 1] > 1) {
			out.push({
				kind: "ellipsis",
				key: `gap-${sorted[i - 1]}-${sorted[i]}`,
			});
		}
		out.push({ kind: "page", page: sorted[i] });
	}
	return out;
}

export const ListPagination = ({
	total,
	limit,
	offset,
	isBusy,
	onOffsetChange,
}: Props) => {
	const totalPages = total > 0 ? Math.ceil(total / limit) : 0;
	const currentPage =
		totalPages > 0 ? Math.min(totalPages, Math.floor(offset / limit) + 1) : 1;
	const canPrev = offset > 0 && total > 0;
	const canNext = total > 0 && offset + limit < total;
	const pageItems = buildPageItems(currentPage, totalPages);

	if (total === 0) {
		return (
			<nav className="list-pagination" aria-label="ページ送り">
				<button type="button" className="secondary" disabled>
					前へ
				</button>
				<button type="button" className="secondary" disabled>
					次へ
				</button>
			</nav>
		);
	}

	return (
		<nav className="list-pagination" aria-label="ページ送り">
			<button
				type="button"
				className="secondary"
				disabled={!canPrev || isBusy}
				onClick={() => onOffsetChange(Math.max(0, offset - limit))}
			>
				前へ
			</button>
			<ul className="list-pagination__pages">
				{pageItems.map((item) =>
					item.kind === "ellipsis" ? (
						<li
							key={item.key}
							className="list-pagination__ellipsis"
							aria-hidden
						>
							…
						</li>
					) : (
						<li key={item.page}>
							<button
								type="button"
								className={
									item.page === currentPage
										? "list-pagination__page is-active"
										: "list-pagination__page"
								}
								disabled={isBusy || item.page === currentPage}
								onClick={() => onOffsetChange((item.page - 1) * limit)}
								aria-current={item.page === currentPage ? "page" : undefined}
							>
								{item.page}
							</button>
						</li>
					),
				)}
			</ul>
			<button
				type="button"
				className="secondary"
				disabled={!canNext || isBusy}
				onClick={() => onOffsetChange(offset + limit)}
			>
				次へ
			</button>
		</nav>
	);
};
