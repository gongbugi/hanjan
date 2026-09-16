import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { expect, it } from "vitest";

import { FlavorTagPicker, MAX_TAGS } from "./FlavorTags";

const TAGS = Array.from({ length: 8 }, (_, i) => ({
  key: `g.t${i}`,
  group: "g",
  group_label: "그룹",
  label: `맛${i}`,
}));

function Harness() {
  const [selected, setSelected] = useState<string[]>([]);
  return <FlavorTagPicker tags={TAGS} selected={selected} onChange={setSelected} />;
}

it(`태그는 ${MAX_TAGS}개까지만 고를 수 있다`, () => {
  render(<Harness />);

  for (let i = 0; i < MAX_TAGS; i++) fireEvent.click(screen.getByRole("button", { name: `맛${i}` }));

  expect(screen.getByRole("button", { name: "맛6" })).toBeDisabled();
  expect(screen.getByText(`${MAX_TAGS}/${MAX_TAGS}개 골랐어요`)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "맛0" }));

  expect(screen.getByRole("button", { name: "맛6" })).toBeEnabled();
});
