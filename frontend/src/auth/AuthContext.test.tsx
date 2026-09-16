import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import type { AuthAdapter, AuthUser } from "./adapter";
import { AuthProvider, useAuth } from "./AuthContext";

function controllableAdapter() {
  let listener: ((user: AuthUser | null) => void) | null = null;
  const unsubscribe = vi.fn();
  const adapter: AuthAdapter = {
    subscribe: (next) => {
      listener = next;
      return unsubscribe;
    },
    signIn: vi.fn(async () => {}),
    signOut: vi.fn(async () => {}),
    getToken: vi.fn(async () => "token-123"),
  };
  return { adapter, unsubscribe, emit: (user: AuthUser | null) => listener?.(user) };
}

function stubMe(body: unknown, status = 200) {
  const fetchMock = vi.fn(
    async (_url: string, _init?: RequestInit) =>
      new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function Probe() {
  const { state } = useAuth();
  return <div data-testid="state">{state.status === "authenticated" ? `admin=${state.isAdmin}` : state.status}</div>;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

it("SDK가 세션 복구를 끝내기 전에는 권한을 묻지 않는다", async () => {
  const fetchMock = stubMe({ uid: "u1", is_admin: true });
  const { adapter, emit } = controllableAdapter();

  render(
    <AuthProvider adapter={adapter}>
      <Probe />
    </AuthProvider>,
  );

  // 새로고침 직후: 아직 모른다 — "비로그인"이 아니라 "확인 중"
  expect(screen.getByTestId("state")).toHaveTextContent("loading");
  expect(fetchMock).not.toHaveBeenCalled();

  act(() => emit({ uid: "u1" }));

  await waitFor(() => expect(screen.getByTestId("state")).toHaveTextContent("admin=true"));
  const init = fetchMock.mock.calls[0][1];
  expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer token-123");
});

it("복구 결과가 비로그인이면 anonymous이고 권한을 묻지 않는다", async () => {
  const fetchMock = stubMe({});
  const { adapter, emit } = controllableAdapter();
  render(
    <AuthProvider adapter={adapter}>
      <Probe />
    </AuthProvider>,
  );

  act(() => emit(null));

  expect(screen.getByTestId("state")).toHaveTextContent("anonymous");
  expect(fetchMock).not.toHaveBeenCalled();
});

it("언마운트하면 구독을 해제한다", () => {
  stubMe({});
  const { adapter, unsubscribe } = controllableAdapter();
  const { unmount } = render(
    <AuthProvider adapter={adapter}>
      <Probe />
    </AuthProvider>,
  );

  unmount();

  expect(unsubscribe).toHaveBeenCalledTimes(1);
});
