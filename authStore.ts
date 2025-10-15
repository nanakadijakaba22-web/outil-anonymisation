// app/lib/authStore.ts
import crypto from "node:crypto";

type User = {
  id: string;
  email: string;
  passHash: string; // sha256
  createdAt: string;
};

type ResetToken = {
  token: string;
  userId: string;
  expireAt: number;
};

class AuthStore {
  users: Map<string, User> = new Map();           // key: email
  tokens: Map<string, ResetToken> = new Map();    // key: token

  sha256(data: string) {
    return crypto.createHash("sha256").update(data).digest("hex");
  }

  async register(email: string, password: string) {
    const e = email.trim().toLowerCase();
    if (this.users.has(e)) throw new Error("Cet email est déjà utilisé.");
    if ((password || "").length < 6) throw new Error("Mot de passe : 6 caractères minimum.");
    const u: User = {
      id: crypto.randomUUID(),
      email: e,
      passHash: this.sha256(password),
      createdAt: new Date().toISOString(),
    };
    this.users.set(e, u);
    return u;
  }

  async login(email: string, password: string) {
    const e = email.trim().toLowerCase();
    const u = this.users.get(e);
    if (!u) throw new Error("Identifiants invalides.");
    if (u.passHash !== this.sha256(password)) throw new Error("Identifiants invalides.");
    return u;
  }

  async createResetToken(email: string, ttlMinutes = 30) {
    const e = email.trim().toLowerCase();
    const u = this.users.get(e);
    if (!u) throw new Error("Si le compte existe, un email a été envoyé.");
    const token = crypto.randomBytes(24).toString("hex");
    this.tokens.set(token, { token, userId: u.id, expireAt: Date.now() + ttlMinutes * 60_000 });
    return token;
  }

  async resetPassword(token: string, newPassword: string) {
    const rec = this.tokens.get(token);
    if (!rec || rec.expireAt < Date.now()) throw new Error("Lien expiré ou invalide.");
    const user = [...this.users.values()].find(u => u.id === rec.userId);
    if (!user) throw new Error("Utilisateur introuvable.");
    if ((newPassword || "").length < 6) throw new Error("Mot de passe : 6 caractères minimum.");
    user.passHash = this.sha256(newPassword);
    this.tokens.delete(token);
    return user;
  }
}

export const authStore = (globalThis as any).__authStore ?? new AuthStore();
(globalThis as any).__authStore = authStore;
