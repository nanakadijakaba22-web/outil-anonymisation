// app/api/login/route.ts
import { NextResponse, NextRequest } from "next/server";
import crypto from "node:crypto";
import { authStore } from "../../lib/authStore"; // import RELATIF (même instance)

export async function POST(req: NextRequest) {
  try {
    const { email = "", password = "" } = await req.json();

    // Utilise la bonne méthode du store
    const user = await authStore.login(String(email), String(password));
    // Si ton login() lève déjà une erreur quand c'est invalide, le test suivant est
    // optionnel mais inoffensif :
    if (!user) {
      return NextResponse.json(
        { ok: false, error: "Identifiants invalides." },
        { status: 400 }
      );
    }

    // Génère un jeton de session
    const token = crypto.randomBytes(32).toString("hex");

    // Réponse JSON + Set-Cookie (forme objet, compatible partout)
    const res = NextResponse.json({ ok: true });
    res.cookies.set({
      name: "session",
      value: token,
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production", // true en prod (HTTPS)
      path: "/",
      maxAge: 60 * 60 * 8, // 8h
    });

    // (Optionnel) Si ton authStore gère une table de sessions, tu peux l’enregistrer :
    // if ((authStore as any).sessions) { (authStore as any).sessions.set(token, user.email); }

    return res;
  } catch (err: any) {
    return NextResponse.json(
      { ok: false, error: err?.message ?? "Erreur" },
      { status: 400 }
    );
  }
}
