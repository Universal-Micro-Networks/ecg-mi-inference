import { useCallback, useEffect, useRef } from "react";
import { ExaminationDetailView } from "../../diagnosis-viewer/ExaminationDetailView";
import "./DiagnosisDetailPanel.css";

type Props = {
	/** 表示中の診察 ID（閉じるアニメーション中も保持） */
	renderId: string | null;
	/** パネルが開ききっているか（false でスライドアウト） */
	panelOpen: boolean;
	onRequestClose: () => void;
	/** スライドアウト完了後に URL から detail を外すなど */
	onPanelClosed: () => void;
};

export const DiagnosisDetailPanel = ({
	renderId,
	panelOpen,
	onRequestClose,
	onPanelClosed,
}: Props) => {
	const asideRef = useRef<HTMLElement>(null);

	const handleTransitionEnd = useCallback(
		(event: React.TransitionEvent<HTMLElement>) => {
			if (event.target !== asideRef.current) {
				return;
			}
			if (event.propertyName !== "transform") {
				return;
			}
			if (!panelOpen) {
				onPanelClosed();
			}
		},
		[panelOpen, onPanelClosed],
	);

	useEffect(() => {
		const onKeyDown = (e: KeyboardEvent) => {
			if (e.key !== "Escape" || !renderId || !panelOpen) {
				return;
			}
			if (document.querySelector("[data-prevent-panel-escape]")) {
				return;
			}
			onRequestClose();
		};
		window.addEventListener("keydown", onKeyDown);
		return () => window.removeEventListener("keydown", onKeyDown);
	}, [renderId, panelOpen, onRequestClose]);

	useEffect(() => {
		if (!renderId) {
			return;
		}
		const prev = document.body.style.overflow;
		document.body.style.overflow = "hidden";
		return () => {
			document.body.style.overflow = prev;
		};
	}, [renderId]);

	if (!renderId) {
		return null;
	}

	return (
		<div className="diagnosis-detail-panel-root">
			<button
				type="button"
				className={`diagnosis-detail-backdrop${panelOpen ? " is-visible" : ""}`}
				aria-label="パネルを閉じる"
				onClick={onRequestClose}
			/>
			<aside
				ref={asideRef}
				className={`diagnosis-detail-panel${panelOpen ? " is-open" : ""}`}
				role="dialog"
				aria-modal="true"
				aria-label="診察詳細"
				onTransitionEnd={handleTransitionEnd}
			>
				<div className="diagnosis-detail-panel__scroll">
					<ExaminationDetailView key={renderId} examinationId={renderId} />
				</div>
			</aside>
		</div>
	);
};
