import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      <nav className="border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <span className="text-xl font-bold text-brand-700">MigratorGen</span>
          <div className="flex items-center gap-4">
            <Link href="/auth/login" className="text-gray-600 hover:text-gray-900 text-sm font-medium">Sign in</Link>
            <Link href="/auth/register" className="bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-brand-700">Get started</Link>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center max-w-3xl mx-auto">
          <h1 className="text-5xl font-bold text-gray-900 tracking-tight">
            Migrate Python code<br />
            <span className="text-brand-600">automatically</span>
          </h1>
          <p className="mt-6 text-lg text-gray-600 max-w-2xl mx-auto">
            Parse changelogs into machine-executable rules. AST-accurate transformations.
            Transaction-safe with rollback. Parallel execution for large codebases.
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <Link href="/auth/register" className="bg-brand-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-brand-700 text-lg">
              Start for free
            </Link>
            <Link href="/dashboard" className="border border-gray-300 text-gray-700 px-6 py-3 rounded-lg font-medium hover:bg-gray-50 text-lg">
              View demo
            </Link>
          </div>
        </div>

        <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            { title: "Changelog → Rules", desc: "Parse any changelog format into structured, machine-executable migration rules." },
            { title: "AST-Accurate", desc: "LibCST-powered transformations that preserve formatting, comments, and structure." },
            { title: "Transaction-Safe", desc: "Atomic migrations with checkpoint-based rollback. Never lose your code." },
          ].map((f) => (
            <div key={f.title} className="p-6 border border-gray-200 rounded-xl">
              <h3 className="text-lg font-semibold text-gray-900">{f.title}</h3>
              <p className="mt-2 text-gray-600">{f.desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-20">
          <h2 className="text-2xl font-bold text-center text-gray-900 mb-8">Works with your tools</h2>
          <div className="flex items-center justify-center gap-8 text-gray-500">
            <span className="text-sm font-medium">CLI</span>
            <span className="text-sm font-medium">REST API</span>
            <span className="text-sm font-medium">MCP Server</span>
            <span className="text-sm font-medium">AI Agents</span>
            <span className="text-sm font-medium">CI/CD</span>
          </div>
        </div>
      </main>
    </div>
  );
}
