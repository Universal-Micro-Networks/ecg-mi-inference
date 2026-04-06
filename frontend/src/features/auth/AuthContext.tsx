import { createContext, useContext } from "react";

export type AuthContextValue = {
	isAuthenticated: boolean;
	setAuthenticated: (value: boolean) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider = AuthContext.Provider;

export const useAuthContext = () => {
	const ctx = useContext(AuthContext);
	if (!ctx) {
		throw new Error("useAuthContext must be used within AuthProvider");
	}
	return ctx;
};
