import { config } from "../config";
import type { components } from "./schema";

/** 백엔드 OpenAPI에서 생성한 스키마 (npm run gen:api). 손으로 타입을 다시 적지 않는다. */
export type S = components["schemas"];
export type Page<T> = { items: T[]; total: number; limit: number; offset: number };
export type TokenGetter = () => Promise<string | null>;

let tokenGetter: TokenGetter = async () => null;

export function setTokenGetter(getter: TokenGetter): void {
  tokenGetter = getter;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type RequestOptions = { json?: unknown; form?: FormData; auth?: boolean };

async function errorMessage(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      const messages = data.detail.map((d: { msg?: string }) => d.msg ?? "").filter(Boolean);
      if (messages.length > 0) return messages.join(" / ");
    }
  } catch {
    // JSON이 아닌 응답
  }
  return `요청 실패 (${response.status})`;
}

async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.auth) {
    // 토큰은 매 요청마다 인증 SDK에서 받는다 — 만료·갱신을 직접 관리하지 않는다
    const token = await tokenGetter();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  let body: BodyInit | undefined;
  if (options.form) {
    body = options.form;
  } else if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  }
  const response = await fetch(`${config.apiBaseUrl}${path}`, { method, headers, body });
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

function formOf(fields: Record<string, File | string | number | null | undefined>): FormData {
  const form = new FormData();
  for (const [key, value] of Object.entries(fields)) {
    if (value === undefined || value === null) continue;
    form.append(key, value instanceof File ? value : String(value));
  }
  return form;
}

export const api = {
  me: () => request<S["MeOut"]>("GET", "/api/auth/me", { auth: true }),

  flavorTags: () => request<S["FlavorTagOut"][]>("GET", "/api/flavor-tags"),
  beans: (limit = 50, offset = 0) => request<Page<S["BeanOut"]>>("GET", `/api/beans${query({ limit, offset })}`),
  bean: (id: number) => request<S["BeanStatsOut"]>("GET", `/api/beans/${id}`),
  similarBeans: (id: number) => request<S["SimilarBeanOut"][]>("GET", `/api/beans/${id}/similar`),
  brews: (params: { beanId?: number; limit?: number; offset?: number } = {}) =>
    request<Page<S["BrewOut"]>>(
      "GET",
      `/api/brews${query({ bean_id: params.beanId, limit: params.limit ?? 20, offset: params.offset ?? 0 })}`,
    ),
  brew: (id: number) => request<S["BrewOut"]>("GET", `/api/brews/${id}`),
  grinders: () => request<S["GrinderOut"][]>("GET", "/api/grinders"),
  calibration: (grinderId: number) => request<S["CalibrationOut"]>("GET", `/api/grinders/${grinderId}/calibration`),
  suggestClicks: (grinderId: number, targetD50: number) =>
    request<S["ClickSuggestionOut"]>("GET", `/api/grinders/${grinderId}/suggest${query({ target_d50_mm: targetD50 })}`),
  catalog: (limit = 50, offset = 0) =>
    request<Page<S["CatalogBeanOut"]>>("GET", `/api/catalog${query({ limit, offset })}`),
  latestRecommendations: () =>
    request<S["RecommendationSnapshotOut"] | null>("GET", "/api/recommendations/latest"),

  admin: {
    extractBean: (file: File) =>
      request<S["BeanDraftOut"]>("POST", "/api/admin/beans/extract", { auth: true, form: formOf({ file }) }),
    createBean: (body: S["BeanIn"]) => request<S["BeanOut"]>("POST", "/api/admin/beans", { auth: true, json: body }),
    createGrinder: (body: S["GrinderIn"]) =>
      request<S["GrinderOut"]>("POST", "/api/admin/grinders", { auth: true, json: body }),
    createBrew: (body: S["BrewIn"]) => request<S["BrewOut"]>("POST", "/api/admin/brews", { auth: true, json: body }),
    suggestTags: (note: string) =>
      request<S["TagSuggestOut"]>("POST", "/api/admin/brews/suggest-tags", { auth: true, json: { note } }),
    analyzeGrind: (file: File) =>
      request<S["GrindAnalysisOut"]>("POST", "/api/admin/grind/analyze", { auth: true, form: formOf({ file }) }),
    createMeasurement: (file: File, fields: { brewId?: number; grinderId?: number; clicks?: number }) =>
      request<S["GrindMeasurementOut"]>("POST", "/api/admin/grind/measurements", {
        auth: true,
        form: formOf({ file, brew_id: fields.brewId, grinder_id: fields.grinderId, clicks: fields.clicks }),
      }),
    collectCatalog: () => request<S["CollectResultOut"]>("POST", "/api/admin/catalog/collect", { auth: true }),
    refreshRecommendations: () =>
      request<S["RecommendationSnapshotOut"]>("POST", "/api/admin/recommendations/refresh", { auth: true }),
  },
};
