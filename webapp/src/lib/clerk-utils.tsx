"use client";

import { createContext, useContext, type ReactNode } from "react";
import {
  ClerkProvider as RealClerkProvider,
  useUser as realUseUser,
  useClerk as realUseClerk,
} from "@clerk/nextjs";

const hasClerkKey = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

interface AuthContextValue {
  user: ReturnType<typeof realUseUser>["user"];
  isLoaded: boolean;
  isSignedIn: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isLoaded: true,
  isSignedIn: false,
  signOut: async () => {},
});

function ClerkUserProvider({ children }: { children: ReactNode }) {
  const { user, isLoaded, isSignedIn } = realUseUser();
  const { signOut } = realUseClerk();
  return (
    <AuthContext.Provider value={{ user, isLoaded, isSignedIn: !!isSignedIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function ClerkAuthProvider({ children }: { children: ReactNode }) {
  if (!hasClerkKey) {
    return <AuthContext.Provider value={{ user: null, isLoaded: true, isSignedIn: false, signOut: async () => {} }}>{children}</AuthContext.Provider>;
  }
  return (
    <RealClerkProvider>
      <ClerkUserProvider>{children}</ClerkUserProvider>
    </RealClerkProvider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
