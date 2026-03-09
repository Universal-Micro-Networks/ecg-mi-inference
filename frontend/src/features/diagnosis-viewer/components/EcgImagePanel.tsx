type Props = {
	imageUrl: string | null;
	isLoading: boolean;
	error?: string | null;
};

export const EcgImagePanel = ({ imageUrl, isLoading, error }: Props) => (
	<section className="card">
		<h2>心電図波形</h2>
		{isLoading && <div className="state loading">読み込み中...</div>}
		{error && <div className="state error">{error}</div>}
		{!isLoading && !error && !imageUrl && (
			<div className="state empty">心電図データがありません</div>
		)}
		{!isLoading && !error && imageUrl && (
			<img src={imageUrl} alt="心電図波形" className="ecg-image" />
		)}
	</section>
);
