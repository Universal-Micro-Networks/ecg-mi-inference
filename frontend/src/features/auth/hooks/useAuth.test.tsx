import { act, renderHook } from "@testing-library/react";

import { clearTokens, getAccessToken, setTokens } from "../../../lib/auth";
import { useAuth } from "./useAuth";

describe("useAuth", () => {
	afterEach(() => {
		clearTokens();
		vi.restoreAllMocks();
	});

	it("ログイン成功時に access/refresh token を保存する", async () => {
		vi.spyOn(global, "fetch").mockResolvedValueOnce(
			new Response(
				JSON.stringify({
					access_token: "new-access-token",
					refresh_token: "new-refresh-token",
					token_type: "bearer",
					expires_in: 3600,
				}),
				{ status: 200 },
			),
		);

		const { result } = renderHook(() => useAuth());

		await act(async () => {
			await result.current.login("valid-password");
		});

		expect(getAccessToken()).toBe("new-access-token");
		expect(result.current.isAuthenticated).toBe(true);
	});

	it("ログアウト時に token を削除する", async () => {
		vi.spyOn(global, "fetch").mockResolvedValueOnce(
			new Response("", { status: 200 }),
		);
		setTokens({
			accessToken: "existing-access",
			refreshToken: "existing-refresh",
		});

		const { result } = renderHook(() => useAuth());

		await act(async () => {
			await result.current.logout();
		});

		expect(getAccessToken()).toBeNull();
		expect(result.current.isAuthenticated).toBe(false);
	});
});
