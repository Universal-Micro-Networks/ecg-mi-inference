import {
	type CSSProperties,
	type PointerEvent as ReactPointerEvent,
	useCallback,
	useEffect,
	useRef,
	useState,
} from "react";

import { apiFetch } from "../../../lib/auth";

/** バックエンド `ecg_service.STANDARD_12_LEAD_GRID` と同じ並び */
const ECG_LEAD_GRID: readonly (readonly string[])[] = [
	["I", "II"],
	["III", "aVR"],
	["aVL", "aVF"],
	["V1", "V2"],
	["V3", "V4"],
	["V5", "V6"],
];

/** 12 誘導画像クリック時に最初に表示する誘導 */
const DEFAULT_VIEWER_LEAD = "I";

const ZOOM_MIN = 0.5;
const ZOOM_MAX = 4;
const ZOOM_STEP = 0.25;

type Props = {
	examinationId: string;
	cacheKey: number;
	imageUrl: string | null;
	isLoading: boolean;
};

function buildEcgImagePath(
	examinationId: string,
	cacheKey: number,
	lead?: string,
): string {
	const params = new URLSearchParams();
	if (cacheKey) params.set("v", String(cacheKey));
	if (lead) params.set("lead", lead);
	const qs = params.toString();
	return `/api/examinations/${examinationId}/ecg-image${qs ? `?${qs}` : ""}`;
}

/**
 * 要件4: 一覧パネルは静的 12 誘導 PNG（パネル内パン・ズームなし）。
 * 画像クリックで全画面ビューアを開き、単誘導 PNG と誘導切替・モーダル内ズームを提供する。
 */
