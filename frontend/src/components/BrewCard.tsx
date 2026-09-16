import { Link } from "react-router-dom";

import type { S } from "../api/client";
import { formatDate, orDash } from "../format";
import { TagLabels } from "./FlavorTags";
import { RatingStars } from "./Rating";

export function BrewCard({ brew, tags }: { brew: S["BrewOut"]; tags: S["FlavorTagOut"][] }) {
  const d50 = brew.measurements.at(-1)?.d50_mm;
  return (
    <Link to={`/brews/${brew.id}`} className="card card-link">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <strong>{brew.bean.name}</strong>
        <RatingStars value={brew.rating} />
      </div>
      <div className="muted">
        {formatDate(brew.brewed_on)} · {orDash(brew.grind_clicks, "클릭")} · {orDash(brew.water_temp_c, "℃")} · 1:
        {orDash(brew.ratio)}
        {d50 !== undefined && ` · D50 ${d50.toFixed(2)}mm`}
      </div>
      {brew.flavor_tags.length > 0 && <TagLabels keys={brew.flavor_tags} tags={tags} />}
    </Link>
  );
}
