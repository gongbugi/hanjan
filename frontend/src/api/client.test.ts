import { afterEach, describe, expect, it, vi } from "vitest";

import { api, setTokenGetter } from "./client";

function stubFetch(status: number, body: unknown) {
  const fetchMock = vi.fn(
    async (_url: string, _init?: RequestInit) =>
      new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  setTokenGetter(async () => null);
});

describe("api client", () => {
  it("관리자 요청마다 SDK에서 토큰을 새로 받아 붙인다", async () => {
    const getter = vi.fn(async () => "fresh-token");
    setTokenGetter(getter);
    const fetchMock = stubFetch(200, { tags: [], dropped: [], provider: "fake", model: "m" });

    await api.admin.suggestTags("레몬");
    await api.admin.suggestTags("레몬");

    expect(getter).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/api/admin/brews/suggest-tags");
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get("Authorization")).toBe("Bearer fresh-token");
  });

  it("공개 조회에는 토큰을 붙이지 않는다", async () => {
    setTokenGetter(async () => "token");
    const fetchMock = stubFetch(200, []);

    await api.flavorTags();

    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).has("Authorization")).toBe(false);
  });

  it("서버가 준 detail을 에러 메시지로 쓴다", async () => {
    stubFetch(429, { detail: "AI 하루 한도를 넘었어요" });

    await expect(api.admin.suggestTags("x")).rejects.toMatchObject({
      status: 429,
      message: "AI 하루 한도를 넘었어요",
    });
  });

  it("검증 오류 목록을 한 문장으로 합친다", async () => {
    stubFetch(422, { detail: [{ msg: "이름이 비었어요" }, { msg: "너무 길어요" }] });

    await expect(api.admin.createGrinder({ name: "" })).rejects.toThrow("이름이 비었어요 / 너무 길어요");
  });
});
