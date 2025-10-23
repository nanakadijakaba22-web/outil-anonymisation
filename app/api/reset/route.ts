import { NextResponse } from "next/server";
import { authStore } from "@/app/lib/authStore";

export async function POST(req: Request) {
  try {
    const { token, password } = await req.json();
    await authStore.resetPassword(token, password);
    return NextResponse.json({ ok: true });
  } catch (e: any) {
    return NextResponse.json({ ok: false, error: e.message || "Erreur" }, { status: 400 });
  }
}
