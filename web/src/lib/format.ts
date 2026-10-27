export const pct = (x: number | null | undefined, digits = 0) =>
  x === null || x === undefined || Number.isNaN(x) ? 'n/a' : `${(100 * x).toFixed(digits)}%`

export const fixed = (x: number | null | undefined, digits = 1) =>
  x === null || x === undefined || Number.isNaN(x) ? 'n/a' : x.toFixed(digits)

export const signed = (x: number | null | undefined, digits = 2) =>
  x === null || x === undefined || Number.isNaN(x) ? 'n/a' : `${x >= 0 ? '+' : '−'}${Math.abs(x).toFixed(digits)}`

export const int = (x: number | null | undefined) => (x === null || x === undefined ? 'n/a' : x.toLocaleString('en-GB'))

export const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

/** Read a CSS custom property (resolved for the current theme). */
export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

export const SENTIMENT_VAR: Record<string, string> = {
  positive: '--pos',
  neutral: '--neu',
  negative: '--neg',
  unavailable: '--muted',
}
export const SENTIMENT_FILL: Record<string, string> = {
  positive: 'var(--pos-fill)',
  neutral: 'var(--neu-fill)',
  negative: 'var(--neg-fill)',
}
