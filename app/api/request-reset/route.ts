import { NextResponse } from "next/server";
import { authStore } from "@/app/lib/authStore";

export async function POST(req: Request) {
  try {
    const { email } = await req.json();
    let token = "";
    try { token = await authStore.createResetToken(email, 30); } catch {}
    const url = token ? `${process.env.NEXT_PUBLIC_BASE_URL ?? ""}/reset?token=${token}` : null;
    return NextResponse.json({ ok: true, resetUrl: url });
  } catch {
    return NextResponse.json({ ok: true });
  }
}
