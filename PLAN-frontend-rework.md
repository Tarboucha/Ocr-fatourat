# Plan: Frontend Rework with shadcn/ui (whole app)

## Context

The current frontend works but the UI is hand-rolled Tailwind with ad-hoc styling, `window.confirm`/`alert`, and no design system ([LoginPage.tsx](frontend/src/pages/LoginPage.tsx), [DocumentsPage.tsx](frontend/src/pages/DocumentsPage.tsx), [EditorPage.tsx](frontend/src/pages/EditorPage.tsx), [TopBar.tsx](frontend/src/components/TopBar.tsx)). We're reworking the whole app's look & feel by adopting **shadcn/ui** — the same React+TS+Vite+Tailwind+shadcn stack the `web-artifacts-builder` skill uses — into the real app.

**We are NOT using the skill's Parcel/single-HTML bundling** (that's for standalone artifacts and can't talk to our FastAPI backend). We only borrow its proven shadcn setup. **No backend changes.** All app logic — Zustand stores, TanStack Query hooks, react-konva canvas, routing, auth — stays; only the presentational layer changes.

## Design direction (avoid "AI slop")

Per the skill's guidance, deliberately avoid: dead-center everything, purple gradients, uniform pill rounding, Inter font.

- **Palette**: neutral **zinc** base + one restrained functional accent (default **blue-600**; easy to swap). Keep `manual`=indigo / `ocr`=emerald box colors as semantic tokens.
- **Font**: **Geist Sans** for UI + **Geist Mono** for numeric/coordinate/monetary values (`@fontsource-variable/geist`, `@fontsource-variable/geist-mono`) — not Inter.
- **Density**: this is a productivity tool — compact spacing, real toolbars, left-aligned forms, not airy marketing layouts.
- **Radius**: moderate (`0.5rem`); not everything rounded to a pill.

## Setup — shadcn integration (reuse the skill as a seed)

The skill's `init-artifact.sh` generates a project already wired for shadcn with 40+ components. Use it as a **seed** to copy proven config/components instead of fighting the interactive `shadcn init` CLI.

1. **Generate a throwaway seed** (user runs):
   `bash .claude/skills/web-artifacts-builder/scripts/init-artifact.sh /tmp/shadcn-seed`
2. **Copy into the real frontend**: `src/components/ui/*`, `src/lib/utils.ts` (the `cn()` helper), `components.json`, and merge the seed's `tailwind.config` theme block + `index.css` CSS variables. Prune `ui/` to the components we actually use (list below).
3. **Path alias `@/` → `src`**: add `resolve.alias` in [vite.config.ts](frontend/vite.config.ts) and `compilerOptions.paths` in [tsconfig.json](frontend/tsconfig.json). shadcn components import via `@/components/ui/...`.
4. **package.json deps**: `class-variance-authority`, `clsx`, `tailwind-merge`, `tailwindcss-animate`, `lucide-react` (icons), `sonner` (toasts), the `@radix-ui/react-*` primitives for the components used, and the two `@fontsource-variable/geist*` fonts.
5. **index.css**: import the fonts, add shadcn CSS variables (light theme; dark optional later), set the zinc base + accent.

Components we'll use (the rest can be pruned): `button`, `card`, `input`, `label`, `textarea`, `select`, `dropdown-menu`, `dialog`, `alert-dialog`, `badge`, `separator`, `tooltip`, `scroll-area`, `toggle-group`, `sonner` (toaster).

## Cross-cutting changes

- **New `components/layout/AppShell.tsx`**: shared chrome (top bar with brand, user email, logout) used by Documents + Editor. Replaces [TopBar.tsx](frontend/src/components/TopBar.tsx).
- **Toasts + dialogs**: mount `<Toaster />` (sonner) in [App.tsx](frontend/src/App.tsx). Replace every `window.confirm`/`alert` (e.g. delete in [DocumentsPage.tsx](frontend/src/pages/DocumentsPage.tsx), unsaved-page-switch in [EditorPage.tsx](frontend/src/pages/EditorPage.tsx)) with `AlertDialog` + `sonner` toasts for success/error.
- **Icons**: `lucide-react` throughout (upload, trash, chevrons, undo, etc.).

## Per-screen redesign

- **Login / Register** ([LoginPage.tsx](frontend/src/pages/LoginPage.tsx), [RegisterPage.tsx](frontend/src/pages/RegisterPage.tsx)): replace the shared `AuthShell`/`Field` with a shadcn `Card` + `Input`/`Label`/`Button`. A two-pane layout (brand/intro panel + form) instead of a centered box. Inline error via `Alert`. Reuse existing `loginRequest`/`useAuthStore` logic untouched.
- **Documents** ([DocumentsPage.tsx](frontend/src/pages/DocumentsPage.tsx), [UploadDropzone.tsx](frontend/src/components/UploadDropzone.tsx)): `AppShell` + a polished upload `Card` (drag state, lucide upload icon, progress via toast). Document list as `Card` rows with a `Badge` for page count/status, a `DropdownMenu` (Open / Delete) per row, and a proper empty state. Delete → `AlertDialog`. Keep `useDocuments`/`useUploadDocument`/`useDeleteDocument`.
- **Editor** ([EditorPage.tsx](frontend/src/pages/EditorPage.tsx), [BoxSidebar.tsx](frontend/src/components/editor/BoxSidebar.tsx)): reskin chrome only — the Konva `<Stage>` and box geometry logic in [KonvaStage.tsx](frontend/src/components/editor/KonvaStage.tsx) / [BoxItem.tsx](frontend/src/components/editor/BoxItem.tsx) stay as-is.
  - Toolbar: `ToggleGroup` for Select/Draw, icon `Button`s with `Tooltip`, page-nav as a button group with chevrons + "Page N / M", zoom readout.
  - Sidebar: `ScrollArea` list of box `Card`s, `Textarea` for text, Save / Run-OCR `Button`s with loading states, Geist Mono for any coordinate/number display.

## What stays unchanged

`stores/*`, `hooks/*`, `lib/api.ts`, `lib/queryClient.ts`, react-konva drawing/transform logic, react-router routes, and the entire backend.

## Rebuild

Frontend deps change → the frontend image reinstalls npm packages once (slower build), then back to fast:
```
docker compose up --build
```

## Verification (end-to-end)

1. App loads with Geist font, zinc/accent theme, no console errors; `tsc --noEmit` and `vite build` pass.
2. Register → Login render in the new Card/two-pane layout; auth still works and persists.
3. Documents: upload via the new dropzone (toast on success); list shows cards + page-count badges; row dropdown opens editor; delete shows AlertDialog then toast.
4. Editor: toolbar ToggleGroup switches tools; draw/move/resize a box still works (canvas unchanged); page nav chevrons work; Save / Run-OCR show loading + toast.
5. Logout from AppShell returns to login.
6. Responsive at narrow widths; no Inter, no purple gradients, no all-pill rounding.
```
