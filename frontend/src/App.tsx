import { Navigate, Route, Routes } from "react-router-dom";
import "./App.css";
import { DiagnosisListPage } from "./features/diagnosis-list";
import { DiagnosisViewerPage } from "./features/diagnosis-viewer";

const App = () => (
	<Routes>
		<Route path="/" element={<Navigate to="/diagnoses" replace />} />
		<Route path="/diagnoses" element={<DiagnosisListPage />} />
		<Route path="/diagnoses/:id" element={<DiagnosisViewerPage />} />
	</Routes>
);

export default App;
