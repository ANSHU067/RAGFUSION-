import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowRight, Bot, ChevronDown, FileText, Globe2, LockKeyhole, MessageSquareText, Network, ScanText, Search, ShieldCheck, Sparkles, Video } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/context/AuthContext'
import { dashboardApi } from '@/services/dashboard'
import { getApiError, isCanceled } from '@/services/api'

const reveal = { hidden: { opacity: 0, y: 18 }, visible: { opacity: 1, y: 0 } }
const sourceCards = [
  [FileText, 'Documents', 'Upload and index your files.'],
  [Video, 'Videos', 'Explore YouTube transcripts.'],
  [Globe2, 'Websites', 'Index a public webpage.'],
]

export function SectionHeading({ eyebrow, title, description, align = 'center' }) {
  return <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.2 }} variants={reveal} transition={{ duration: 0.45 }} className={`max-w-2xl ${align === 'center' ? 'mx-auto text-center' : ''}`}>
    <p className="text-xs font-semibold tracking-[0.16em] text-primary uppercase">{eyebrow}</p>
    <h2 className="heading-2 mt-3 text-balance">{title}</h2>
    {description && <p className="body mt-4">{description}</p>}
  </motion.div>
}

export function TechCloud() {
  const technologies = ['Groq', 'LangChain', 'ChromaDB', 'PostgreSQL', 'FastAPI', 'React', 'MiniLM', 'Vector Search']
  return <section className="border-y border-border/70 bg-muted/25 py-10"><div className="container-wide"><p className="text-center text-xs font-semibold tracking-[0.16em] text-muted-foreground uppercase">Built for your AI stack</p><div className="mx-auto mt-6 flex max-w-5xl flex-wrap justify-center gap-2.5">{technologies.map((technology, index) => <motion.span key={technology} initial={{ opacity: 0, scale: 0.92 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }} transition={{ delay: index * 0.025 }} className="rounded-full border bg-background px-3.5 py-1.5 text-sm font-medium text-muted-foreground shadow-xs transition-colors hover:border-primary/40 hover:text-foreground">{technology}</motion.span>)}</div></div></section>
}

export function ProductPreview() {
  const { user, loading } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    if (loading || !user?.id) return
    const controller = new AbortController()
    dashboardApi.overview({ signal: controller.signal }).then((result) => {
      if (!controller.signal.aborted) setData(result)
    }).catch((err) => {
      if (!controller.signal.aborted && !isCanceled(err)) setError(getApiError(err, 'Workspace overview unavailable.'))
    })
    return () => controller.abort()
  }, [loading, user?.id])
  return <section id="product" className="section scroll-mt-24"><div className="container-wide">
    <SectionHeading eyebrow="Your workspace" title="A workspace that makes your sources usable." description="Upload, organize, retrieve, and verify answers in one place." />
    {user ? <div className="mt-10 rounded-2xl border bg-card p-6 sm:p-8">
      {error ? <p role="alert">{error}</p> : data ? <div className="grid grid-cols-2 gap-4 md:grid-cols-4">{[['documents', 'Documents'], ['youtube', 'Videos'], ['websites', 'Websites'], ['conversations', 'Conversations']].map(([key, label]) => <div key={key} className="rounded-xl border bg-background p-5"><p className="text-3xl font-semibold">{data.stats[key]}</p><p className="mt-2 text-sm text-muted-foreground">{label}</p></div>)}</div> : <p role="status">Loading your workspace…</p>}
      <Button asChild className="mt-6"><Link to="/dashboard">Open workspace <ArrowRight className="ml-2 size-4" /></Link></Button>
    </div> : <>
      <div className="mt-10 grid gap-5 sm:grid-cols-3">
        {sourceCards.map(([Icon, title, description]) => <article key={title} className="group rounded-2xl border bg-card p-6 shadow-sm transition-all hover:-translate-y-1 hover:border-primary/40 hover:shadow-lg">
          <div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary/15"><Icon className="size-6" aria-hidden="true" /></div>
          <h3 className="mt-5 text-lg font-semibold">{title}</h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
        </article>)}
      </div>
      <div className="mt-8 flex justify-center"><Button size="lg" asChild><Link to="/signup">Try now <ArrowRight className="ml-2 size-4" aria-hidden="true" /></Link></Button></div>
    </>}
  </div></section>
}

