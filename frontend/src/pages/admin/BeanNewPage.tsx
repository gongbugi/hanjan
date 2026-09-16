import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type ChangeEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, type S } from "../../api/client";
import { PhotoInput } from "../../components/PhotoInput";
import { ErrorBox } from "../../components/States";

type BeanForm = {
  name: string;
  roaster: string;
  country: string;
  region: string;
  variety: string;
  processing: string;
  roast_level: string;
  notes: string;
};

const EMPTY: BeanForm = {
  name: "",
  roaster: "",
  country: "",
  region: "",
  variety: "",
  processing: "",
  roast_level: "",
  notes: "",
};

const FIELDS: [Exclude<keyof BeanForm, "notes">, string][] = [
  ["name", "원두 이름 *"],
  ["roaster", "로스터리"],
  ["country", "나라"],
  ["region", "지역"],
  ["variety", "품종"],
  ["processing", "가공 방식"],
  ["roast_level", "로스팅"],
];

function fromDraft(draft: S["BeanDraft"]): BeanForm {
  return {
    name: draft.name ?? "",
    roaster: draft.roaster ?? "",
    country: draft.country ?? "",
    region: draft.region ?? "",
    variety: draft.variety ?? "",
    processing: draft.processing ?? "",
    roast_level: draft.roast_level ?? "",
    notes: draft.bag_flavor_notes.join(", "),
  };
}

function toBody(form: BeanForm): S["BeanIn"] {
  const text = (value: string) => value.trim() || null;
  return {
    name: form.name.trim(),
    roaster: text(form.roaster),
    country: text(form.country),
    region: text(form.region),
    variety: text(form.variety),
    processing: text(form.processing),
    roast_level: text(form.roast_level),
    bag_flavor_notes: form.notes
      .split(/[,\n]/)
      .map((note) => note.trim())
      .filter(Boolean),
  };
}

export function BeanNewPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [form, setForm] = useState<BeanForm>(EMPTY);

  const extract = useMutation({
    mutationFn: (photo: File) => api.admin.extractBean(photo),
    onSuccess: (result) => setForm(fromDraft(result.draft)),
  });
  const save = useMutation({
    mutationFn: (body: S["BeanIn"]) => api.admin.createBean(body),
    onSuccess: (bean) => {
      void queryClient.invalidateQueries({ queryKey: ["beans"] });
      navigate(`/beans/${bean.id}`);
    },
  });

  const bind = (key: keyof BeanForm) => (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((prev) => ({ ...prev, [key]: event.target.value }));

  return (
    <>
      <h1>원두 등록</h1>
      <div className="card">
        <PhotoInput
          label="원두 봉투 사진"
          hint="택배 송장(이름·주소)이 찍히지 않게 해 주세요. 사진은 AI 제공자에게 전송돼요."
          onFile={setFile}
        />
        <button
          type="button"
          className="btn btn--ghost"
          style={{ marginTop: 8 }}
          disabled={!file || extract.isPending}
          onClick={() => file && extract.mutate(file)}
        >
          {extract.isPending ? "읽는 중…" : "사진에서 채우기"}
        </button>
        {extract.data && (
          <div className="alert">
            AI가 {extract.data.filled_fields}칸을 채웠어요 ({extract.data.model}). 봉투와 대조해서 고친 뒤 저장하세요.
            빈 칸은 봉투에서 읽지 못한 거예요.
          </div>
        )}
        {extract.isError && <ErrorBox error={extract.error} />}
      </div>

      <form
        className="card"
        onSubmit={(event) => {
          event.preventDefault();
          save.mutate(toBody(form));
        }}
      >
        <div className="fields-2">
          {FIELDS.map(([key, label]) => (
            <label key={key}>
              {label}
              <input value={form[key]} onChange={bind(key)} required={key === "name"} />
            </label>
          ))}
        </div>
        <label>
          봉투 컵노트 (쉼표로 구분)
          <textarea rows={2} value={form.notes} onChange={bind("notes")} />
        </label>
        <button className="btn" disabled={!form.name.trim() || save.isPending}>
          {save.isPending ? "저장 중…" : "저장"}
        </button>
        {save.isError && <ErrorBox error={save.error} />}
      </form>
    </>
  );
}
