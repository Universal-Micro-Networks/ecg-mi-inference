import type { ReactNode } from "react";
import { useEffect, useRef } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { clearTokens, getAccessToken } from "../../../lib/auth";

const IDLE_TIMEOUT_MS = 8 * 60 * 60 * 1000; // 8 hours
const ACTIVITY_EVENTS: Array<keyof WindowEventMap> = [
	"mousemove",
	"mousedown",
	"keydown",
	"scroll",
	"touchstart",
	"click",
];

export const ProtectedRoute = ({ children }: { children: ReactNode }) => {
	const navigate = useNavigate();
	const timerRef = useRef<number | null>(null);
	const token = getAccessToken();

	useEffect(() => {
		if (!token) {
			return;
		}

		const logoutByIdle = () => {
			clearTokens();
			navigate("/login", { replace: true });
		};

		const resetTimer = () => {
			if (timerRef.current != null) {
				window.clearTimeout(timerRef.current);
			}
			timerRef.current = window.setTimeout(logoutByIdle, IDLE_TIMEOUT_MS);
		};

		resetTimer();
		for (const eventName of ACTIVITY_EVENTS) {
			window.addEventListener(eventName, resetTimer, { passive: true });
		}

		return () => {
			if (timerRef.current != null) {
				window.clearTimeout(timerRef.current);
				timerRef.current = null;
			}
			for (const eventName of ACTIVITY_EVENTS) {
				window.removeEventListener(eventName, resetTimer);
			}
		};
	}, [navigate, token]);

	if (!token) {
		return <Navigate to="/login" replace />;
	}
	return <>{children}</>;
};
