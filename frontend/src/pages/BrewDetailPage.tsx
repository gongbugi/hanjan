import { Link, useParams } from "react-router-dom";

import { useBrew, useFlavorTags } from "../api/queries";
import { useIsAdmin } from "../auth/AuthContext";
import { TagLabels } from "../components/FlavorTags";
import { GrindHistogram } from "../components/GrindCharts";
import { RatingStars } from "../components/Rating";
import { Empty, ErrorBox, Skeleton } from "../components/States";
import { formatDate, formatDateTime, formatSeconds, orDash } from "../format";

export function BrewDetailPage() {
  const id = Number(useParams().id);
  const brew = useBrew(id);
  const tags = useFlavorTags();
  const isAdmin = useIsAdmin();

  if (brew.isPending) return <Skeleton lines={4} />;
  if (brew.isError) return <ErrorBox error={brew.error} />;

  const b = brew.data;
  const rows: [string, string][] = [
    ["날짜", formatDate(b.brewed_on)],
    ["분쇄", orDash(b.grind_clicks, "클릭 (영점 기준)")],
    ["물 온도", orDash(b.water_temp_c, "℃")],
    ["원두 · 물", `${orDash(b.dose_g, "g")} · ${orDash(b.water_g, "g")}`],
    ["비율", b.ratio ? `1:${b.ratio}` : "-"],
    ["추출 시간", formatSeconds(b.brew_time_s)],
  ];

  return (
    <>
      <p className="muted">
        <Link to={`/beans/${b.bean.id}`}>{b.bean.name}</Link>
      </p>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>추출 기록</h1>
        <RatingStars value={b.rating} />
      </div>
      <div className="card">
        <div className="table-wrap">
          <table>
            <tbody>
              {rows.map(([label, value]) => (
                <tr key={label}>
                  <th>{label}</th>
                  <td>{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {b.flavor_tags.length > 0 && <TagLabels keys={b.flavor_tags} tags={tags.data ?? []} />}
        {b.note && <p style={{ whiteSpace: "pre-wrap" }}>{b.note}</p>}
      </div>

      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2>입도 측정</h2>
        {isAdmin && (
          <Link className="btn btn--ghost" to={`/admin/grind?brew=${b.id}`}>
            측정 추가
          </Link>
        )}
      </div>
      {b.measurements.length === 0 ? (
        <Empty>이 기록에 붙인 입도 측정이 없어요.</Empty>
      ) : (
        b.measurements.map((m) => (
          <div key={m.id} className="card">
            <p className="muted">
              {formatDateTime(m.created_at)} · {m.clicks}클릭
            </p>
            <GrindHistogram result={m} />
          </div>
        ))
      )}
    </>
  );
}
