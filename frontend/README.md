# AI QA Platform — Frontend

Next.js App Router UI for the AI QA Platform.

## Stack

- Next.js 16 + React 19 + TypeScript
- Tailwind CSS v4
- TanStack Query, Zustand, Axios
- React Hook Form + Zod

## Getting started

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) — redirects to **Story Management** (`/stories`).

Backend must be running at `NEXT_PUBLIC_API_URL` (default `http://localhost:8000/api/v1`).

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Dev server |
| `npm run build` | Production build |
| `npm test` | Vitest unit tests |
| `npm run lint` | ESLint |

## Docs

See [docs/StoryManagement.md](./docs/StoryManagement.md) for Milestone 6 details.
