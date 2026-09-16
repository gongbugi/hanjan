import { useEffect, useState } from "react";

export function PhotoInput({
  label,
  hint,
  onFile,
}: {
  label: string;
  hint?: string;
  onFile: (file: File | null) => void;
}) {
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );

  return (
    <label>
      {label}
      {/* 아이폰 HEIC는 서버가 못 읽는다. 브라우저 파일 선택은 대개 JPEG로 바꿔 올리지만, 형식은 명시해 둔다 */}
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        onChange={(event) => {
          const file = event.target.files?.[0] ?? null;
          setPreview(file ? URL.createObjectURL(file) : null);
          onFile(file);
        }}
      />
      {hint && <span className="muted">{hint}</span>}
      {preview && <img src={preview} alt="고른 사진 미리보기" className="photo-preview" />}
    </label>
  );
}
