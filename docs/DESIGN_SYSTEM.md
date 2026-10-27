# Sentiq design system: Ivory, Burgundy and Sage

Version 1.0. Premium editorial, light by default, with a matching dark mode.

Sentiq should feel like a premium academic intelligence platform: warm ivory surfaces, deep burgundy accents,
muted sage for analytical highlights, and crisp typography. One identity runs across the Streamlit pages, the
web interface, the charts and the downloadable reports.

The four core colours come from the project owner's brief. Every other value below is derived from them and
contrast-checked (WCAG ratios shown for text tokens). These are the canonical values. Do not introduce
near-duplicate shades on individual pages.

## Core palette

| Name | Hex | Role |
|---|---|---|
| Warm Ivory | `#F5F0E8` | Light-mode canvas |
| Oxblood Burgundy | `#702F45` | Brand, primary actions, selected navigation, key emphasis |
| Muted Sage | `#8AAB91` | Secondary accent: supporting visualisations, positive trends, subtle highlights (fills only, not text) |
| Ink Charcoal | `#25242A` | Primary text |

## Tokens

| Token | Light | Dark | Notes |
|---|---|---|---|
| `--bg` | `#F5F0E8` | `#1D1B1F` | Canvas. Dark is warm charcoal, never pure black |
| `--surface` | `#EDE6DA` | `#26232A` | Panels, table headers |
| `--surface-2` | `#E5DCCC` | `#302C34` | Fills, chart tracks (not for text backgrounds) |
| `--rule` | `#D3C8B6` | `#3D3842` | 1 px hairlines and borders |
| `--text` | `#25242A` (13.6:1) | `#EFE8DC` (14.0:1) | Body text |
| `--muted` | `#625C57` (5.8:1) | `#ABA399` (6.9:1) | Secondary text |
| `--brand` | `#702F45` (8.5:1) | `#D08AA0` (6.4:1) | Links, primary buttons, selected state |
| `--brand-ink` | `#F5F0E8` | `#1D1B1F` | Text on brand fills (8.5:1 / 6.4:1) |
| `--brand-tint` | `rgba(112,47,69,.08)` | `rgba(208,138,160,.12)` | Selected rows, hover backgrounds |
| `--sage` | `#8AAB91` | `#8AAB91` | Data accent fill |
| `--sage-text` | `#45694E` (5.5:1) | `#9DBDA3` (8.3:1) | Sage as text |
| `--positive` | `#45694E` | `#9DBDA3` | Positive sentiment |
| `--neutral` | `#7A5D16` | `#D9B66A` | Neutral sentiment (ochre) |
| `--negative` | `#A8442F` | `#E58C73` | Negative sentiment (brick, kept distinct from the burgundy brand colour) |

Sentiment fills in charts use the same three hues at full strength, so positive is sage, neutral is ochre and
negative is brick everywhere: charts, tables, cards and reports.

## Typography

All fonts are self-hosted (SIL Open Font License; licences in `static/fonts/`). No external font requests.

| Use | Family | Weights |
|---|---|---|
| Display and headings | Fraunces (variable serif) | 400–650, optical sizing on |
| Body and interface | IBM Plex Sans | 400, 500, 600 |
| Numbers, labels, metadata | IBM Plex Mono | 400, 500 |

Scale: display 64/56/44 px; section 32 px; body 16 px with line height 1.55; labels 12 px mono in uppercase with
0.08 em tracking.

## Shape and depth

* Square corners (`border-radius: 0`; a maximum of 2 px for focus outlines).
* No drop shadows. Depth comes from 1 px rules, surface changes and whitespace.
* No gradients on surfaces or text.
* No coloured side stripes on cards. Sentiment is shown with a labelled colour chip or the text colour itself.

## Motion

* Scroll-driven reveals: sections fade and rise 24 px, charts draw in when they enter the viewport, numbers count
  up once. Durations 0.5–0.9 s with ease-out.
* Hover: colour, underline or background-tint changes only. No lifting, scaling, tilting or bouncing.
* `prefers-reduced-motion` turns all motion off.

## Things this system never uses

Lucide or sparkle icons, emojis, em dashes in copy, Inter, Geist or Space Grotesk, liquid glass, harsh gradients,
pure white backgrounds, rainbow or neon colours, purple-and-black themes, pastel palettes, drop shadows, soft
rounded corners, radial orbs, dot grids, bento grids, three-card feature rows, terminal windows, coloured left
stripes, checkmark bullets, animated arrows, skeleton loaders, fake testimonials, pricing tiers, and boilerplate
legal pages.
