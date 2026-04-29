import type { FormEvent } from "react";
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { getAccessToken } from "../../../lib/auth";
import { useAuth } from "../hooks/useAuth";
import { PasswordStrengthIndicator } from "./PasswordStrengthIndicator";
import "../auth.css";

const APP_DISPLAY_NAME = "心筋梗塞診断支援システム";

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
	const {
		isAuthenticated,
		isLoading,
		requiresSetup,
		error,
		login,
		bootstrapPassword,
	} = useAuth();
	const [password, setPassword] = useState("");
	const [confirmPassword, setConfirmPassword] = useState("");
	const [showPassword, setShowPassword] = useState(false);
	const [clientError, setClientError] = useState<string | null>(null);
	const passwordInputId = "login-password";
	const confirmPasswordInputId = "login-password-confirm";

	if (isAuthenticated || getAccessToken()) {
		return <Navigate to="/diagnoses" replace />;
	}

	const onSubmit = async (e: FormEvent) => {
		e.preventDefault();
		setClientError(null);
		if (requiresSetup) {
			const normalized = password.trim();
			if (normalized !== confirmPassword.trim()) {
				setClientError("確認用パスワードが一致しません");
				setPassword("");
				setConfirmPassword("");
				return;
			}
			const ok = await bootstrapPassword(normalized);
			if (!ok) {
				setPassword("");
				setConfirmPassword("");
				return;
			}
		}
		// 末尾改行やコピペ由来の空白で 401 になりやすいので正規化する
		await login(password.trim());
		if (getAccessToken()) {
			navigate("/diagnoses", { replace: true });
		} else {
			setPassword("");
			setConfirmPassword("");
		}
	};

	return (
		<div className="auth-login-page">
			<div className="auth-login-shell">
				<h1 className="auth-app-name">{APP_DISPLAY_NAME}</h1>
				<form onSubmit={onSubmit} aria-label="認証">
					{requiresSetup ? (
						<p className="auth-login-note">
							管理者パスワードが未設定です。初回パスワードを設定してください。
						</p>
					) : null}
					<label htmlFor={passwordInputId} className="auth-login-label">
						{requiresSetup ? "初回パスワード" : "パスワード"}
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
					{requiresSetup ? (
						<>
							<label
								htmlFor={confirmPasswordInputId}
								className="auth-login-label"
							>
								初回パスワード（確認）
							</label>
							<input
								id={confirmPasswordInputId}
								type={showPassword ? "text" : "password"}
								value={confirmPassword}
								onChange={(e) => setConfirmPassword(e.target.value)}
								className="auth-login-input"
								aria-label="初回パスワード確認"
							/>
						</>
					) : null}
					<PasswordStrengthIndicator strength={getStrength(password)} />

					{clientError || error ? (
						<div className="auth-login-error">{clientError || error}</div>
					) : null}

					<button
						type="submit"
						disabled={!password || isLoading}
						className="auth-login-submit"
					>
						{isLoading
							? requiresSetup
								? "設定中..."
								: "ログイン中..."
							: requiresSetup
								? "初回設定してログイン"
								: "ログイン"}
					</button>
				</form>
			</div>
		</div>
	);
};
