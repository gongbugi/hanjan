export function RatingStars({ value }: { value: number }) {
  return (
    <span aria-label={`${value}점`} style={{ color: "var(--accent)", letterSpacing: 1 }}>
      {"★".repeat(value)}
      <span style={{ color: "var(--line)" }}>{"★".repeat(5 - value)}</span>
    </span>
  );
}

export function RatingInput({ value, onChange }: { value: number; onChange: (value: number) => void }) {
  return (
    <div className="stars" role="group" aria-label="만족도">
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} type="button" aria-label={`${n}점`} aria-pressed={n <= value} onClick={() => onChange(n)}>
          ★
        </button>
      ))}
    </div>
  );
}