const featureItems = [
  [Search, 'Semantic retrieval', 'Find relevant passages within your authorized sources.'],
  [Bot, 'Grounded chat', 'Ask questions with retrieved source material in context.'],
  [ScanText, 'Document ingestion', 'Extract text, create chunks, and index supported files.'],
  [Network, 'Source selection', 'Focus a conversation on an indexed document, video, or website.'],
  [MessageSquareText, 'Citation engine', 'Trace every answer to the passages that support it.'],
  [LockKeyhole, 'Account isolation', 'Keep your sources and conversations scoped to your authenticated account.'],
]

export function FeaturesAndBento() {
  return <><section id="features" className="section scroll-mt-24"><div className="container-wide"><SectionHeading eyebrow="Built for deep work" title="More than a chat window." description="Purpose-built retrieval tools make the quality of your answers visible and repeatable." /><div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-3">{featureItems.map(([Icon, title, description], index) => <motion.article key={title} initial="hidden" whileInView="visible" viewport={{ once: true }} variants={reveal} transition={{ delay: index * 0.06 }} whileHover={{ y: -4 }} className="group rounded-xl border bg-card p-6 shadow-sm transition-shadow hover:shadow-lg"><div className="w-fit rounded-lg bg-primary/10 p-2.5 text-primary transition-transform group-hover:scale-105"><Icon className="size-5" /></div><h3 className="mt-5 font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p></motion.article>)}</div></div></section><section className="section-sm"><div className="container-wide"><SectionHeading eyebrow="Intelligence, composed" title="Every capability has a place." /><div className="mt-10 grid gap-4 md:grid-cols-4"><Bento className="md:col-span-2 md:row-span-2" icon={Network} title="Your sources, together" text="Bring documents, video transcripts, and public webpages into one workspace." visual="graph" /><Bento className="md:col-span-2" icon={Bot} title="Source-grounded conversations" text="Research and synthesis stay grounded in your materials." /><Bento icon={ScanText} title="Document ready" text="Index text from supported files." /><Bento icon={ShieldCheck} title="Private by design" text="Authenticated account boundaries." /><Bento className="md:col-span-2" icon={Search} title="Semantic retrieval" text="Relevant passages from the sources you select." /></div></div></section></>
}

function Bento({ icon: Icon, title, text, className = '', visual }) {
  return <motion.article whileHover={{ y: -3 }} className={`min-h-44 overflow-hidden rounded-2xl border bg-card p-6 shadow-sm ${className}`}><Icon className="size-5 text-primary" /><h3 className="mt-5 text-lg font-semibold">{title}</h3><p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">{text}</p>{visual === 'graph' && <div className="mt-8 flex items-center justify-center gap-3 opacity-80"><span className="size-8 rounded-full border-4 border-primary/30 bg-primary/10" /><span className="h-px w-16 bg-primary/40" /><span className="size-5 rounded-full bg-primary" /><span className="h-px w-16 bg-primary/40" /><span className="size-7 rounded-full border-4 border-primary/30 bg-primary/10" /></div>}</motion.article>
}

export function WorkflowPipeline() {
  const stages = ['Upload', 'Process', 'Chunk', 'Embed', 'Retrieve', 'Generate', 'Ground', 'Cite']
  return <section id="workflow" className="section scroll-mt-24"><div className="container-wide rounded-2xl border bg-muted/30 px-6 py-10 sm:px-10 lg:p-14"><SectionHeading eyebrow="From source to answer" title="A retrieval pipeline designed for confidence." description="RAGFUSION keeps every stage observable—so answers can be faster without becoming less trustworthy." align="left" /><ol className="mt-10 flex snap-x gap-3 overflow-x-auto pb-2">{stages.map((stage, index) => <li key={stage} className="flex min-w-32 snap-start items-center gap-3"><div className="w-full rounded-xl border bg-background p-4"><span className="text-xs font-semibold text-primary">{String(index + 1).padStart(2, '0')}</span><p className="mt-2 text-sm font-semibold">{stage}</p></div>{index < stages.length - 1 && <ArrowRight className="hidden size-4 shrink-0 text-primary/60 xl:block" />}</li>)}</ol></div></section>
}

