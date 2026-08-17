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
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Billing</h1>
        <p className="text-sm text-gray-500 mt-1">Choose the plan that fits your needs</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {PLANS.map((plan) => (
          <div key={plan.name} className={`bg-white rounded-xl border p-6 flex flex-col ${
            plan.highlight ? "border-blue-300 ring-1 ring-blue-200" : "border-gray-200"
          }`}>
            {plan.highlight && (
              <span className="text-xs font-medium bg-blue-600 text-white px-2.5 py-0.5 rounded-full self-start mb-3">Most popular</span>
            )}
            <h3 className="text-lg font-semibold text-gray-900">{plan.name}</h3>
            <div className="mt-2 mb-4">
              <span className="text-3xl font-bold text-gray-900">{plan.price}</span>
              {plan.period && <span className="text-sm text-gray-500 ml-1">{plan.period}</span>}
            </div>
            <ul className="space-y-2.5 mb-6 flex-1">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
                  <svg className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  {f}
                </li>
              ))}
            </ul>
            {plan.current ? (
              <div className="text-center py-2.5 rounded-lg bg-gray-50 text-sm font-medium text-gray-500 border border-gray-200">Current plan</div>
            ) : plan.highlight ? (
              <button className="text-center py-2.5 rounded-lg bg-blue-600 text-sm font-medium text-white hover:bg-blue-700 transition-colors">
                Upgrade to Pro
              </button>
            ) : (
              <button className="text-center py-2.5 rounded-lg border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
                Contact sales
              </button>
            )}
          </div>
        ))}
      </div>

      {/* FAQ */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Frequently asked questions</h2>
        <div className="space-y-4">
          {[
            { q: "Can I switch plans at any time?", a: "Yes, you can upgrade or downgrade at any time. Changes take effect immediately." },
            { q: "What payment methods do you accept?", a: "We accept all major credit cards, and wire transfer for Enterprise plans." },
            { q: "Is there a free trial for Pro?", a: "Yes, Pro comes with a 14-day free trial. No credit card required." },
          ].map((faq) => (
            <div key={faq.q} className="p-4 rounded-lg bg-gray-50">
              <p className="text-sm font-medium text-gray-900">{faq.q}</p>
              <p className="text-sm text-gray-500 mt-1">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
