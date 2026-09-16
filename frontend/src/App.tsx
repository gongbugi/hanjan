import { lazy } from "react";
import { createBrowserRouter, Link, RouterProvider } from "react-router-dom";

import { Layout } from "./components/Layout";
import { RequireAdmin } from "./components/RequireAdmin";
import { HomePage } from "./pages/HomePage";

// 첫 화면(HomePage)만 처음부터 받고 나머지는 열 때 받는다.
// 방문자는 차트(recharts)와 쓰기 화면을 받지 않는다 — 프로필의 조회 p95 500ms가 이 경로다.
const BeansPage = lazy(() => import("./pages/BeansPage").then((m) => ({ default: m.BeansPage })));
const BeanDetailPage = lazy(() => import("./pages/BeanDetailPage").then((m) => ({ default: m.BeanDetailPage })));
const BrewDetailPage = lazy(() => import("./pages/BrewDetailPage").then((m) => ({ default: m.BrewDetailPage })));
const GrindersPage = lazy(() => import("./pages/GrindersPage").then((m) => ({ default: m.GrindersPage })));
const RecommendationsPage = lazy(() =>
  import("./pages/RecommendationsPage").then((m) => ({ default: m.RecommendationsPage })),
);
const CatalogPage = lazy(() => import("./pages/CatalogPage").then((m) => ({ default: m.CatalogPage })));
const LoginPage = lazy(() => import("./pages/LoginPage").then((m) => ({ default: m.LoginPage })));
const AdminHomePage = lazy(() => import("./pages/admin/AdminHomePage").then((m) => ({ default: m.AdminHomePage })));
const BeanNewPage = lazy(() => import("./pages/admin/BeanNewPage").then((m) => ({ default: m.BeanNewPage })));
const BrewNewPage = lazy(() => import("./pages/admin/BrewNewPage").then((m) => ({ default: m.BrewNewPage })));
const GrindMeasurePage = lazy(() =>
  import("./pages/admin/GrindMeasurePage").then((m) => ({ default: m.GrindMeasurePage })),
);

function NotFound() {
  return (
    <>
      <h1>페이지를 찾을 수 없어요</h1>
      <Link to="/">처음으로</Link>
    </>
  );
}

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/beans", element: <BeansPage /> },
      { path: "/beans/:id", element: <BeanDetailPage /> },
      { path: "/brews/:id", element: <BrewDetailPage /> },
      { path: "/grinders", element: <GrindersPage /> },
      { path: "/recommendations", element: <RecommendationsPage /> },
      { path: "/catalog", element: <CatalogPage /> },
      { path: "/login", element: <LoginPage /> },
      { path: "/admin", element: <RequireAdmin><AdminHomePage /></RequireAdmin> },
      { path: "/admin/beans/new", element: <RequireAdmin><BeanNewPage /></RequireAdmin> },
      { path: "/admin/brews/new", element: <RequireAdmin><BrewNewPage /></RequireAdmin> },
      { path: "/admin/grind", element: <RequireAdmin><GrindMeasurePage /></RequireAdmin> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}
