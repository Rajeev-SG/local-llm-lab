# Acceptance: current installed-model guide

## Expected behavior

The production site should act as a one-page guide to every local AI model currently available on this Mac. It should:

- show 23 exact installed builds and seven tuned names
- distinguish installed builds from previously tested builds
- expose local rank, work-fit, quality, speed, peak memory, file size, context, modalities, capabilities, cautions, and exact source links where available
- filter the inventory by runtime, capability, search text, and alias
- remain readable and usable on phone, tablet, normal desktop, and wide desktop widths

## Executed steps

Target URL: `https://local-llm-lab.vercel.app`

Deployment:

- Vercel deployment: `dpl_EEk48fBHqvguULAfNgwx81topbpz`
- deployed source checkpoint: `90c6f31`
- deployment state: `Ready`
- production alias explicitly assigned to the new deployment

Browser flow:

1. Opened the production guide.
2. Confirmed the page title and the 23-build inventory summary.
3. Confirmed Qwen3 Coder 30B A3B appears as local rank 1 with a 98.3 work-fit score.
4. Applied the image-input filter and confirmed image-capable models remained while Whisper was excluded.
5. Switched to Ollama and searched for `local-helper-fast`.
6. Confirmed the search resolved to the installed Qwen3.5 9B build.
7. Expanded “Details and source” and confirmed the tuned alias, local benchmark artifact, and exact model-page link were reachable.
8. Confirmed the four removed MLX builds remain visible only in the historical section.
9. Cleared the filters and confirmed all 23 installed builds returned.
10. Repeated the complete flow at 375, 768, 1440, and 1575 pixels.

Command:

```bash
PLAYWRIGHT_BASE_URL=https://local-llm-lab.vercel.app pnpm test:smoke
```

Result: four projects passed.

## Evidence

- normal desktop hero: `output/playwright/model-guide-production-20260730/hero-desktop.png`
- wide desktop hero: `output/playwright/model-guide-production-20260730/hero-wide.png`
- mobile hero: `output/playwright/model-guide-production-20260730/hero-mobile.png`
- tablet filtered inventory: `output/playwright/model-guide-production-20260730/inventory-tablet.png`
- mobile filtered inventory and expanded details: `output/playwright/model-guide-production-20260730/inventory-mobile.png`
- desktop aliases: `output/playwright/model-guide-production-20260730/aliases-desktop.png`
- mobile historical results: `output/playwright/model-guide-production-20260730/historical-mobile.png`
- full normal-desktop page: `output/playwright/model-guide-production-20260730/full-page-desktop.png`

## Design review

- AI-generated interface patterns: pass. The page uses an editorial reference layout, not repeated cards, decorative gradients, glowing dark panels, or generic metric tiles.
- Normal desktop width: pass. The hero, recommendations, controls, and model rows use the available width.
- Wide desktop width: pass. The 1575-pixel capture has no large dead zones or leftover side space.
- Intermediate width: pass. At 768 pixels, model specifications and benchmark evidence reflow without overlap or clipping.
- Mobile: pass. Filters, model details, aliases, historical scores, methods, and run commands remain in the correct reading order.
- Tall narrow panels: none found.
- Whitespace: intentional section separation rather than unused layout space.
- Primary workflow: the searchable installed inventory is visually stronger than setup and method information.
- Below-the-fold sections: no overlap, clipping, horizontal page scroll, or broken reflow found.
- Console: no errors in any of the four projects.

## Accessibility and performance review

- Search, sort, filter groups, details controls, tables, navigation, and headings have semantic labels or native elements.
- Keyboard focus is visible.
- Interactive controls retain at least a 44-pixel target at narrow widths.
- Reduced-motion preferences disable the remaining transitions and smooth scrolling.
- The production build completed successfully.
- Built assets: approximately 232 KB JavaScript and 17 KB CSS before compression.

## Result

PASS

The user can identify an installed model, compare its local evidence and capabilities, filter by the required job, open the exact source and evidence, and distinguish current availability from historical testing on the deployed site.

## Remaining risk

The public inventory is a checked-in snapshot. Installing or deleting another model requires rerunning `python3 scripts/generate-current-model-guide.py`, reviewing the generated data, and redeploying. Qwen3 Coder Next is not installed and is therefore intentionally absent from the current-model list.
