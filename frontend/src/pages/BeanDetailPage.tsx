import { Link, useParams } from "react-router-dom";

import { useBean, useBrews, useFlavorTags, useSimilarBeans } from "../api/queries";
import { BrewCard } from "../components/BrewCard";
import { Empty, ErrorBox, Skeleton } from "../components/States";

export function BeanDetailPage() {
  const id = Number(useParams().id);
  const bean = useBean(id);
  const similar = useSimilarBeans(id);
  const brews = useBrews({ beanId: id, limit: 50 });
  const tags = useFlavorTags();

  if (bean.isPending) return <Skeleton lines={4} />;
  if (bean.isError) return <ErrorBox error={bean.error} />;

  const { bean: b, brew_count, avg_rating } = bean.data;
  const rows: [string, string | null][] = [
    ["로스터리", b.roaster],
    ["산지", [b.country, b.region].filter(Boolean).join(" ") || null],
    ["품종", b.variety],
    ["가공", b.processing],
    ["로스팅", b.roast_level],
  ];

  return (
    <>
      <h1>{b.name}</h1>
      <div className="card">
        <div className="table-wrap">
          <table>
            <tbody>
              {rows.map(([label, value]) => (
                <tr key={label}>
                  <th>{label}</th>
                  <td>{value ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {b.bag_flavor_notes.length > 0 && (
          <div className="row" style={{ marginTop: 8 }}>
            {b.bag_flavor_notes.map((note) => (
              <span key={note} className="chip">
                {note}
              </span>
            ))}
          </div>
        )}
        <p className="muted">
          기록 {brew_count}번 · 평균 만족도 {avg_rating ?? "-"}
        </p>
      </div>

      <h2>비슷한 원두</h2>
      {similar.isPending ? (
        <Skeleton />
      ) : similar.isError ? (
        <ErrorBox error={similar.error} />
      ) : similar.data.length === 0 ? (
        <Empty>비교할 원두가 아직 없어요.</Empty>
      ) : (
        similar.data.map((s) => (
          <Link key={s.bean.id} to={`/beans/${s.bean.id}`} className="card card-link">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <strong>{s.bean.name}</strong>
              <span className="muted">유사도 {(s.similarity * 100).toFixed(0)}%</span>
            </div>
            <div className="muted">
              기록 {s.brew_count}번 · 평균 {s.avg_rating ?? "-"}
            </div>
          </Link>
        ))
      )}

      <h2>추출 기록</h2>
      {brews.isPending ? (
        <Skeleton />
      ) : brews.isError ? (
        <ErrorBox error={brews.error} />
      ) : brews.data.items.length === 0 ? (
        <Empty>이 원두로 내린 기록이 없어요.</Empty>
      ) : (
        brews.data.items.map((brew) => <BrewCard key={brew.id} brew={brew} tags={tags.data ?? []} />)
      )}
    </>
  );
}
