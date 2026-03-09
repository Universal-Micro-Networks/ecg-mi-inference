type Props = {
	message: string;
};

export const ErrorState = ({ message }: Props) => (
	<div className="state error">{message}</div>
);
