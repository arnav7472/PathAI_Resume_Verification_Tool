# TODO - PathAI Verify Frontend → New PathAI Design System

## Phase 1 — Global theme/design system integration (stability-first)
- [x] Inspect current Tailwind/global styles in `src/styles/*`.
- [x] Inspect design system tokens/animations in `pathai_design/styles/*` and `pathai_design/app/globals.css` (design system utilities like `glass-card`, `fade-in-up`, `pulse-dot`, `shimmer` already exist as CSS tokens).
- [x] Confirm current Vite app already uses shadcn-style theme variables in `src/styles/theme.css` and imports `tailwind.css` + `fonts.css` via `src/styles/index.css`.
- [x] Merge/adapt required design-system CSS variables/classes into Vite app (`src/styles/index.css`, `src/styles/theme.css`). (Added PathAI design utilities from `pathai_design/app/globals.css` into `src/styles/theme.css`, incl. `glass-card`, `fade-in-up`, `pulse-dot`, `shimmer`.)
- [x] Ensure Tailwind input scans include any new class usage (no visual regression).
- [x] Verify: `npm run dev` (no console errors).
- [x] Verify build: `npm run build`.

## Phase 2 — Shell/layout migration
- [x] Refactor `src/app/components/DashboardLayout.tsx` to use design-system shell/sidebar styles.
- [x] Ensure routing (`Outlet`) and active link styling behave identically.
- [x] Verify: `npm run dev` + smoke test navigation.
- [x] Verify build: `npm run build`. 


## Phase 3 — Page-by-page UI migration (no business logic changes)
- [x] Upload page: migrate form/cards/buttons/loading to design system; keep upload/OCR/verify flow intact.
- [x] Summary/dashboard page: migrate cards/typography; preserve Recharts usage.
- [x] Evidence page: migrate timeline/evidence cards/badges; preserve data rendering.
- [x] Reports page: migrate empty/loading states; preserve history query/calls.
- [x] Settings page: migrate toggles/inputs; preserve localStorage behavior.
- [x] Skills page: migrate lists/badges/progress.
- [x] Help page: migrate typography.
- [ ] Verify: smoke test upload → scan → summary → evidence.
- [x] Verify build: `npm run build`.

## Phase 4 — Animation/loading enhancements (subtle premium)
- [x] Add Framer Motion transitions to scan result reveal + loading states.
- [x] Add skeletons for analysis pending states.
- [x] Ensure animations respect reduced-motion preferences.
- [x] Verify: no console errors and no noticeable lag.

## Phase 5 — Dependency cleanup and verification
- [x] Check for Tailwind/shadcn dependency conflicts.
- [x] Ensure consistent icon imports (Lucide) and chart theming (Recharts).
- [x] Run final `npm run build` and verify no lint/type errors.
- [ ] Optional cleanup: remove unused legacy styles only after stable migration.

