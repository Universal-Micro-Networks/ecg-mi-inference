import type { FormEvent } from "react";
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { getAccessToken } from "../../../lib/auth";
import { useAuth } from "../hooks/useAuth";
import { PasswordStrengthIndicator } from "./PasswordStrengthIndicator";
import "../auth.css";

const getStrength = (value: string): "weak" | "medium" | "strong" => {
	if (!value) return "weak";
	const hasUpper = /[A-Z]/.test(value);
	const hasLower = /[a-z]/.test(value);
	const hasDigit = /\d/.test(value);
	const hasSymbol = /[^A-Za-z0-9]/.test(value);
	const kinds = [hasUpper, hasLower, hasDigit, hasSymbol].filter(
		Boolean,
	).length;
	if (value.length >= 12 && kinds >= 3) return "strong";
	if (value.length >= 8 && kinds >= 2) return "medium";
	return "weak";
};

export const LoginPage = () => {
	const navigate = useNavigate();
	const { isAuthenticated, isLoading, error, login } = useAuth();
	const [password, setPassword] = useState("");
	const [showPassword, setShowPassword] = useState(false);
	const passwordInputId = "login-password";

	if (isAuthenticated || getAccessToken()) {
		return <Navigate to="/diagnoses" replace />;
	}

	const onSubmit = async (e: FormEvent) => {
		e.preventDefault();
		await login(password);
		if (getAccessToken()) {
			navigate("/diagnoses", { replace: true });
		} else {
			setPassword("");
		}
	};

	return (
		<div className="auth-login-page">
			<h1 className="auth-login-title">ログイン</h1>
			<form onSubmit={onSubmit}>
				<label htmlFor={passwordInputId} className="auth-login-label">
					パスワード
				</label>
				<div className="auth-login-input-row">
					<input
						id={passwordInputId}
						type={showPassword ? "text" : "password"}
						value={password}
						onChange={(e) => setPassword(e.target.value)}
						className="auth-login-input"
						aria-label="パスワード"
					/>
					<button
						type="button"
						onClick={() => setShowPassword((v) => !v)}
						className="auth-login-toggle"
					>
						{showPassword ? "隠す" : "表示"}
					</button>
				</div>
				<PasswordStrengthIndicator strength={getStrength(password)} />

				{error ? <div className="auth-login-error">{error}</div> : null}

				<button
					type="submit"
					disabled={!password || isLoading}
					className="auth-login-submit"
				>
					{isLoading ? "ログイン中..." : "ログイン"}
				</button>
			</form>
		</div>
	);
};
