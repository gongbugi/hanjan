import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Skeleton } from "./States";

/** 화면 숨김은 편의일 뿐이다. 실제 차단은 서버의 require_admin이 한다. */
export function RequireAdmin({ children }: { children: ReactNode }) {
  const { state } = useAuth();
  const location = useLocation();

  if (state.status === "loading") return <Skeleton lines={3} />; // 아직 모른다 — 판단하지 않는다
  if (state.status === "anonymous") return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (!state.isAdmin) return <div className="alert">관리자만 쓸 수 있어요.</div>;
  return <>{children}</>;
}
