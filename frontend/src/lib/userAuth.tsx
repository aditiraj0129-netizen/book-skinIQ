import { createContext, useContext, useState, type ReactNode } from "react";
import { api } from "./api";
import type { AppUser } from "./types";

interface UserAuthState {
  user: AppUser | null;
  loading: boolean;
  login: (name: string, email?: string) => Promise<AppUser>;
  logout: () => void;
}

const UserAuthContext = createContext<UserAuthState | null>(null);
const STORAGE_KEY = "bright_studio_user";

export function UserAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  });
  const [loading, setLoading] = useState(false);

  async function login(name: string, email?: string) {
    setLoading(true);
    try {
      const result = await api.userLogin(name, email);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(result));
      setUser(result);
      return result;
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem(STORAGE_KEY);
    setUser(null);
  }

  return (
    <UserAuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </UserAuthContext.Provider>
  );
}

export function useUserAuth() {
  const ctx = useContext(UserAuthContext);
  if (!ctx) throw new Error("useUserAuth must be used within UserAuthProvider");
  return ctx;
}
