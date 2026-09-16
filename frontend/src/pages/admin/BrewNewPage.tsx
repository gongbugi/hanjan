import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api, type S } from "../../api/client";
import { useBeans, useFlavorTags, useGrinders } from "../../api/queries";
import { FlavorTagPicker, MAX_TAGS } from "../../components/FlavorTags";
import { RatingInput } from "../../components/Rating";
import { ErrorBox } from "../../components/States";
import { parseNumber } from "../../format";

export function BrewNewPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [params] = useSearchParams();
  const beans = useBeans(100);
  const grinders = useGrinders();
  const tags = useFlavorTags();

  const [beanId, setBeanId] = useState(params.get("bean") ?? "");
  const [grinderId, setGrinderId] = useState("");
  const [clicks, setClicks] = useState("");
  const [temp, setTemp] = useState("92");
  const [seconds, setSeconds] = useState("");
  const [dose, setDose] = useState("15");
  const [water, setWater] = useState("240");
  const [rating, setRating] = useState(0);
  const [note, setNote] = useState("");
  const [selected, setSelected] = useState<string[]>([]);

  const suggest = useMutation({
    mutationFn: (text: string) => api.admin.suggestTags(text),
    onSuccess: (result) => setSelected((prev) => [...new Set([...prev, ...result.tags])].slice(0, MAX_TAGS)),
  });
  const save = useMutation({
    mutationFn: (body: S["BrewIn"]) => api.admin.createBrew(body),
    onSuccess: (brew) => {
      void queryClient.invalidateQueries({ queryKey: ["brews"] });
      navigate(`/brews/${brew.id}`);
    },
  });

  const doseG = parseNumber(dose);
  const waterG = parseNumber(water);
  const ratio = doseG && waterG ? (waterG / doseG).toFixed(1) : null;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    save.mutate({
      bean_id: Number(beanId),
      grinder_id: grinderId ? Number(grinderId) : null,
      grind_clicks: parseNumber(clicks),
      water_temp_c: parseNumber(temp),
      dose_g: doseG,
      water_g: waterG,
      brew_time_s: parseNumber(seconds),
      rating,
      flavor_tags: selected,
      note: note.trim() || null,
    });
  };

  return (
    <>
      <h1>새 추출 기록</h1>
      <form className="card" onSubmit={submit}>
        <label>
          원두 *
          <select value={beanId} onChange={(e) => setBeanId(e.target.value)} required>
            <option value="">고르기</option>
            {beans.data?.items.map((bean) => (
              <option key={bean.id} value={bean.id}>
                {bean.name}
              </option>
            ))}
          </select>
        </label>
        {beans.data?.items.length === 0 && (
          <p className="muted">
            먼저 <Link to="/admin/beans/new">원두를 등록</Link>하세요.
          </p>
        )}

        <div className="fields-2">
          <label>
            그라인더
            <select value={grinderId} onChange={(e) => setGrinderId(e.target.value)}>
              <option value="">안 적음</option>
              {grinders.data?.map((grinder) => (
                <option key={grinder.id} value={grinder.id}>
                  {grinder.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            분쇄 클릭 (영점에서 푼 수)
            <input inputMode="numeric" value={clicks} onChange={(e) => setClicks(e.target.value)} />
          </label>
          <label>
            물 온도(℃)
            <input inputMode="numeric" value={temp} onChange={(e) => setTemp(e.target.value)} />
          </label>
          <label>
            추출 시간(초)
            <input inputMode="numeric" value={seconds} onChange={(e) => setSeconds(e.target.value)} />
          </label>
          <label>
            원두(g)
            <input inputMode="decimal" value={dose} onChange={(e) => setDose(e.target.value)} />
          </label>
          <label>
            물(g){ratio && ` · 1:${ratio}`}
            <input inputMode="decimal" value={water} onChange={(e) => setWater(e.target.value)} />
          </label>
        </div>

        <div>
          <div className="muted">만족도 *</div>
          <RatingInput value={rating} onChange={setRating} />
        </div>

        <label>
          맛 메모
          <textarea
            rows={3}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="예: 레몬 같은 산미, 끝에 홍차 느낌"
          />
        </label>
        <button
          type="button"
          className="btn btn--ghost"
          disabled={!note.trim() || suggest.isPending}
          onClick={() => suggest.mutate(note)}
        >
          {suggest.isPending ? "고르는 중…" : "메모에서 맛 태그 고르기"}
        </button>
        {suggest.data && suggest.data.dropped.length > 0 && (
          <p className="muted">목록에 없는 태그 {suggest.data.dropped.length}개는 버렸어요.</p>
        )}
        {suggest.isError && <ErrorBox error={suggest.error} />}
        <FlavorTagPicker tags={tags.data ?? []} selected={selected} onChange={setSelected} />

        <button className="btn" disabled={!beanId || rating === 0 || save.isPending}>
          {save.isPending ? "저장 중…" : "저장"}
        </button>
        {save.isError && <ErrorBox error={save.error} />}
      </form>
    </>
  );
}
