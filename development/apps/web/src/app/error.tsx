"use client";

export default function Error({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return <main className="auth-page"><section className="auth-card" role="alert">
    <h1>Learning space unavailable</h1>
    <p>Your catalogue and saved learning could not be loaded. Please try again.</p>
    <button onClick={() => retry()}>Try again</button>
  </section></main>;
}

