import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";

import { api, setTokenGetter } from "../api/client";
import type { AuthAdapter } from "./adapter";

/**
 * 로그인 상태는 둘이 아니라 셋이다.
 * "확인 중(loading)"을 "비로그인(anonymous)"과 합치면, 새로고침 직후 SDK가 세션을 복구하기 전에
 * 권한을 물어서 관리자가 비로그인으로 판정된다 (myWeb에서 밟은 문제).
 */
export type AuthState =
  | { status: "loading" }
  | { status: "anonymous" }
  | { status: "authenticated"; uid: string; isAdmin: boolean };

type AuthContextValue = {
  state: AuthState;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ adapter, children }: { adapter: AuthAdapter; children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading" });

  useEffect(() => {
    setTokenGetter(() => adapter.getToken());
    let active = true;
    let latest = 0;
    // 조회가 아니라 구독 — SDK가 복구를 끝냈다고 알려줄 때만 권한을 묻는다
    const unsubscribe = adapter.subscribe((user) => {
      const call = ++latest;
      if (user === null) {
        setState({ status: "anonymous" });
        return;
      }
      setState({ status: "loading" });
      api
        .me()
        .then((me) => {
          if (active && call === latest) setState({ status: "authenticated", uid: me.uid, isAdmin: me.is_admin });
        })
        .catch(() => {
          if (active && call === latest) setState({ status: "anonymous" });
        });
    });
    return () => {
      active = false;
      unsubscribe();
    };
  }, [adapter]);

  const value = useMemo<AuthContextValue>(
    () => ({ state, signIn: () => adapter.signIn(), signOut: () => adapter.signOut() }),
    [state, adapter],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (value === null) throw new Error("AuthProvider 밖에서 useAuth를 썼다");
  return value;
}

export function useIsAdmin(): boolean {
  const { state } = useAuth();
  return state.status === "authenticated" && state.isAdmin;
}
