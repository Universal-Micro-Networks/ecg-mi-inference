import { Navigate, Route, Routes } from "react-router-dom";
import "./App.css";
import { LoginPage, ProtectedRoute } from "./features/auth";
import { DiagnosisListPage } from "./features/diagnosis-list";
import { DiagnosisLegacyRedirect } from "./features/diagnosis-viewer";

const App = () => (
	<Routes>
		<Route path="/" element={<Navigate to="/diagnoses" replace />} />
		<Route path="/login" element={<LoginPage />} />
		<Route
			path="/diagnoses"
			element={
				<ProtectedRoute>
					<DiagnosisListPage />
				</ProtectedRoute>
			}
		/>
		<Route
			path="/diagnoses/:id"
			element={
				<ProtectedRoute>
					<DiagnosisLegacyRedirect />
				</ProtectedRoute>
			}
		/>
	</Routes>
);

export default App;
