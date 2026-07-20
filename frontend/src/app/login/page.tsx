"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { APP_NAME, ROUTES } from "@/lib/constants";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login({ email, password });
    } catch {
      setError("Invalid email or password. Ensure the API is running.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="relative flex min-h-full flex-1 items-center justify-center overflow-hidden bg-[radial-gradient(ellipse_at_top,_#e8f4f1_0%,_#f7faf9_45%,_#eef2f1_100%)] px-4 py-16">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%230d9488' fill-opacity='0.08'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")",
        }}
      />
      <div className="relative w-full max-w-md">
        <p className="text-center text-xs font-semibold uppercase tracking-[0.18em] text-accent">
          {APP_NAME}
        </p>
        <h1 className="mt-3 text-center text-3xl font-semibold tracking-tight text-foreground">
          Sign in
        </h1>
        <p className="mt-2 text-center text-sm text-muted">
          Access your QA workspace with email and password.
        </p>

        <form
          onSubmit={onSubmit}
          className="mt-8 flex flex-col gap-4 border border-border/80 bg-surface/90 p-6 shadow-sm backdrop-blur"
        >
          <Input
            label="Email"
            type="email"
            name="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
          />
          <Input
            label="Password"
            type="password"
            name="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
          {error ? (
            <p className="text-sm text-danger" role="alert">
              {error}
            </p>
          ) : null}
          <Button type="submit" loading={loading} className="w-full">
            Sign in
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted">
          <Link href={ROUTES.DASHBOARD} className="text-accent hover:underline">
            Continue without signing in
          </Link>
          {" · "}
          Auth is optional while{" "}
          <code className="text-xs">AUTH_ENABLED=false</code>
        </p>
      </div>
    </main>
  );
}
