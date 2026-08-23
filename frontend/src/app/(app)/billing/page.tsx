import Link from "next/link";

const PLANS = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    current: true,
    features: ["3 migration libraries", "100 migrations/month", "Community support", "Basic rules"],
  },
  {
    name: "Pro",
    price: "$29",
    period: "/month",
    current: false,
    features: ["Unlimited libraries", "Unlimited migrations", "Priority support", "Advanced rules", "Custom integrations", "API access"],
    highlight: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    current: false,
    features: ["Everything in Pro", "Self-hosted option", "SSO / SAML", "Dedicated support", "Custom SLA", "Audit logs"],
  },
];

export default function BillingPage() {
  return (
    <div className="max-w-4xl mx-auto animate-fade-up">
      <div className="mb-8">
        <h1 className="text-[28px] font-bold text-zinc-100 tracking-tight">Billing</h1>
        <p className="text-[14px] text-zinc-400 mt-1">Choose the plan that fits your needs</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-10">
        {PLANS.map((plan) => (
          <div key={plan.name} className={`bg-[#18181b] rounded-xl border p-6 flex flex-col transition-all ${
            plan.highlight ? "border-blue-500/30 shadow-lg shadow-blue-500/5" : "border-white/10 hover:border-white/20"
          }`}>
            {plan.highlight && (
              <span className="text-[11px] font-bold bg-blue-600 text-white px-2.5 py-0.5 rounded-md self-start mb-3 uppercase tracking-wider">Most popular</span>
            )}
            <h3 className="text-[16px] font-semibold text-zinc-100">{plan.name}</h3>
            <div className="mt-3 mb-5">
              <span className="text-[32px] font-bold text-zinc-100 tracking-tight">{plan.price}</span>
              {plan.period && <span className="text-[13px] text-zinc-500 ml-1">{plan.period}</span>}
            </div>
            <ul className="space-y-3 mb-7 flex-1">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2.5 text-[13px] text-zinc-400">
                  <svg className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                  {f}
                </li>
              ))}
            </ul>
            {plan.current ? (
              <div className="text-center py-3 rounded-lg bg-white/5 text-[13px] font-semibold text-zinc-500 border border-white/10">Current plan</div>
            ) : plan.highlight ? (
              <button className="text-center py-3 rounded-lg bg-blue-600 text-[13px] font-semibold text-white hover:bg-blue-700 transition-all btn-press">
                Upgrade to Pro
              </button>
            ) : (
              <button className="text-center py-3 rounded-lg border border-white/10 text-[13px] font-semibold text-zinc-300 hover:bg-white/5 transition-colors btn-press">
                Contact sales
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="bg-[#18181b] rounded-xl border border-white/10 p-6">
        <h2 className="text-[15px] font-semibold text-zinc-100 mb-5">Frequently asked questions</h2>
        <div className="space-y-4">
          {[
            { q: "Can I switch plans at any time?", a: "Yes, you can upgrade or downgrade at any time. Changes take effect immediately." },
            { q: "What payment methods do you accept?", a: "We accept all major credit cards, and wire transfer for Enterprise plans." },
            { q: "Is there a free trial for Pro?", a: "Yes, Pro comes with a 14-day free trial. No credit card required." },
          ].map((faq) => (
            <div key={faq.q} className="p-4 rounded-lg bg-white/[0.02] border border-white/5">
              <p className="text-[13px] font-semibold text-zinc-100">{faq.q}</p>
              <p className="text-[13px] text-zinc-400 mt-1">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
