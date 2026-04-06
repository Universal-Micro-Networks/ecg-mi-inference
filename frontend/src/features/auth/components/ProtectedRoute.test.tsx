import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { clearTokens, setTokens } from "../../../lib/auth";
import { ProtectedRoute } from "./ProtectedRoute";

describe("ProtectedRoute", () => {
	afterEach(() => {
		clearTokens();
	});

	it("未認証時は /login へリダイレクトする", () => {
		render(
			<MemoryRouter initialEntries={["/diagnoses"]}>
				<Routes>
					<Route
						path="/diagnoses"
						element={
							<ProtectedRoute>
								<div>secret page</div>
							</ProtectedRoute>
						}
					/>
					<Route path="/login" element={<div>login page</div>} />
				</Routes>
			</MemoryRouter>,
		);

		expect(screen.getByText("login page")).toBeTruthy();
	});

	it("認証済み時は子要素を表示する", () => {
		setTokens({ accessToken: "header.payload.signature" });

		render(
			<MemoryRouter initialEntries={["/diagnoses"]}>
				<Routes>
					<Route
						path="/diagnoses"
						element={
							<ProtectedRoute>
								<div>secret page</div>
							</ProtectedRoute>
						}
					/>
					<Route path="/login" element={<div>login page</div>} />
				</Routes>
			</MemoryRouter>,
		);

		expect(screen.getByText("secret page")).toBeTruthy();
	});
});
