import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api, getToken, setToken } from "./api";

interface AuthCtx {
  token: string | null;
  login: (u: string, p: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>({ token: null, login: async () => {}, logout: () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setT] = useState<string | null>(getToken());

  useEffect(() => {
    if (!token) return;
    api
      .listCases()
      .catch(() => {
        setToken(null);
        setT(null);
      });
  }, [token]);

  const login = async (u: string, p: string) => {
    const { token } = await api.login(u, p);
    setToken(token);
    setT(token);
  };
  const logout = () => {
    try {
      api.logout();
    } catch {
      /* ignore */
    }
    setToken(null);
    setT(null);
  };

  return <Ctx.Provider value={{ token, login, logout }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  return useContext(Ctx);
}
