import { Check, FileText, Globe2, Video } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { SectionHeading } from '@/components/common/LandingSections'

const tiers = [
  {
    name: 'Free',
    price: '$0',
    priceNote: 'forever',
    eyebrow: 'Explore',
    description: 'Try the complete source-grounded workflow in a personal workspace.',
    details: ['Groq chat with MiniLM embeddings', '100 MB maximum per uploaded file', '2 MB maximum per crawled page'],
    cta: 'Create a workspace',
  },
  {
    name: 'Workspace',
    price: '$20',
    priceNote: 'per month',
    eyebrow: 'Current deployment',
    description: 'The full RAGFUSION workspace for teams sharing one secured deployment.',
    details: ['Documents, YouTube transcripts, and websites', 'No per-account source cap is configured', 'Ingestion is protected by a 10 request/minute limit'],
    featured: true,
    cta: 'Open the workspace',
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    priceNote: 'contact us',
    eyebrow: 'Operator configured',
    description: 'Bring RAGFUSION to your environment with limits set by your operator.',
    details: ['Same tenant isolation and source citations', 'Model and storage policy controlled by deployment', 'Custom quotas require an operator configuration'],
    cta: 'Talk to your operator',
  },
]

export function PricingSection() {
  return <section id="pricing" className="section scroll-mt-24">
    <div className="container-wide">
      <SectionHeading eyebrow="Plans and limits" title="Clear capabilities for every workspace." description="RAGFUSION has no hidden subscription meter in this deployment. The limits below are the safeguards enforced by the running application." />
      <div className="mt-10 grid gap-5 lg:grid-cols-3">
        {tiers.map((tier) => <article key={tier.name} className={`relative flex h-full flex-col rounded-2xl border bg-card p-6 shadow-sm ${tier.featured ? 'border-primary ring-1 ring-primary/20' : ''}`}>
          {tier.featured && <span className="absolute right-5 top-5 rounded-full bg-primary/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-primary">AVAILABLE</span>}
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">{tier.eyebrow}</p>
          <h3 className="mt-3 text-2xl font-semibold">{tier.name}</h3>
          <div className="mt-5 flex items-baseline gap-2">
            <span className="text-4xl font-bold tracking-tight">{tier.price}</span>
            <span className="text-sm text-muted-foreground">{tier.priceNote}</span>
          </div>
          <p className="mt-3 min-h-12 text-sm leading-6 text-muted-foreground">{tier.description}</p>
          <div className="my-6 h-px bg-border" />
          <ul className="space-y-3 text-sm">
            {tier.details.map((detail) => <li key={detail} className="flex gap-2"><Check className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" /><span>{detail}</span></li>)}
          </ul>
          <Button className="mt-8" variant={tier.featured ? 'default' : 'outline'} asChild>
            <Link to={tier.name === 'Workspace' ? '/dashboard' : '/signup'}>{tier.cta}</Link>
          </Button>
        </article>)}
      </div>
      <div className="mt-8 grid gap-3 rounded-xl border bg-muted/30 p-5 text-sm text-muted-foreground sm:grid-cols-3">
        <span className="flex items-center gap-2"><FileText className="size-4 text-primary" /> 100 MB per file</span>
        <span className="flex items-center gap-2"><Video className="size-4 text-primary" /> YouTube transcript indexing</span>
        <span className="flex items-center gap-2"><Globe2 className="size-4 text-primary" /> 2 MB per website response</span>
      </div>
    </div>
  </section>
}
