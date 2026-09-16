import type { AuthAdapter, AuthUser } from "./adapter";

const KEY = "hanjan-dev-signed-in";

/** 로컬 개발용. 백엔드 HANJAN_AUTH_MODE=dev의 개발용 토큰을 쓴다. */
export function createDevAdapter(token: string, storage: Storage = window.localStorage): AuthAdapter {
  const listeners = new Set<(user: AuthUser | null) => void>();
  const current = (): AuthUser | null => (storage.getItem(KEY) === "1" ? { uid: "dev" } : null);
  const emit = () => {
    const user = current();
    for (const listener of listeners) listener(user);
  };

  return {
    subscribe(listener) {
      listeners.add(listener);
      // 실제 SDK처럼 복구를 비동기로 알린다 — 개발 중에도 "확인 중" 상태를 거치게
      const timer = setTimeout(() => listener(current()), 0);
      return () => {
        clearTimeout(timer);
        listeners.delete(listener);
      };
    },
    async signIn() {
      storage.setItem(KEY, "1");
      emit();
    },
    async signOut() {
      storage.removeItem(KEY);
      emit();
    },
    async getToken() {
      return current() ? token : null;
    },
  };
}
