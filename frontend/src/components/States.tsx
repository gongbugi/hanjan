import type { ReactNode } from "react";

export function Skeleton({ lines = 2 }: { lines?: number }) {
  return (
    <div aria-busy="true" aria-label="불러오는 중">
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="skeleton" />
      ))}
    </div>
  );
}

export function ErrorBox({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : "알 수 없는 오류가 났어요";
  return (
    <div className="alert alert--error" role="alert">
      {message}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="muted">{children}</p>;
}
