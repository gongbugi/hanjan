import { config } from "../config";
import type { AuthAdapter } from "./adapter";

/**
 * Firebase SDK를 **쓸 때 받는다**. 정적으로 import하면 로그인하지 않는 방문자도 함께 내려받는다
 * (첫 로드가 그만큼 커진다 — 프로필의 조회 p95 500ms가 이 경로다).
 *
 * 받는 동안 인증 상태는 "확인 중"으로 남는다. 그게 3상태를 둔 이유 그대로다:
 * 복구가 끝나기 전에 비로그인으로 판정하지 않는다.
 */
let ready: ReturnType<typeof load> | null = null;

async function load() {
  const [{ initializeApp, getApps }, auth] = await Promise.all([import("firebase/app"), import("firebase/auth")]);
  const app = getApps()[0] ?? initializeApp(config.firebase);
  return { ...auth, instance: auth.getAuth(app) };
}

const sdk = () => (ready ??= load());

export function createFirebaseAdapter(): AuthAdapter {
  return {
    subscribe: (listener) => {
      let unsubscribe: (() => void) | null = null;
      let cancelled = false;
      void sdk().then(({ onAuthStateChanged, instance }) => {
        if (cancelled) return; // 로드가 끝나기 전에 해제됐다 — 붙이지 않는다
        // onAuthStateChanged는 복구가 끝난 뒤 호출되고, 진짜 구독 해제 함수를 돌려준다
        unsubscribe = onAuthStateChanged(instance, (user) => listener(user ? { uid: user.uid } : null));
      });
      return () => {
        cancelled = true;
        unsubscribe?.();
      };
    },
    // 리다이렉트 로그인은 앱 주소(pages.dev)와 authDomain(firebaseapp.com)이 다르면
    // 서드파티 저장소를 막는 브라우저(Safari 16.1+ · Firefox 109+ · Chrome M115+)에서 실패한다 → 팝업을 쓴다
    signIn: async () => {
      const { signInWithPopup, GoogleAuthProvider, instance } = await sdk();
      await signInWithPopup(instance, new GoogleAuthProvider());
    },
    signOut: async () => {
      const { signOut, instance } = await sdk();
      await signOut(instance);
    },
    getToken: async () => {
      const { instance } = await sdk();
      const user = instance.currentUser;
      return user ? user.getIdToken() : null;
    },
  };
}