export function ComparisonStats() {
  return <section className="section-sm"><div className="container-wide"><SectionHeading eyebrow="Why RAGFUSION" title="Designed for work where the source matters." /><div className="mt-8 grid gap-4 sm:grid-cols-3">{[['Sources you control', 'Index your own documents, videos, and public pages.'], ['Conversations you can continue', 'Return to your history and keep asking questions.'], ['Private account boundaries', 'Sources and conversation history stay scoped to the authenticated account.']].map(([title, text]) => <article key={title} className="rounded-xl border bg-card p-6"><h3 className="font-semibold">{title}</h3><p className="mt-2 text-sm text-muted-foreground">{text}</p></article>)}</div></div></section>
}

export function UseCasesPricingFaq() {
  const [open, setOpen] = useState(0)
  const faqs = [['What can I upload?', 'RAGFUSION supports documents, YouTube transcripts, and public webpages. The indexing workflow makes each source searchable and citeable.'], ['How are answers grounded?', 'Retrieved passages are connected to every answer so users can inspect the evidence instead of relying on an opaque response.'], ['Can teams control access?', 'Authenticated users see only their authorized sources and conversation history.']]
  return <><section className="section"><div className="container-wide"><SectionHeading eyebrow="Built for teams" title="Adaptable to every knowledge-heavy workflow." /><div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{['Legal review', 'Healthcare operations', 'Education', 'Research teams', 'Financial analysis', 'Enterprise knowledge'].map((useCase, index) => <motion.div key={useCase} whileHover={{ y: -3 }} className="rounded-xl border bg-card p-5"><span className="text-xs font-semibold text-primary">0{index + 1}</span><h3 className="mt-5 font-semibold">{useCase}</h3><p className="mt-2 text-sm text-muted-foreground">Keep complex source material searchable, traceable, and ready for informed decisions.</p></motion.div>)}</div></div></section><section id="faq" className="section scroll-mt-24"><div className="container-narrow"><SectionHeading eyebrow="Questions, answered" title="Everything you need to know before you begin." /><div className="mt-8 divide-y rounded-xl border bg-card">{faqs.map(([question, answer], index) => <div key={question}><button className="flex w-full items-center justify-between gap-4 px-5 py-5 text-left text-sm font-semibold" aria-expanded={open === index} onClick={() => setOpen(open === index ? -1 : index)}>{question}<ChevronDown className={`size-4 shrink-0 text-primary transition-transform ${open === index ? 'rotate-180' : ''}`} /></button>{open === index && <p className="px-5 pb-5 text-sm leading-6 text-muted-foreground">{answer}</p>}</div>)}</div></div></section></>
}

export function FinalCta() {
  return <section className="pb-10"><div className="container-wide"><div className="relative overflow-hidden rounded-2xl border bg-card px-6 py-14 text-center shadow-lg sm:px-10"><div className="absolute inset-x-1/4 top-0 h-24 bg-primary/10 blur-3xl" aria-hidden="true" /><div className="relative"><Sparkles className="mx-auto size-5 text-primary" /><h2 className="heading-2 mt-4 text-balance">Turn every trusted source into a better answer.</h2><p className="body mx-auto mt-4 max-w-xl">Start building a knowledge workspace your team can verify, trust, and use every day.</p><Button size="lg" className="mt-7" asChild><Link to="/signup">Create your workspace <ArrowRight aria-hidden="true" /></Link></Button></div></div></div></section>
}
