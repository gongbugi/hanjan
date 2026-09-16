import { Link } from "react-router-dom";

import { useBrews, useFlavorTags } from "../api/queries";
import { useIsAdmin } from "../auth/AuthContext";
import { BrewCard } from "../components/BrewCard";
import { Empty, ErrorBox, Skeleton } from "../components/States";

export function HomePage() {
  const brews = useBrews({ limit: 20 });
  const tags = useFlavorTags();
  const isAdmin = useIsAdmin();

  return (
    <>
      <h1>최근 추출 기록</h1>
      {isAdmin && (
        <div className="row" style={{ marginBottom: 12 }}>
          <Link className="btn" to="/admin/brews/new">
            새 추출 기록
          </Link>
          <Link className="btn btn--ghost" to="/admin/beans/new">
            원두 등록
          </Link>
        </div>
      )}
      {brews.isPending ? (
        <Skeleton lines={3} />
      ) : brews.isError ? (
        <ErrorBox error={brews.error} />
      ) : brews.data.items.length === 0 ? (
        <Empty>아직 추출 기록이 없어요.</Empty>
      ) : (
        brews.data.items.map((brew) => <BrewCard key={brew.id} brew={brew} tags={tags.data ?? []} />)
      )}
    </>
  );
}
