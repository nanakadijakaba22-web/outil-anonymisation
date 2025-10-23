"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Link from "next/link";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingGoogle, setLoadingGoogle] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null); setLoading(true);
    try {
      const r = await fetch("/api/login", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const j = await r.json();
      if (!j.ok) throw new Error(j.error || "Identifiants invalides");
      router.push("/studio");
    } catch (e: any) {
      setErr(e.message);
    } finally { setLoading(false); }
  }

  async function onLoginWithGoogle() {
    setLoadingGoogle(true);
    // window.location.href = "/api/auth/google"; // quand tu brancheras OAuth
    setTimeout(()=>setLoadingGoogle(false), 800);
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,rgba(14,165,233,.08),transparent_50%),radial-gradient(ellipse_at_bottom,rgba(99,102,241,.08),transparent_45%)]">
      <div className="mx-auto flex min-h-screen max-w-6xl items-center justify-center px-4">
        <div className="grid w-full grid-cols-1 overflow-hidden rounded-3xl border bg-white shadow-xl md:grid-cols-2">
          <div className="relative hidden bg-gradient-to-br from-brand-600 to-indigo-600 p-10 text-white md:block">
            <div className="flex items-center gap-3">
              <img src="/logo.svg" alt="AnonyTool" className="h-9 w-9 rounded-md bg-white/10 p-1.5" />
              <div className="text-lg font-semibold tracking-tight">AnonyTool</div>
            </div>
            <div className="mt-16 space-y-4">
              <h1 className="text-3xl font-bold leading-snug">
                Studio d’anonymisation<br/>conforme <span className="text-white/90">Loi&nbsp;25</span>
              </h1>
              <p className="max-w-sm text-white/80">
                k-anonymat, l-diversity, t-closeness et confidentialité différentielle.
              </p>
            </div>
            <div className="absolute inset-x-0 bottom-0 p-10 text-xs text-white/70">
              © {new Date().getFullYear()} AnonyTool
            </div>
          </div>

          <div className="p-8 md:p-12">
            <div className="mb-8 flex items-center gap-3 md:hidden">
              <img src="/logo.svg" alt="AnonyTool" className="h-8 w-8 rounded-md bg-gray-100 p-1.5" />
              <div className="text-base font-semibold tracking-tight">AnonyTool</div>
            </div>

            <div className="mb-6">
              <h2 className="text-xl font-semibold tracking-tight">Se connecter</h2>
              <p className="mt-1 text-sm text-gray-500">Accédez au studio d’anonymisation.</p>
            </div>

            <form onSubmit={onSubmit} className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700">Email</label>
                <input className="mt-1 w-full h-11 rounded-lg border px-3 outline-none transition focus:ring-2 focus:ring-brand-600/30 focus:border-brand-600"
                  type="email" placeholder="prenom.nom@entreprise.com" value={email} onChange={e=>setEmail(e.target.value)} required />
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700">Mot de passe</label>
                <div className="mt-1 flex h-11 items-center rounded-lg border px-3 focus-within:ring-2 focus-within:ring-brand-600/30 focus-within:border-brand-600">
                  <input className="h-full w-full outline-none" type={showPw ? "text" : "password"}
                    placeholder="••••••••" value={password} onChange={e=>setPassword(e.target.value)} required minLength={6} />
                  <button type="button" onClick={()=>setShowPw(s=>!s)} className="text-xs text-gray-500 hover:text-gray-700">
                    {showPw ? "Masquer" : "Afficher"}
                  </button>
                </div>
                <div className="mt-2 text-right">
                  <Link href="/forgot" className="text-sm text-brand-600 hover:underline">Mot de passe oublié ?</Link>
                </div>
              </div>

              {err && <div className="rounded-lg border border-red-100 bg-red-50 p-2 text-sm text-red-700">{err}</div>}

              <button disabled={loading}
                className="flex h-11 w-full items-center justify-center rounded-lg bg-brand-600 font-medium text-white shadow-sm transition hover:bg-brand-600/95 disabled:opacity-60">
                {loading ? "Connexion…" : "Se connecter"}
              </button>

              <div className="relative py-2 text-center text-xs text-gray-400">
                <span className="bg-white px-2">ou</span>
                <div className="absolute inset-x-0 top-1/2 -z-10 h-px -translate-y-1/2 bg-gray-200" />
              </div>

              <button type="button" onClick={onLoginWithGoogle}
                className="flex h-11 w-full items-center justify-center gap-2 rounded-lg border bg-white font-medium text-gray-700 transition hover:bg-gray-50 disabled:opacity-60"
                disabled={loadingGoogle}>
                {/* icône Google simple */}
                <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden className="-ml-1">
                  <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 33.7 29.3 37 24 37c-7.2 0-13-5.8-13-13s5.8-13 13-13c3.3 0 6.3 1.3 8.6 3.4l5.7-5.7C34.9 5.1 29.7 3 24 3 12.4 3 3 12.4 3 24s9.4 21 21 21c10.5 0 20-7.6 20-21 0-1.2-.1-2.3-.4-3.5z" />
                  <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16.3 19 13 24 13c3.3 0 6.3 1.3 8.6 3.4l5.7-5.7C34.9 5.1 29.7 3 24 3 15.5 3 8.2 7.9 6.3 14.7z" />
                  <path fill="#4CAF50" d="M24 45c5.2 0 9.9-1.7 13.6-4.7l-6.3-5.2c-2 1.3-4.6 2.1-7.3 2.1-5.3 0-9.7-3.3-11.3-7.9l-6.6 5.1C8.2 40.1 15.5 45 24 45z" />
                  <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-1 3.1-3.7 5.5-7.3 5.5-4.4 0-8-3.6-8-8s3.6-8 8-8c2.2 0 4.2.9 5.6 2.3l6-6C35.5 11.1 30.9 9 26 9 17.8 9 10.9 14.1 8.7 21.3l6.6 5.1C16.9 22.3 20.1 20 24 20c4.4 0 8 3.6 8 8 0 1.3-.3 2.5-.8 3.5H24v8h8c6.8-5 11.6-13 11.6-22.5 0-1.2-.1-2.3-.4-3.5z" />
                </svg>
                {loadingGoogle ? "Connexion…" : "Se connecter avec Google"}
              </button>
            </form>

            <div className="mt-6 text-center text-sm">
              Pas de compte ? <Link href="/register" className="text-brand-600 hover:underline">Créer un compte</Link>
            </div>

            <div className="mt-8 text-center text-xs text-gray-400">
              En vous connectant, vous acceptez nos <a href="#" className="underline">conditions</a> et notre <a href="#" className="underline">politique de confidentialité</a>.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
