"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { api, setCsrf } from "@/lib/api";
import type { User } from "@/lib/types";
type Session = {
  user: User | null;
  loading: boolean;
  setUser: (user: User | null) => void;
};
const Context = createContext<Session>({
  user: null,
  loading: true,
  setUser: () => {},
});
export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setValue] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  function setUser(value: User | null) {
    setValue(value);
    setCsrf(value?.csrf_token || "");
  }
  useEffect(() => {
    const expired = () => setUser(null);
    window.addEventListener("careeros:unauthorized", expired);
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
    return () => window.removeEventListener("careeros:unauthorized", expired);
  }, []);
  return (
    <Context.Provider value={{ user, loading, setUser }}>
      {children}
    </Context.Provider>
  );
}
export const useSession = () => useContext(Context);
