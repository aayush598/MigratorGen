import { NextRequest, NextResponse } from "next/server";
import { getSessionCookie } from "better-auth/cookies";

const protectedPaths = ["/dashboard", "/migrations", "/libraries", "/api-keys", "/settings", "/billing", "/rules"];
const authPaths = ["/auth/login", "/auth/register"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const sessionCookie = getSessionCookie(request);

  const isProtected = protectedPaths.some((path) => pathname.startsWith(path));
  const isAuthPath = authPaths.some((path) => pathname.startsWith(path));

  if (isProtected && !sessionCookie) {
    return NextResponse.redirect(new URL("/auth/login", request.url));
  }

  if (isAuthPath && sessionCookie) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|api/auth|favicon.ico|.*\\.).*)"],
};
