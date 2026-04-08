type Props = {
	open: boolean;
	title: string;
	description: string;
	onCancel: () => void;
	onConfirm: () => void;
};

export const ConfirmDialog = ({
	open,
	title,
	description,
	onCancel,
	onConfirm,
}: Props) => {
	if (!open) {
		return null;
	}

	return (
		<div
			className="dialog-backdrop"
			data-prevent-panel-escape="true"
			role="presentation"
		>
			<dialog className="dialog" aria-modal="true" open>
				<h3>{title}</h3>
				<p>{description}</p>
				<div className="dialog-actions">
					<button type="button" className="secondary" onClick={onCancel}>
						キャンセル
					</button>
					<button type="button" onClick={onConfirm}>
						実行
					</button>
				</div>
			</dialog>
		</div>
	);
};
