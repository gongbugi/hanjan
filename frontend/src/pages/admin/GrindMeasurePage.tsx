import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api } from "../../api/client";
import { useBrew, useGrinders } from "../../api/queries";
import { GrindHistogram } from "../../components/GrindCharts";
import { PhotoInput } from "../../components/PhotoInput";
import { ErrorBox } from "../../components/States";
import { orDash, parseNumber } from "../../format";

export function GrindMeasurePage() {
  const [params] = useSearchParams();
  const brewParam = params.get("brew");
  const brewId = brewParam ? Number(brewParam) : undefined;
  const brew = useBrew(brewId);
  const grinders = useGrinders();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [file, setFile] = useState<File | null>(null);
  const [grinderId, setGrinderId] = useState("");
  const [clicks, setClicks] = useState("");

  const preview = useMutation({ mutationFn: (photo: File) => api.admin.analyzeGrind(photo) });
  const save = useMutation({
    mutationFn: (photo: File) =>
      api.admin.createMeasurement(photo, {
        brewId,
        grinderId: grinderId ? Number(grinderId) : undefined,
        clicks: parseNumber(clicks) ?? undefined,
      }),
    onSuccess: (measurement) => {
      void queryClient.invalidateQueries({ queryKey: ["calibration", measurement.grinder_id] });
      if (brewId !== undefined) {
        void queryClient.invalidateQueries({ queryKey: ["brew", brewId] });
        navigate(`/brews/${brewId}`);
      } else {
        navigate("/grinders");
      }
    },
  });

  // 추출 기록에 그라인더·클릭이 적혀 있으면 그 값을 쓴다
  const needsGrinder = !brew.data?.grinder_id;
  const needsClicks = brew.data?.grind_clicks === null || brew.data?.grind_clicks === undefined;
  const canSave = file !== null && (!needsGrinder || grinderId !== "") && (!needsClicks || clicks !== "");

  return (
    <>
      <h1>입도 측정</h1>
      <div className="card">
        <p>1. 인쇄한 기준 마커와 원두 가루를 흰 종이 위에 둬요. 가루는 겹치지 않게 넓게 흩어요.</p>
        <p>2. 종이와 평행하게, 그림자가 지지 않게 위에서 찍어요. 사진은 줄이지 않고 원본으로 올라가요.</p>
        <p className="muted">
          마커는 백엔드의 scripts/make_marker.py로 만들어요. 인쇄는 반드시 실제 크기(100%)로 하고, 자로 한 변을 재서 서버
          설정에 넣어요.
        </p>
      </div>

      <div className="card">
        {brew.data && (
          <p className="muted">
            추출 기록: <Link to={`/brews/${brew.data.id}`}>{brew.data.bean.name}</Link> ·{" "}
            {orDash(brew.data.grind_clicks, "클릭")}
          </p>
        )}
        <div className="fields-2">
          {needsGrinder && (
            <label>
              그라인더 *
              <select value={grinderId} onChange={(e) => setGrinderId(e.target.value)}>
                <option value="">고르기</option>
                {grinders.data?.map((grinder) => (
                  <option key={grinder.id} value={grinder.id}>
                    {grinder.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {needsClicks && (
            <label>
              분쇄 클릭 (영점에서 푼 수) *
              <input inputMode="numeric" value={clicks} onChange={(e) => setClicks(e.target.value)} />
            </label>
          )}
        </div>
        <PhotoInput
          label="가루 사진"
          onFile={(photo) => {
            setFile(photo);
            preview.reset();
          }}
        />
        <div className="row" style={{ marginTop: 8 }}>
          <button
            type="button"
            className="btn btn--ghost"
            disabled={!file || preview.isPending}
            onClick={() => file && preview.mutate(file)}
          >
            {preview.isPending ? "재는 중…" : "미리 재 보기"}
          </button>
          <button
            type="button"
            className="btn"
            disabled={!canSave || save.isPending}
            onClick={() => file && save.mutate(file)}
          >
            {save.isPending ? "저장 중…" : "재고 저장"}
          </button>
        </div>
        {preview.isError && <ErrorBox error={preview.error} />}
        {save.isError && <ErrorBox error={save.error} />}
      </div>

      {preview.data && (
        <div className="card">
          <GrindHistogram result={preview.data} />
        </div>
      )}
    </>
  );
}
