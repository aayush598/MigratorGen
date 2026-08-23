import { createAuthClient } from "better-auth/react";

const baseURL = process.env.NEXT_PUBLIC_APP_URL || "https://migrator-gen.vercel.app";

export const authClient = createAuthClient({ baseURL });

export const { signIn, signUp, signOut, useSession } = authClient;

export async function requestPasswordReset(email: string) {
  const res = await fetch(`${baseURL}/request-password-reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, redirectTo: "/auth/reset-password" }),
  });
  return res.json();
}

export async function resetPassword(newPassword: string, token: string) {
  const res = await fetch(`${baseURL}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ newPassword, token }),
  });
  return res.json();
}
