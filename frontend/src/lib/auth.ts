export const AUTH_ACCESS_TOKEN_KEY = "auth_access_token";
export const AUTH_REFRESH_TOKEN_KEY = "auth_refresh_token";

export const getAccessToken = () =>
	localStorage.getItem(AUTH_ACCESS_TOKEN_KEY) ??
	localStorage.getItem("auth_token");

export const getRefreshToken = () =>
	localStorage.getItem(AUTH_REFRESH_TOKEN_KEY);

export const setTokens = (tokens: {
	accessToken: string;
	refreshToken?: string;
}) => {
	localStorage.setItem(AUTH_ACCESS_TOKEN_KEY, tokens.accessToken);
	if (tokens.refreshToken) {
		localStorage.setItem(AUTH_REFRESH_TOKEN_KEY, tokens.refreshToken);
	}
	// Backward compat (existing hooks)
	localStorage.setItem("auth_token", tokens.accessToken);
};

export const clearTokens = () => {
	localStorage.removeItem(AUTH_ACCESS_TOKEN_KEY);
	localStorage.removeItem(AUTH_REFRESH_TOKEN_KEY);
	localStorage.removeItem("auth_token");
};

const parseJwtPayload = (token: string): { exp?: number } | null => {
	const parts = token.split(".");
	if (parts.length < 2) {
		return null;
	}
	try {
		const payload = JSON.parse(atob(parts[1])) as { exp?: number };
		return payload;
	} catch {
		return null;
	}
};

const shouldRefreshSoon = (token: string, thresholdSeconds = 3600): boolean => {
	const payload = parseJwtPayload(token);
	if (!payload?.exp) {
		return false;
	}
	const now = Math.floor(Date.now() / 1000);
	return payload.exp - now <= thresholdSeconds;
};

export const refreshAccessToken = async (): Promise<string | null> => {
	const refreshToken = getRefreshToken();
	if (!refreshToken) {
		return null;
	}

	const response = await fetch("/api/auth/refresh", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ refresh_token: refreshToken }),
	});
	if (!response.ok) {
		clearTokens();
		return null;
	}
	const data = (await response.json()) as { access_token: string };
	setTokens({ accessToken: data.access_token });
	return data.access_token;
};

const buildHeaders = (
	headers: HeadersInit | undefined,
	token: string | null,
): Record<string, string> => {
	const base = new Headers(headers);
	if (!base.has("Content-Type")) {
		base.set("Content-Type", "application/json");
	}
	if (token) {
		base.set("Authorization", `Bearer ${token}`);
	}
	return Object.fromEntries(base.entries());
};

export const getAuthHeaders = (): Record<string, string> => {
	const token = getAccessToken();
	return buildHeaders(undefined, token);
};

export const apiFetch = async (
	input: RequestInfo | URL,
	init?: RequestInit,
): Promise<Response> => {
	const url = typeof input === "string" ? input : input.toString();
	const isAuthEndpoint = url.startsWith("/api/auth/");
	let token = getAccessToken();

	// Proactive refresh when token is close to expiry.
	if (!isAuthEndpoint && token && shouldRefreshSoon(token)) {
		token = await refreshAccessToken();
	}

	let response = await fetch(input, {
		...init,
		headers: buildHeaders(init?.headers, token),
	});

	// Retry once with refresh if access token is expired/invalid.
	if (!isAuthEndpoint && response.status === 401) {
		const refreshed = await refreshAccessToken();
		if (!refreshed) {
			return response;
		}
		response = await fetch(input, {
			...init,
			headers: buildHeaders(init?.headers, refreshed),
		});
	}

	return response;
};
