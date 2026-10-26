/** Ascending numeric lock, wrapping 9 back to 0. */
export function digitRoll(from: number | null, to: number) {
  const start = from ?? (to + 9) % 10;
  const steps = (to - start + 10) % 10;
  const digits = Array.from({ length: steps + 1 }, (_, i) => (start + i) % 10);
  return { digits, steps, seconds: steps ? Math.min(.36, .08 + steps * .035) : 0 };
}