export const EcgImagePanel = ({
	examinationId,
	cacheKey,
	imageUrl,
	isLoading,
}: Props) => {
	const [viewerOpen, setViewerOpen] = useState(false);
	const [viewerLead, setViewerLead] = useState(DEFAULT_VIEWER_LEAD);
	const [zoom, setZoom] = useState(1);
	const [modalUrl, setModalUrl] = useState<string | null>(null);
	const [modalLoading, setModalLoading] = useState(false);
	const [stagePanning, setStagePanning] = useState(false);
	const stageRef = useRef<HTMLDivElement>(null);
	const panRef = useRef<{
		active: boolean;
		pointerId: number;
		lastX: number;
		lastY: number;
	}>({ active: false, pointerId: -1, lastX: 0, lastY: 0 });

	const openViewer = useCallback(() => {
		setViewerLead(DEFAULT_VIEWER_LEAD);
		setZoom(1);
		setViewerOpen(true);
	}, []);

	const closeViewer = useCallback(() => {
		setViewerOpen(false);
	}, []);

	const selectLead = useCallback((lead: string) => {
		setViewerLead(lead);
		setZoom(1);
	}, []);

	useEffect(() => {
		if (!viewerOpen || !viewerLead || !examinationId) {
			setModalUrl((prev) => {
				if (prev) URL.revokeObjectURL(prev);
				return null;
			});
			setModalLoading(false);
			return;
		}

		let createdUrl: string | null = null;
		const controller = new AbortController();
		setModalLoading(true);
		setModalUrl((prev) => {
			if (prev) URL.revokeObjectURL(prev);
			return null;
		});

		(async () => {
			try {
				const response = await apiFetch(
					buildEcgImagePath(examinationId, cacheKey, viewerLead),
					{ signal: controller.signal },
				);
				if (!response.ok) {
					return;
				}
				const blob = await response.blob();
				if (controller.signal.aborted) {
					return;
				}
				createdUrl = URL.createObjectURL(blob);
				setModalUrl(createdUrl);
			} catch (e) {
				if (e instanceof DOMException && e.name === "AbortError") {
					return;
				}
			} finally {
				if (!controller.signal.aborted) {
					setModalLoading(false);
				}
			}
		})();

		return () => {
			controller.abort();
			if (createdUrl) {
				URL.revokeObjectURL(createdUrl);
			}
		};
	}, [viewerOpen, viewerLead, examinationId, cacheKey]);

	useEffect(() => {
		if (!viewerOpen) return;
		const onKey = (e: KeyboardEvent) => {
			if (e.key === "Escape") closeViewer();
		};
		document.addEventListener("keydown", onKey);
		return () => document.removeEventListener("keydown", onKey);
	}, [viewerOpen, closeViewer]);

	const zoomIn = useCallback(() => {
		setZoom((z) => Math.min(ZOOM_MAX, Math.round((z + ZOOM_STEP) * 100) / 100));
	}, []);

	const zoomOut = useCallback(() => {
		setZoom((z) => Math.max(ZOOM_MIN, Math.round((z - ZOOM_STEP) * 100) / 100));
	}, []);

	const endStagePan = useCallback((e: ReactPointerEvent<HTMLDivElement>) => {
		const p = panRef.current;
		if (!p.active || p.pointerId !== e.pointerId) return;
		const pid = e.pointerId;
		p.active = false;
		p.pointerId = -1;
		const el = stageRef.current;
		if (el) {
			try {
				el.releasePointerCapture(pid);
			} catch {
				/* already released */
			}
		}
		setStagePanning(false);
	}, []);

	const onStagePointerDown = useCallback(
		(e: React.PointerEvent<HTMLDivElement>) => {
			if (!stageRef.current || modalLoading || !modalUrl) return;
			if (e.pointerType === "mouse" && e.button !== 0) return;
			panRef.current = {
				active: true,
				pointerId: e.pointerId,
				lastX: e.clientX,
				lastY: e.clientY,
			};
			try {
				stageRef.current.setPointerCapture(e.pointerId);
			} catch {
				return;
			}
			setStagePanning(true);
		},
		[modalLoading, modalUrl],
	);

	const onStagePointerMove = useCallback(
		(e: React.PointerEvent<HTMLDivElement>) => {
			const p = panRef.current;
			if (!p.active || p.pointerId !== e.pointerId) return;
			const el = stageRef.current;
			if (!el) return;
			const dx = e.clientX - p.lastX;
			const dy = e.clientY - p.lastY;
			p.lastX = e.clientX;
			p.lastY = e.clientY;
			el.scrollLeft -= dx;
			el.scrollTop -= dy;
		},
		[],
	);

	const onStageLostPointerCapture = useCallback(
		(e: React.PointerEvent<HTMLDivElement>) => {
			const p = panRef.current;
			if (p.pointerId === e.pointerId) {
				p.active = false;
				p.pointerId = -1;
				setStagePanning(false);
			}
		},
		[],
	);

	const stageClassName = [
		"ecg-viewer__stage",
		modalUrl && !modalLoading ? "ecg-viewer__stage--pannable" : "",
		stagePanning ? "ecg-viewer__stage--dragging" : "",
		zoom > 1 ? "ecg-viewer__stage--zoomed" : "",
	]
		.filter(Boolean)
		.join(" ");

	return (
		<section className="card ecg-image-card">
			{isLoading && (
				<div className="state loading ecg-image-card__loading">
					心電図を読み込み中…
				</div>
			)}
			{!isLoading && !imageUrl && (
				<div className="state empty">心電図データがありません</div>
			)}
			{!isLoading && imageUrl ? (
				<>
					<button
						type="button"
						className="ecg-image-zoom-trigger"
						onClick={openViewer}
						aria-label="12誘導を開いて単誘導を拡大表示"
					>
						<img
							src={imageUrl}
							alt="心電図波形（タップで拡大）"
							className="ecg-image"
						/>
					</button>
					<p className="ecg-image-zoom-hint">画像をタップして拡大表示</p>
				</>
			) : null}

			{viewerOpen ? (
				<div className="ecg-viewer-backdrop" role="presentation">
					<button
						type="button"
						className="ecg-viewer-backdrop__dismiss"
						onClick={closeViewer}
						aria-label="閉じる"
					/>
					<div
						className="ecg-viewer-shell"
						role="dialog"
						aria-modal="true"
						aria-label={`単誘導表示 誘導 ${viewerLead}`}
					>
						<div className="ecg-viewer__header">
							<span className="ecg-viewer__title">誘導 {viewerLead}</span>
							<button
								type="button"
								className="ecg-viewer__close"
								onClick={closeViewer}
							>
								閉じる
							</button>
						</div>

						<div
							ref={stageRef}
							className={stageClassName}
							onPointerDown={onStagePointerDown}
							onPointerMove={onStagePointerMove}
							onPointerUp={endStagePan}
							onPointerCancel={endStagePan}
							onLostPointerCapture={onStageLostPointerCapture}
						>
							{modalLoading && (
								<div className="state loading ecg-viewer__loading">
									読み込み中…
								</div>
							)}
							{!modalLoading && modalUrl ? (
								<div
									className="ecg-viewer__img-frame"
									style={
										{
											"--ecg-viewer-zoom": zoom,
										} as CSSProperties
									}
								>
									<img
										src={modalUrl}
										alt={`心電図 誘導 ${viewerLead}`}
										className="ecg-viewer__img"
										draggable={false}
									/>
								</div>
							) : null}
							{!modalLoading && !modalUrl ? (
								<div className="state empty ecg-viewer__error">
									画像を表示できませんでした
								</div>
							) : null}
						</div>

						<div className="ecg-viewer__footer">
							<p className="ecg-viewer__footer-label">誘導を切り替え</p>
							<fieldset
								className="ecg-viewer__lead-grid"
								aria-label="誘導の選択"
							>
								{ECG_LEAD_GRID.map((row) =>
									row.map((lead) => (
										<button
											key={lead}
											type="button"
											className={
												lead === viewerLead
													? "ecg-viewer__lead-btn ecg-viewer__lead-btn--active"
													: "ecg-viewer__lead-btn"
											}
											onClick={() => selectLead(lead)}
										>
											{lead}
										</button>
									)),
								)}
							</fieldset>
						</div>
					</div>

					<div
						className="ecg-viewer-zoom-fab"
						role="toolbar"
						aria-label="表示の拡大縮小"
					>
						<button
							type="button"
							className="ecg-viewer-zoom-fab__btn"
							onClick={zoomIn}
							disabled={zoom >= ZOOM_MAX}
							aria-label="拡大"
						>
							+
						</button>
						<button
							type="button"
							className="ecg-viewer-zoom-fab__btn"
							onClick={zoomOut}
							disabled={zoom <= ZOOM_MIN}
							aria-label="縮小"
						>
							−
						</button>
					</div>
				</div>
			) : null}
		</section>
	);
};
