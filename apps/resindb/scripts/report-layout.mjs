/**
 * Return the largest font size that keeps a single-line label inside maxWidth.
 * The caller supplies a text measurement callback so this stays independent of
 * any PDF or canvas implementation and remains easy to regression-test.
 */
export function fitSingleLineFontSize(
  text,
  maxWidth,
  measureText,
  { preferred = 18, minimum = 8, step = 0.5 } = {},
) {
  if (typeof text !== 'string') text = String(text ?? '');
  if (!Number.isFinite(maxWidth) || maxWidth <= 0) return minimum;
  if (typeof measureText !== 'function') throw new TypeError('measureText must be a function');

  for (let size = preferred; size >= minimum; size -= step) {
    const width = measureText(text, size);
    if (Number.isFinite(width) && width <= maxWidth) return size;
  }
  return minimum;
}
