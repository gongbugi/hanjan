import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api, type S } from "../api/client";
import { useCalibration, useClickSuggestion, useGrinders } from "../api/queries";
import { useIsAdmin } from "../auth/AuthContext";
import { CalibrationChart } from "../components/GrindCharts";
import { Empty, ErrorBox, Skeleton } from "../components/States";
import { parseNumber } from "../format";

function GrinderSection({ grinder }: { grinder: S["GrinderOut"] }) {
  const calibration = useCalibration(grinder.id);
  const [target, setTarget] = useState("");
  const suggestion = useClickSuggestion(grinder.id, parseNumber(target));

  return (
    <div className="card">
      <strong>{grinder.name}</strong>
      {grinder.notes && <p className="muted">{grinder.notes}</p>}
      {calibration.isPending ? (
        <Skeleton />
      ) : calibration.isError ? (
        <ErrorBox error={calibration.error} />
      ) : calibration.data.rows.length === 0 ? (
        <Empty>아직 입도를 잰 적이 없어요. 여러 클릭에서 재면 클릭 ↔ 입도 표가 만들어져요.</Empty>
      ) : (
        <>
          {!calibration.data.monotonic && (
            <div className="alert">
              클릭을 늘려도 입도가 커지지 않는 구간이 있어요. 영점이 틀어졌거나 측정이 흔들렸을 수 있어요.
            </div>
          )}
          <CalibrationChart rows={calibration.data.rows} />
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>클릭</th>
                  <th>측정 수</th>
                  <th>D50 중앙값</th>
                  <th>범위</th>
                </tr>
              </thead>
              <tbody>
                {calibration.data.rows.map((row) => (
                  <tr key={row.clicks}>
                    <td>{row.clicks}</td>
                    <td>{row.n}</td>
                    <td>{row.d50_median_mm.toFixed(2)}mm</td>
                    <td>
                      {row.d50_min_mm.toFixed(2)}~{row.d50_max_mm.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <label style={{ marginTop: 12 }}>
            원하는 D50(mm)을 넣으면 클릭 수로 바꿔 드려요
            <input inputMode="decimal" placeholder="예: 0.7" value={target} onChange={(e) => setTarget(e.target.value)} />
          </label>
          {suggestion.data && (
            <div className="alert">
              {suggestion.data.clicks !== null && <strong>{suggestion.data.clicks}클릭 · </strong>}
              {suggestion.data.reason}
            </div>
          )}
          {suggestion.isError && <ErrorBox error={suggestion.error} />}
        </>
      )}
    </div>
  );
}

function NewGrinderForm() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const create = useMutation({
    mutationFn: (body: S["GrinderIn"]) => api.admin.createGrinder(body),
    onSuccess: () => {
      setName("");
      void queryClient.invalidateQueries({ queryKey: ["grinders"] });
    },
  });

  return (
    <form
      className="card"
      onSubmit={(event) => {
        event.preventDefault();
        create.mutate({ name: name.trim(), notes: null });
      }}
    >
      <label>
        그라인더 추가
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="예: 알리 핸드밀 (모델 모름)" />
      </label>
      <p className="muted">클릭은 가장 곱게 조인 상태(영점)에서 몇 클릭 풀었는지로 기록해요.</p>
      <button className="btn" disabled={!name.trim() || create.isPending}>
        추가
      </button>
      {create.isError && <ErrorBox error={create.error} />}
    </form>
  );
}

export function GrindersPage() {
  const grinders = useGrinders();
  const isAdmin = useIsAdmin();

  return (
    <>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>그라인더</h1>
        {isAdmin && (
          <Link className="btn btn--ghost" to="/admin/grind">
            입도 측정
          </Link>
        )}
      </div>
      {isAdmin && <NewGrinderForm />}
      {grinders.isPending ? (
        <Skeleton />
      ) : grinders.isError ? (
        <ErrorBox error={grinders.error} />
      ) : grinders.data.length === 0 ? (
        <Empty>등록한 그라인더가 없어요.</Empty>
      ) : (
        grinders.data.map((grinder) => <GrinderSection key={grinder.id} grinder={grinder} />)
      )}
    </>
  );
}
