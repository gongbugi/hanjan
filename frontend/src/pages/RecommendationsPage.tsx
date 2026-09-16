import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api, type S } from "../api/client";
import { useLatestRecommendations } from "../api/queries";
import { useIsAdmin } from "../auth/AuthContext";
import { Empty, ErrorBox, Skeleton } from "../components/States";
import { formatDateTime } from "../format";

function RecommendationCard({ item }: { item: S["RecommendationItemOut"] }) {
  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between" }}>
        {item.kind === "catalog" && item.source_url ? (
          <a href={item.source_url} target="_blank" rel="noreferrer">
            <strong>{item.title}</strong>
          </a>
        ) : (
          <Link to={`/beans/${item.ref_id}`}>
            <strong>{item.title}</strong>
          </Link>
        )}
        <span className="muted">취향 유사도 {(item.similarity * 100).toFixed(0)}%</span>
      </div>
      <p>{item.reason}</p>
      <p className="muted">
        {item.reason_source === "llm"
          ? "AI가 쓴 이유 · 인용한 기록이 실제 근거인지 코드가 확인했어요"
          : "템플릿 문장 · AI 이유가 근거 확인을 통과하지 못했거나 AI를 쓸 수 없었어요"}
        {" · 근거 "}
        {item.evidence_brew_ids.map((brewId, index) => (
          <span key={brewId}>
            {index > 0 && ", "}
            <Link to={`/brews/${brewId}`}>기록 #{brewId}</Link>
          </span>
        ))}
      </p>
      {item.start_grind && (
        <div className="alert">
          시작 굵기 D50 {item.start_grind.d50_mm.toFixed(2)}mm
          {item.start_grind.clicks !== null && ` → 약 ${item.start_grind.clicks}클릭`}
          <div className="muted">{item.start_grind.reason}</div>
        </div>
      )}
    </div>
  );
}

export function RecommendationsPage() {
  const latest = useLatestRecommendations();
  const isAdmin = useIsAdmin();
  const queryClient = useQueryClient();
  const refresh = useMutation({
    mutationFn: () => api.admin.refreshRecommendations(),
    onSuccess: (snapshot) => queryClient.setQueryData(["recommendations", "latest"], snapshot),
  });

  let content;
  if (latest.isPending) {
    content = <Skeleton lines={3} />;
  } else if (latest.isError) {
    content = <ErrorBox error={latest.error} />;
  } else if (latest.data === null) {
    content = <Empty>아직 추천을 만든 적이 없어요.</Empty>;
  } else {
    const snapshot = latest.data;
    const catalog = snapshot.items.filter((item) => item.kind === "catalog");
    const mine = snapshot.items.filter((item) => item.kind === "my_bean");
    content = (
      <>
        <p className="muted">
          {formatDateTime(snapshot.created_at)} 기준 · 임베딩 {snapshot.embedding_model} · 이유{" "}
          {snapshot.llm_model ?? "템플릿"}
        </p>
        {snapshot.items.length === 0 && <Empty>만족도 4점 이상인 기록이 없어서 추천할 근거가 없어요.</Empty>}
        {catalog.length > 0 && (
          <>
            <h2>신상 중 취향에 맞는 원두</h2>
            {catalog.map((item) => (
              <RecommendationCard key={`catalog-${item.ref_id}`} item={item} />
            ))}
          </>
        )}
        {mine.length > 0 && (
          <>
            <h2>내 기록 중 취향에 가까운 원두</h2>
            {mine.map((item) => (
              <RecommendationCard key={`bean-${item.ref_id}`} item={item} />
            ))}
          </>
        )}
      </>
    );
  }

  return (
    <>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>추천</h1>
        {isAdmin && (
          <button type="button" className="btn btn--ghost" disabled={refresh.isPending} onClick={() => refresh.mutate()}>
            {refresh.isPending ? "만드는 중…" : "추천 새로 만들기"}
          </button>
        )}
      </div>
      {refresh.isError && <ErrorBox error={refresh.error} />}
      {content}
    </>
  );
}
