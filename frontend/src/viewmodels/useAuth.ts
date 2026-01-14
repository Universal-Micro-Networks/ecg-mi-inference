import { useState } from 'react';

interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
}

export const useAuth = () => {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    token: null,
  });

  const login = async (password: string): Promise<boolean> => {
    // TODO: 実装
    return false;
  };

  const logout = () => {
    setAuthState({
      isAuthenticated: false,
      token: null,
    });
  };

  return {
    ...authState,
    login,
    logout,
  };
};
