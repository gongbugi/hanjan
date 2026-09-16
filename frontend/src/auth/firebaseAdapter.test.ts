/**
 * 이 어댑터에는 테스트가 없었다. 번들에서 Firebase를 미루려면 여기부터 덮어야 한다 —
 * 인증 상태 3가지는 myWeb에서 밟은 자리라 조용히 깨지면 안 된다.
 *
 * 비동기로 기다리게 쓴 것은 의도다: SDK를 정적으로 받든 늦게 받든 같은 테스트가 통과해야 한다.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const onAuthStateChanged = vi.fn();
const signInWithPopup = vi.fn().mockResolvedValue(undefined);
const signOutFn = vi.fn().mockResolvedValue(undefined);
const getAuth = vi.fn();
const initializeApp = vi.fn(() => ({ name: "app" }));

let currentUser: { getIdToken: () => Promise<string> } | null = null;

vi.mock("firebase/app", () => ({
  initializeApp: (...args: unknown[]) => initializeApp(...(args as [])),
  getApps: () => [],
}));

vi.mock("firebase/auth", () => ({
  getAuth: (...args: unknown[]) => {
    getAuth(...(args as []));
    return { get currentUser() { return currentUser; } };
  },
  onAuthStateChanged: (...args: unknown[]) => onAuthStateChanged(...(args as [])),
  signInWithPopup: (...args: unknown[]) => signInWithPopup(...(args as [])),
  signOut: (...args: unknown[]) => signOutFn(...(args as [])),
  GoogleAuthProvider: class GoogleAuthProvider {},
}));

async function adapter() {
  const { createFirebaseAdapter } = await import("./firebaseAdapter");
  return createFirebaseAdapter();
}

describe("firebaseAdapter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
    currentUser = null;
  });

  it("로그인한 사용자를 uid로 넘긴다", async () => {
    const listener = vi.fn();
    (await adapter()).subscribe(listener);

    await vi.waitFor(() => expect(onAuthStateChanged).toHaveBeenCalled());
    onAuthStateChanged.mock.calls[0][1]({ uid: "abc", email: "x@y.z" });

    expect(listener).toHaveBeenCalledWith({ uid: "abc" });
  });

  it("로그아웃 상태는 null로 넘긴다", async () => {
    const listener = vi.fn();
    (await adapter()).subscribe(listener);

    await vi.waitFor(() => expect(onAuthStateChanged).toHaveBeenCalled());
    onAuthStateChanged.mock.calls[0][1](null);

    expect(listener).toHaveBeenCalledWith(null);
  });

  it("구독 해제는 SDK의 해제 함수를 실제로 부른다", async () => {
    // myWeb에서 어댑터의 해제를 빈 함수로 둬서 누수 위험이 남았다 (adapter.ts 주석)
    const sdkUnsubscribe = vi.fn();
    onAuthStateChanged.mockReturnValue(sdkUnsubscribe);
    const unsubscribe = (await adapter()).subscribe(vi.fn());

    await vi.waitFor(() => expect(onAuthStateChanged).toHaveBeenCalled());
    unsubscribe();

    expect(sdkUnsubscribe).toHaveBeenCalledTimes(1);
  });

  it("로그인은 리다이렉트가 아니라 팝업을 쓴다", async () => {
    // 앱 주소(pages.dev)와 authDomain이 달라서, 서드파티 저장소를 막는 브라우저에서 리다이렉트가 깨진다
    await (await adapter()).signIn();

    expect(signInWithPopup).toHaveBeenCalledTimes(1);
  });

  it("토큰은 로그인했을 때만 준다", async () => {
    const a = await adapter();
    expect(await a.getToken()).toBeNull();

    currentUser = { getIdToken: () => Promise.resolve("id-token") };
    expect(await a.getToken()).toBe("id-token");
  });

  it("앱을 한 번만 초기화한다", async () => {
    const a = await adapter();
    a.subscribe(vi.fn());
    await a.getToken();
    await a.signOut();

    await vi.waitFor(() => expect(onAuthStateChanged).toHaveBeenCalled());
    expect(initializeApp).toHaveBeenCalledTimes(1);
    expect(signOutFn).toHaveBeenCalledTimes(1);
  });
});
