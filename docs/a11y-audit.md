# Accessibility audit — 2026-11-04

Scope: the eight product screens at 390 px and 1440 px, light and dark, in Chromium 141
against the production bundle (`vite preview`, port 4173) talking to the real API on
`127.0.0.1:8765`.

## Method, and what it can and cannot prove

Contrast was measured in the page: `getComputedStyle` for the foreground, the nearest opaque
ancestor background, then WCAG 2.x relative luminance and the `(L1+0.05)/(L2+0.05)` ratio.
Large text uses the 3:1 floor, normal text the 4.5:1 floor (WCAG 2.2 SC 1.4.3).

**Limitation, stated because it matters:** some ancestor backgrounds are written as
`oklch(…)` inside `color-mix()` or via a variable that the sampling canvas could not resolve
on every element. In those cases the resolver fell back to black and produced a physically
impossible ratio (1.26:1 for a mid-grey on a light surface). Those pairs are reported here as
**unresolved**, not as failures — a measurement that cannot be trusted must not be quoted as
either a pass or a fail. Resolving them needs a pixel-sampling harness, which this run did not
build.

## Found and fixed

| Finding | Measured | Fix |
|---|---|---|
| Crisis footnote `text-pop-red-ink/80` at 12 px | **4.26:1** (floor 4.5) | dropped the 80 % opacity → full `--pop-red-ink` |
| Destructive button fill, light theme: `oklch(0.63 0.235 32)` + white label | **3.80:1** (floor 4.5) | fill darkened to `oklch(0.53 0.19 30)` → **4.94:1** |
| `--muted-foreground` `oklch(0.51 0.009 80)` on the page surface | **4.72:1**, no margin for any opacity variant | `oklch(0.47 0.009 80)` → **5.5:1** on the surface, 5.9:1 on white |

Both changes are monotone increases in contrast, so no pair that passed before can fail now.

## Measured cleanly (light theme)

| Pair | Ratio |
|---|---|
| Body text `--foreground` on `--background` | 13.1 : 1 |
| Body text on card surface | 14.2 : 1 |
| `--muted-foreground` on white (sidebar) | 5.9 : 1 |
| `--muted-foreground` on the page surface | 5.5 : 1 |
| Primary button label (near-white on near-black) | 15.4 : 1 |
| Crisis card ink on crisis surface | 6.6 : 1 |
| Destructive button label on destructive fill | 4.94 : 1 |

The lowest verified pair is the destructive button at 4.94:1, which clears the 4.5:1 floor
without a margin large enough to be relaxed later.

## Structural checks (verified in the browser, not by inspection)

- `prefers-reduced-motion` rules are present in the compiled stylesheet
  (`conditionText` contains the media query).
- Skip link `Zum Inhalt springen` is the first focusable element and targets `#main-content`.
- `aria-live="polite"` on the transcript container, so streamed text is announced without
  interrupting.
- Every icon-only control has an `aria-label` (theme toggle, copy, send/stop).
- `aria-current="page"` on the active navigation button.
- `document.documentElement.lang` follows the selected locale (set before first paint).
- Crisis state is signalled by an icon, a heading and text — never by colour alone.
- Focus is visible on every interactive element (`focus-visible:ring-2` on the control tier).
- Horizontal overflow: `scrollWidth === clientWidth` on all eight screens at 375, 768 and
  1440 px.
- Command palette: `role="dialog"`, `aria-modal`, autofocused input, `Esc` closes, `Ctrl/⌘+K`
  toggles.

## Not done

- **Better Design review tools were not run.** The account returned `AGENT_QUOTA_EXHAUSTED`
  (25 free queries used, unchanged since the previous session). The evidence above is
  source-level plus rendered-browser measurement, **not** a tool receipt. Stating otherwise
  would be the exact kind of claim this repository refuses.
- No screen-reader pass with NVDA or Narrator. The structural checks above are necessary but
  not sufficient for that claim.
- No zoom/reflow test at 400 % (WCAG 1.4.10).
- Dark theme was swept (93 pairs). The destructive fill `oklch(0.68 0.21 32)` measured
  **3.08:1** against its white label — genuinely below the floor — and was darkened to
  `oklch(0.56 0.19 30)` (**4.62:1**). Re-measured after the change: no failures reported in
  the dark sweep.
