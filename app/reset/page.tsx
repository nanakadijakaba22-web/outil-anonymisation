"use client";
import { useSearchParams, useRouter } from "next/navigation";
import { useState } from "react";
import Link from "next/link";

export default function ResetPage() {
  const token = useSearchParams().get("token") || "";
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setErr(null); setOk(null);
    try {
      const r = await fetch("/api/reset", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      const j = await r.json();
      if (!j.ok) throw new Error(j.error || "Erreur");
      setOk("Mot de passe mis à jour. Vous pouvez vous connecter.");
      setTimeout(()=>router.push("/login"), 900);
    } catch (e: any) { setErr(e.message); }
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow p-6 text-sm">
          Lien invalide. <Link href="/forgot" className="text-blue-600">Redemander</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow p-6">
        <div className="text-center mb-4">
          <div className="text-lg font-semibold">Réinitialiser le mot de passe</div>
        </div>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="text-sm">Nouveau mot de passe (≥ 6)</label>
            <input className="mt-1 w-full h-10 rounded-md border px-3" type="password"
                   value={password} onChange={(e)=>setPassword(e.target.value)} required minLength={6} />
          </div>
          {err && <div className="text-sm text-red-600 bg-red-50 border border-red-100 p-2 rounded">{err}</div>}
          {ok  && <div className="text-sm text-green-700 bg-green-50 border border-green-100 p-2 rounded">{ok}</div>}
          <button className="w-full h-10 rounded-md bg-blue-600 text-white hover:bg-blue-600/90">Mettre à jour</button>
        </form>
      </div>
    </div>
  );
}
