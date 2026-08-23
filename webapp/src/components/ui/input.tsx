"use client";

import { forwardRef } from "react";
import { cn } from "@/lib/utils";

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement> & { error?: string }>(
  ({ className, error, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus:outline-none",
        error ? "border-red-300 focus:border-red-400" : "border-slate-200 focus:border-slate-400",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement> & { error?: string }
>(({ className, error, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "code-input w-full rounded-lg border bg-white px-3 py-2 text-slate-900 placeholder:text-slate-400 transition-colors focus:outline-none",
      error ? "border-red-300 focus:border-red-400" : "border-slate-200 focus:border-slate-400",
      className,
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";

export const Select = forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement> & { error?: string }
>(({ className, error, children, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "w-full appearance-none rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 transition-colors focus:outline-none",
      error ? "border-red-300 focus:border-red-400" : "border-slate-200 focus:border-slate-400",
      className,
    )}
    {...props}
  >
    {children}
  </select>
));
Select.displayName = "Select";

export function Label({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 block text-xs font-medium text-slate-600">
      {children}
    </label>
  );
}

export function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-xs text-red-500">{message}</p>;
}
