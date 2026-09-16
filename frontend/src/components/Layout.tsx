import { Suspense } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Skeleton } from "./States";

export function Layout() {
  const { state, signOut } = useAuth();
  const isAdmin = state.status === "authenticated" && state.isAdmin;

  return (
    <>
      <header className="app-header">
        <div className="app-header__inner">
          <Link to="/" className="brand">
            ☕ 한 잔
          </Link>
          {state.status === "authenticated" && (
            <button type="button" className="btn btn--light" onClick={() => void signOut()}>
              로그아웃
            </button>
          )}
          {state.status === "anonymous" && (
            <Link to="/login" className="btn btn--light">
              관리자
            </Link>
          )}
        </div>
        <nav className="nav" aria-label="주요 메뉴">
          <NavLink to="/" end>
            기록
          </NavLink>
          <NavLink to="/beans">원두</NavLink>
          <NavLink to="/grinders">그라인더</NavLink>
          <NavLink to="/recommendations">추천</NavLink>
          <NavLink to="/catalog">신상</NavLink>
          {isAdmin && <NavLink to="/admin">쓰기</NavLink>}
        </nav>
      </header>
      <main className="page">
        {/* 화면 코드를 나눠 받는다 (App.tsx의 lazy) — 받는 동안 뼈대를 보여준다 */}
        <Suspense fallback={<Skeleton lines={3} />}>
          <Outlet />
        </Suspense>
      </main>
    </>
  );
}
