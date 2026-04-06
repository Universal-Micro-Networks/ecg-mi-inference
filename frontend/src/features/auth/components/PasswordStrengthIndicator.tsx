type Strength = "weak" | "medium" | "strong";

const getLabel = (strength: Strength) => {
	if (strength === "strong") return "強い";
	if (strength === "medium") return "普通";
	return "弱い";
};

const getClassName = (strength: Strength) => {
	if (strength === "strong") return "auth-password-strength-strong";
	if (strength === "medium") return "auth-password-strength-medium";
	return "auth-password-strength-weak";
};

export const PasswordStrengthIndicator = ({
	strength,
}: { strength: Strength }) => (
	<div className={`auth-password-strength ${getClassName(strength)}`}>
		パスワード強度: {getLabel(strength)}
	</div>
);
