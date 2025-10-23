// app/api/register/route.ts
import { NextResponse } from "next/server";
import { authStore } from "../../lib/authStore"; // import RELATIF, pas d'alias

export async function POST(req: Request) {
  try {
    const { email = "", password = "" } = await req.json();
    const u = await authStore.register(String(email), String(password));
    return NextResponse.json({ ok: true, id: u.id });
  } catch (err: any) {
    return NextResponse.json(
      { ok: false, error: err?.message ?? "Erreur" },
      { status: 400 }
    );
  }
}
