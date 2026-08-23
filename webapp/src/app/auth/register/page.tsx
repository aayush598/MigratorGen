"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { signUp } from "@/lib/auth-client";
import { signUpSchema, type SignUpInput } from "@/schemas";
import { Button } from "@/components/ui/button";
import { Input, Label, FieldError } from "@/components/ui/input";

export default function RegisterPage() {
  const router = useRouter();

  const form = useForm<SignUpInput>({
    resolver: zodResolver(signUpSchema),
    defaultValues: { name: "", email: "", password: "", confirmPassword: "" },
  });

  const onSubmit = async (data: SignUpInput) => {
    try {
      const { error: signUpError } = await signUp.email({
        name: data.name,
        email: data.email,
        password: data.password,
      });
      if (signUpError) {
        form.setError("root", { message: signUpError.message || "Could not create account" });
      } else {
        router.push("/dashboard");
      }
    } catch {
      form.setError("root", { message: "Could not create account" });
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#fafafa] px-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <Link href="/" className="mb-6 inline-flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900">
              <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
              </svg>
            </span>
            <span className="text-lg font-semibold text-slate-900">MigratorGen</span>
          </Link>
          <h1 className="text-2xl font-bold text-slate-900">Create your account</h1>
          <p className="mt-1 text-sm text-slate-500">Start migrating in minutes</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <Label htmlFor="name">Name</Label>
              <Input id="name" placeholder="Ada Lovelace" autoComplete="name" {...form.register("name")} />
              <FieldError message={form.formState.errors.name?.message} />
            </div>
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" placeholder="you@company.dev" autoComplete="email" {...form.register("email")} />
              <FieldError message={form.formState.errors.email?.message} />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" placeholder="At least 8 characters" autoComplete="new-password" {...form.register("password")} />
              <FieldError message={form.formState.errors.password?.message} />
            </div>
            <div>
              <Label htmlFor="confirmPassword">Confirm password</Label>
              <Input id="confirmPassword" type="password" placeholder="Repeat your password" autoComplete="new-password" {...form.register("confirmPassword")} />
              <FieldError message={form.formState.errors.confirmPassword?.message} />
            </div>
            {form.formState.errors.root && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{form.formState.errors.root.message}</p>
            )}
            <Button type="submit" className="w-full" loading={form.formState.isSubmitting}>
              Create account
            </Button>
          </form>

          <p className="mt-5 text-center text-xs text-slate-400">
            Already have an account?{" "}
            <Link href="/auth/login" className="font-medium text-slate-700 transition-colors hover:text-slate-900">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
