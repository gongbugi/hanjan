import type { S } from "../api/client";

export const MAX_TAGS = 6;

type Tag = S["FlavorTagOut"];

export function FlavorTagPicker({
  tags,
  selected,
  onChange,
}: {
  tags: Tag[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const groups = new Map<string, { label: string; items: Tag[] }>();
  for (const tag of tags) {
    const group = groups.get(tag.group) ?? { label: tag.group_label, items: [] };
    group.items.push(tag);
    groups.set(tag.group, group);
  }
  const full = selected.length >= MAX_TAGS;
  const toggle = (key: string) => {
    if (selected.includes(key)) onChange(selected.filter((k) => k !== key));
    else if (!full) onChange([...selected, key]);
  };

  return (
    <div>
      {[...groups.entries()].map(([groupKey, group]) => (
        <div key={groupKey} style={{ marginBottom: 8 }}>
          <div className="muted">{group.label}</div>
          <div className="row">
            {group.items.map((tag) => {
              const on = selected.includes(tag.key);
              return (
                <button
                  key={tag.key}
                  type="button"
                  className="chip"
                  aria-pressed={on}
                  disabled={!on && full}
                  onClick={() => toggle(tag.key)}
                >
                  {tag.label}
                </button>
              );
            })}
          </div>
        </div>
      ))}
      <p className="muted">
        {selected.length}/{MAX_TAGS}개 골랐어요
      </p>
    </div>
  );
}

export function TagLabels({ keys, tags }: { keys: string[]; tags: Tag[] }) {
  const labels = new Map(tags.map((t) => [t.key, t.label]));
  return (
    <div className="row" style={{ marginTop: 6 }}>
      {keys.map((key) => (
        <span key={key} className="chip">
          {labels.get(key) ?? key}
        </span>
      ))}
    </div>
  );
}
