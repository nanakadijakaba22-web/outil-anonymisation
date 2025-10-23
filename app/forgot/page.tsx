"use client";
import { useState } from "react";
import Link from "next/link";

export default function ForgotPage() {
  const [email, setEmail] = useState("");
  const [info, setInfo] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setErr(null); setInfo(null);
    try {
      const r = await fetch("/api/request-reset", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const j = await r.json();
      setInfo(j.resetUrl ? `Lien de réinitialisation (démo) : ${j.resetUrl}` : "Si un compte existe, un email a été envoyé.");
    } catch { setErr("Erreur, réessayez plus tard."); }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow p-6">
        <div className="text-center mb-4">
          <div className="text-lg font-semibold">Mot de passe oublié</div>
        </div>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="text-sm">Votre email</label>
            <input className="mt-1 w-full h-10 rounded-md border px-3" type="email"
                   value={email} onChange={(e)=>setEmail(e.target.value)} required />
          </div>
          {err &&  <div className="text-sm text-red-600 bg-red-50 border border-red-100 p-2 rounded">{err}</div>}
          {info && <div className="text-xs text-gray-700 bg-gray-50 border border-gray-200 p-2 rounded break-all">{info}</div>}
          <button className="w-full h-10 rounded-md bg-blue-600 text-white hover:bg-blue-600/90">Envoyer le lien</button>
        </form>
        <div className="text-sm mt-3">
          <Link href="/login" className="text-gray-700 hover:underline">Retour à la connexion</Link>
        </div>
      </div>
    </div>
  );
}
