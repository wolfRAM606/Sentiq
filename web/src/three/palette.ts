// Three.js materials cannot read CSS variables, so the theme colours are mirrored here (docs/DESIGN_SYSTEM.md).
export const THREE_PALETTE = {
  light: { bg: '#EDE6DA', rule: '#B9AC97', text: '#25242A', brand: '#702F45', positive: '#6F9A79', neutral: '#C49A3A', negative: '#C0634C' },
  dark: { bg: '#26232A', rule: '#5A5360', text: '#EFE8DC', brand: '#D08AA0', positive: '#8AAB91', neutral: '#D9B66A', negative: '#E58C73' },
} as const
