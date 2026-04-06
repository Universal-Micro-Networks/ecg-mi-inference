import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { getAccessToken } from "../../../lib/auth";

export const ProtectedRoute = ({ children }: { children: ReactNode }) => {
	if (!getAccessToken()) {
		return <Navigate to="/login" replace />;
	}
	return <>{children}</>;
};
