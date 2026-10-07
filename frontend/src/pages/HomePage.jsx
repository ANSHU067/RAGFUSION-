import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowRight, Check, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ComparisonStats, FeaturesAndBento, FinalCta, ProductPreview, TechCloud, UseCasesPricingFaq, WorkflowPipeline } from '@/components/common/LandingSections'
import { PricingSection } from '@/components/landing/PricingSection'

const HeroScene = lazy(() => import('../components/common/HeroScene'))

const sourceTypes = [
  { icon: '📄', label: 'Documents' },
  { icon: '▶️', label: 'Videos' },
]

export default function HomePage() {
  const [inView, setInView] = useState(true)
  const heroRef = useRef(null)

  useEffect(() => {
    const hero = heroRef.current
    if (!hero) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        setInView(entry.isIntersecting)
      },
      { threshold: 0.05, rootMargin: '0px' }
    )

    observer.observe(hero)
    return () => observer.disconnect()
  }, [])

  return (
    <div id="top" className="overflow-hidden">
      <section 
        ref={heroRef}
        className="relative section pt-14 sm:pt-20 lg:pt-28 min-h-screen flex items-center"
        aria-label="Hero"
      >
        <div className="container-wide">
          <div className="grid items-start gap-12 lg:grid-cols-[1.1fr_0.9fr]">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="relative z-10 pt-4 lg:pt-12"
            >
              <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary">
                <Sparkles className="size-3.5" />
                RAGFUSION AI, reimagined for teams
              </div>
              <h1 className="heading-1 mt-6 max-w-3xl text-balance">
                Make every source <span className="text-primary">instantly useful.</span>
              </h1>
              <p className="body-lg mt-6 max-w-2xl">
                RAGFUSION turns documents and videos into a trusted AI workspace where clear, source-grounded answers are always one question away.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Button size="lg" asChild>
                  <Link to="/signup">Build your workspace <ArrowRight aria-hidden="true" /></Link>
                </Button>
                <Button size="lg" variant="outline" asChild>
                  <a href="#product">Explore the product</a>
                </Button>
              </div>
              <div className="mt-9 flex flex-wrap gap-x-5 gap-y-3 text-sm text-muted-foreground">
                {[
                  'Citations by default',
                  'Your sources stay in context',
                  'Ready for team workflows',
                ].map((item) => (
                  <span key={item} className="flex items-center gap-2">
                    <Check className="size-4 text-primary" />
                    {item}
                  </span>
                ))}
              </div>
              <div className="mt-10 flex items-center gap-4 text-sm text-muted-foreground">
                {sourceTypes.map((item) => (
                  <span key={item.label} className="flex items-center gap-1.5">
                    <span className="text-lg">{item.icon}</span>
                    {item.label}
                  </span>
                ))}
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: inView ? 1 : 0, scale: 1 }}
              transition={{ delay: 0.15, duration: 0.7 }}
              className="relative h-[55vh] min-h-[400px] max-h-[600px] w-full"
            >
              <Suspense fallback={<div className="h-full w-full" aria-label="Loading knowledge core" />}>
                <HeroScene inView={inView} className="h-full w-full" />
              </Suspense>
            </motion.div>
          </div>
        </div>

        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent pointer-events-none" aria-hidden="true" />
      </section>

      <TechCloud />
      <ProductPreview />
      <FeaturesAndBento />
      <WorkflowPipeline />
      <ComparisonStats />
      <UseCasesPricingFaq />
      <PricingSection />
      <FinalCta />
    </div>
  )
}
