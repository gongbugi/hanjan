import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "../api/client";
import { useCatalog } from "../api/queries";
import { useIsAdmin } from "../auth/AuthContext";
import { Empty, ErrorBox, Skeleton } from "../components/States";

export function CatalogPage() {
  const catalog = useCatalog();
  const isAdmin = useIsAdmin();
  const queryClient = useQueryClient();
  const collect = useMutation({
    mutationFn: () => api.admin.collectCatalog(),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["catalog"] }),
  });

  return (
    <>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>로스터리 신상</h1>
        {isAdmin && (
          <button type="button" className="btn btn--ghost" disabled={collect.isPending} onClick={() => collect.mutate()}>
            {collect.isPending ? "수집 중…" : "지금 수집"}
          </button>
        )}
      </div>
      {collect.data && (
        <div className="alert">
          새 상품 {collect.data.new} · 정리 {collect.data.normalized} · 원두 아님 {collect.data.skipped} · 대기{" "}
          {collect.data.pending}
          {collect.data.errors.length > 0 && (
            <ul>
              {collect.data.errors.map((error) => (
                <li key={error}>{error}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {collect.isError && <ErrorBox error={collect.error} />}
      {catalog.isPending ? (
        <Skeleton lines={3} />
      ) : catalog.isError ? (
        <ErrorBox error={catalog.error} />
      ) : catalog.data.items.length === 0 ? (
        <Empty>수집한 신상이 없어요.</Empty>
      ) : (
        catalog.data.items.map((item) => {
          const notes = Array.isArray(item.normalized?.flavor_notes) ? (item.normalized.flavor_notes as string[]) : [];
          return (
            <div key={item.id} className="card">
              <a href={item.source_url} target="_blank" rel="noreferrer">
                <strong>{item.title}</strong>
              </a>
              <div className="muted">
                {[item.source_name, item.country, item.processing, item.price].filter(Boolean).join(" · ")}
              </div>
              {notes.length > 0 && (
                <div className="row" style={{ marginTop: 6 }}>
                  {notes.map((note) => (
                    <span key={note} className="chip">
                      {note}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })
      )}
    </>
  );
}
