type Props = {
	message: string;
};

export const EmptyState = ({ message }: Props) => (
	<div className="state empty">{message}</div>
);
