import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { S } from "../api/client";

const BRAND = "#6f4e37";

export type GrindResult = Pick<
  S["GrindAnalysisOut"],
  "particle_count" | "d10_mm" | "d50_mm" | "d90_mm" | "min_detectable_mm" | "clump_suspects" | "histogram" | "warnings"
>;

export function GrindHistogram({ result }: { result: GrindResult }) {
  const data = result.histogram.map((bin) => ({
    label: bin.lo_mm.toFixed(1),
    share: Math.round(bin.area_share * 1000) / 10,
  }));
  return (
    <div>
      <div className="grid">
        <div>
          <div className="muted">D50 (면적 기준)</div>
          <div className="stat">{result.d50_mm.toFixed(2)}mm</div>
        </div>
        <div>
          <div className="muted">D10 ~ D90</div>
          <div className="stat">
            {result.d10_mm.toFixed(2)}~{result.d90_mm.toFixed(2)}
          </div>
        </div>
        <div>
          <div className="muted">입자 수</div>
          <div className="stat">{result.particle_count.toLocaleString()}</div>
        </div>
      </div>
      <div style={{ width: "100%", height: 220, marginTop: 8 }}>
        <ResponsiveContainer>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" unit="mm" fontSize={12} />
            <YAxis unit="%" fontSize={12} width={44} />
            <Tooltip formatter={(value) => [`${value}%`, "면적 비율"]} />
            <Bar dataKey="share" fill={BRAND} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="muted">
        약 {result.min_detectable_mm.toFixed(2)}mm보다 작은 미분은 이 사진으로 잡지 못해요 · 뭉친 입자 의심{" "}
        {result.clump_suspects}개
      </p>
      {result.warnings.map((warning) => (
        <div key={warning} className="alert">
          {warning}
        </div>
      ))}
    </div>
  );
}

export function CalibrationChart({ rows }: { rows: S["CalibrationRowOut"][] }) {
  return (
    <div style={{ width: "100%", height: 220 }}>
      <ResponsiveContainer>
        <LineChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="clicks" type="number" domain={["dataMin", "dataMax"]} unit="클릭" fontSize={12} />
          <YAxis unit="mm" fontSize={12} width={52} domain={["auto", "auto"]} />
          <Tooltip />
          <Line type="monotone" dataKey="d50_median_mm" name="D50 중앙값" stroke={BRAND} strokeWidth={2} dot />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
