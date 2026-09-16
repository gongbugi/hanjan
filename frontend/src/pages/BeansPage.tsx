import { Link } from "react-router-dom";

import { useBeans } from "../api/queries";
import { useIsAdmin } from "../auth/AuthContext";
import { Empty, ErrorBox, Skeleton } from "../components/States";

export function BeansPage() {
  const beans = useBeans(100);
  const isAdmin = useIsAdmin();

  return (
    <>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>원두</h1>
        {isAdmin && (
          <Link className="btn" to="/admin/beans/new">
            원두 등록
          </Link>
        )}
      </div>
      {beans.isPending ? (
        <Skeleton lines={3} />
      ) : beans.isError ? (
        <ErrorBox error={beans.error} />
      ) : beans.data.items.length === 0 ? (
        <Empty>등록한 원두가 없어요.</Empty>
      ) : (
        beans.data.items.map((bean) => (
          <Link key={bean.id} to={`/beans/${bean.id}`} className="card card-link">
            <strong>{bean.name}</strong>
            <div className="muted">
              {[bean.roaster, bean.country, bean.region, bean.processing].filter(Boolean).join(" · ") || "정보 없음"}
            </div>
          </Link>
        ))
      )}
    </>
  );
}
