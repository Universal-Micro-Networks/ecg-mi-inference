import { Link } from "react-router-dom";

export const BackToListButton = () => (
	<Link className="back-link" to="/diagnoses">
		← 診察一覧に戻る
	</Link>
);
