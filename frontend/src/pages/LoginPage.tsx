import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { ErrorBox } from "../components/States";
import { config } from "../config";

export function LoginPage() {
  const { state, signIn } = useAuth();
  const location = useLocation();
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  if (state.status === "authenticated") {
    return state.isAdmin ? (
      <Navigate to={from} replace />
    ) : (
      <div className="alert">로그인은 됐지만 관리자 허용 목록에 없는 계정이에요. 보기는 로그인 없이도 돼요.</div>
    );
  }

  const handleSignIn = async () => {
    setBusy(true);
    setError(null);
    try {
      await signIn();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h1>관리자 로그인</h1>
      <p className="muted">기록을 쓰는 건 관리자만 할 수 있어요. 보기는 로그인 없이 돼요.</p>
      <button type="button" className="btn" disabled={busy || state.status === "loading"} onClick={handleSignIn}>
        {config.authMode === "firebase" ? "Google로 로그인" : "개발용 로그인"}
      </button>
      {error !== null && <ErrorBox error={error} />}
    </>
  );
}
