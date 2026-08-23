"use client";

import { useState } from "react";
import { useSession, signOut } from "@/lib/auth-client";
import { useRouter } from "next/navigation";

export default function SettingsPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const [saved, setSaved] = useState(false);

  const handleSignOut = () => {
    signOut({ fetchOptions: { onSuccess: () => router.push("/login") } });
  };

  return (
    <div className="max-w-2xl animate-fade-up">
      <div className="mb-8">
        <h1 className="text-[28px] font-bold text-slate-900 tracking-tight">Settings</h1>
        <p className="text-[14px] text-slate-500 mt-1">Manage your account settings and preferences</p>
      </div>

      <div className="space-y-6">
        {/* Profile */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h2 className="text-[15px] font-semibold text-slate-900 mb-5">Profile</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-[13px] font-medium text-slate-600 mb-1.5">Email</label>
              <input type="email" value={session?.user?.email || ""} disabled
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-[13px] text-slate-400 cursor-not-allowed" />
              <p className="text-[12px] text-slate-400 mt-1">Contact support to change your email</p>
            </div>
            <div>
              <label className="block text-[13px] font-medium text-slate-600 mb-1.5">User ID</label>
              <input type="text" value={session?.user?.id || ""} disabled
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-[13px] text-slate-400 font-mono cursor-not-allowed" />
            </div>
          </div>
        </div>

        {/* Notifications placeholder */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h2 className="text-[15px] font-semibold text-slate-900 mb-5">Notifications</h2>
          <div className="space-y-3">
            {[
              { label: "Migration completed", desc: "Get notified when a migration finishes" },
              { label: "Library updates", desc: "Notify when built-in libraries are updated" },
              { label: "Weekly digest", desc: "Summary of your migration activity" },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <div>
                  <p className="text-[13px] font-semibold text-slate-900">{item.label}</p>
                  <p className="text-[12px] text-slate-400 mt-0.5">{item.desc}</p>
                </div>
                <div className="w-10 h-[22px] bg-slate-200 rounded-full relative cursor-pointer transition-colors hover:bg-slate-300">
                  <div className="w-4 h-4 bg-white rounded-full absolute top-[3px] left-[3px] shadow-sm transition-transform" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sign out */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h2 className="text-[15px] font-semibold text-slate-900 mb-2">Session</h2>
          <p className="text-[13px] text-slate-500 mb-5">Sign out of your account on this device.</p>
          <button onClick={handleSignOut}
            className="bg-red-600 text-white px-5 py-2.5 rounded-xl text-[13px] font-semibold hover:bg-red-700 transition-all flex items-center gap-2 btn-press">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
            </svg>
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
