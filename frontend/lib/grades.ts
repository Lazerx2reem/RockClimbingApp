export const V_SCALE: string[] = [
  "VB",
  ...Array.from({ length: 18 }, (_, i) => `V${i}`),
];

export const YDS: string[] = [
  "5.5",
  "5.6",
  "5.7",
  "5.8",
  "5.9",
  ...[10, 11, 12, 13, 14, 15].flatMap((n) =>
    ["a", "b", "c", "d"].map((l) => `5.${n}${l}`)
  ),
];
