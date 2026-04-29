import { useCallback, useEffect, useMemo, useState } from "react";

import {
	clearTokens,
	getAccessToken,
	getAuthHeaders,
	getRefreshToken,
	refreshAccessToken,
	setTokens,
} from "../../../lib/auth";

type LoginResponse = {
	access_token: string;
	refresh_token: string;
	token_type: string;
	expires_in: number;
};

type BootstrapStatusResponse = {
	requires_setup: boolean;
};

export const useAuth = () => {
	const [isAuthenticated, setAuthenticated] = useState(
		Boolean(getAccessToken()),
	);
	const [error, setError] = useState<string | null>(null);
	const [isLoading, setIsLoading] = useState(false);
	const [requiresSetup, setRequiresSetup] = useState(false);

	useEffect(() => {
		const bootstrap = async () => {
			try {
				const statusRes = await fetch("/api/auth/bootstrap-status");
				if (statusRes.ok) {
					const statusData =
						(await statusRes.json()) as BootstrapStatusResponse;
					setRequiresSetup(Boolean(statusData.requires_setup));
				}
			} catch {
				// noop
			}
			const access = getAccessToken();
			if (access) {
				setAuthenticated(true);
				return;
			}
			if (getRefreshToken()) {
				const refreshed = await refreshAccessToken();
				setAuthenticated(Boolean(refreshed));
				return;
			}
			setAuthenticated(false);
		};
		void bootstrap();
	}, []);

	const login = useCallback(async (password: string) => {
		setIsLoading(true);
		setError(null);
		try {
			const response = await fetch("/api/auth/login", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ password }),
			});

			if (response.status === 401) {
				clearTokens();
				setAuthenticated(false);
				setError("パスワードが正しくありません");
				return;
			}
			if (response.status === 403) {
				const body = (await response.json().catch(() => ({}))) as {
					detail?: string;
				};
				setRequiresSetup(true);
				setError(body.detail || "管理者パスワードが未設定です");
				return;
			}

			if (!response.ok) {
				throw new Error("ログインに失敗しました");
			}

			const data = (await response.json()) as LoginResponse;
			setTokens({
				accessToken: data.access_token,
				refreshToken: data.refresh_token,
			});
			setRequiresSetup(false);
			setAuthenticated(true);
		} finally {
			setIsLoading(false);
		}
	}, []);

	const bootstrapPassword = useCallback(async (newPassword: string) => {
		setIsLoading(true);
		setError(null);
		try {
			const response = await fetch("/api/auth/bootstrap", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ new_password: newPassword }),
			});
			if (response.status === 422 || response.status === 403) {
				const body = (await response.json().catch(() => ({}))) as {
					detail?: string;
				};
				setError(body.detail || "初期設定に失敗しました");
				return false;
			}
			if (!response.ok) {
				setError("初期設定に失敗しました");
				return false;
			}
			setRequiresSetup(false);
			return true;
		} finally {
			setIsLoading(false);
		}
	}, []);

	const logout = useCallback(async () => {
		setIsLoading(true);
		setError(null);
		try {
			await fetch("/api/auth/logout", {
				method: "POST",
				headers: getAuthHeaders(),
			});
		} catch {
			// Ignore network failures; always clear local tokens.
		} finally {
			clearTokens();
			setAuthenticated(false);
			setIsLoading(false);
		}
	}, []);

	const refreshToken = useCallback(async () => {
		const refreshed = await refreshAccessToken();
		setAuthenticated(Boolean(refreshed));
		if (!refreshed) {
			setError("セッションの有効期限が切れました。再度ログインしてください");
		}
	}, []);

	const value = useMemo(
		() => ({
			isAuthenticated,
			setAuthenticated,
		}),
		[isAuthenticated],
	);

	return {
		isAuthenticated,
		isLoading,
		requiresSetup,
		error,
		login,
		bootstrapPassword,
		logout,
		refreshToken,
		contextValue: value,
	};
};
