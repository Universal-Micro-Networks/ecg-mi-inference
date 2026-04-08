import { Navigate, useParams } from "react-router-dom";

/** 旧 URL `/diagnoses/:id` をクエリ付き一覧へリダイレクト */
export const DiagnosisLegacyRedirect = () => {
	const { id } = useParams();
	const q = id ? `?detail=${encodeURIComponent(id)}` : "";
	return <Navigate to={`/diagnoses${q}`} replace />;
};
