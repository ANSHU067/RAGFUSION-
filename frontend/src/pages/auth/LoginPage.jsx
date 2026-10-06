import { RecoveryUnavailable } from '@/components/forms/RecoveryUnavailable'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, LockKeyhole, Loader2, AlertCircle, CheckCircle } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { loginSchema } from '@/lib/validations'
import { useAuth } from '@/context/AuthContext'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [error, setError] = useState('')

  const savedEmail = localStorage.getItem('remember_email') || ''

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: savedEmail,
      password: '',
      remember: !!savedEmail,
    },
  })

  const onSubmit = async (data) => {
    setError('')

    const result = await login({
      email: data.email,
      password: data.password,
    })

    if (result.success) {
      const { user } = result
      if (data.remember) {
        localStorage.setItem('remember_email', data.email)
      } else {
        localStorage.removeItem('remember_email')
      }

      toast.success('Welcome back!', {
        description: `Signed in as ${user.email}`,
        icon: <CheckCircle className="size-4" />,
      })

      navigate('/dashboard')
      return
    }

    setError(result.error)
    toast.error('Sign in failed', {
      description: result.error,
      icon: <AlertCircle className="size-4" />,
    })
  }

  return (
    <section className="mx-auto flex min-h-[calc(100vh-15rem)] max-w-md items-center py-10">
      <div className="w-full rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 w-fit rounded-xl bg-primary/10 p-3 text-primary">
            <LockKeyhole className="size-6" />
          </div>
          <h1 className="text-2xl font-bold">Welcome back</h1>
          <p className="mt-2 text-sm text-muted-foreground">Sign in to continue to your knowledge workspace.</p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit(onSubmit)}>
          <div className="space-y-2">
            <label htmlFor="email" className="block text-sm font-medium">
              Email
            </label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              {...register('email')}
              disabled={isSubmitting}
              aria-invalid={errors.email ? 'true' : 'false'}
              aria-describedby={errors.email ? 'email-error' : undefined}
            />
            {errors.email && (
              <p id="email-error" className="text-sm text-destructive" role="alert">
                {errors.email.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <label htmlFor="password" className="block text-sm font-medium">
              Password
            </label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="Enter your password"
              {...register('password')}
              disabled={isSubmitting}
              aria-invalid={errors.password ? 'true' : 'false'}
              aria-describedby={errors.password ? 'password-error' : undefined}
            />
            {errors.password && (
              <p id="password-error" className="text-sm text-destructive" role="alert">
                {errors.password.message}
              </p>
            )}
          </div>

          <div className="flex items-center justify-between text-sm">
            <label className="flex items-center gap-2 text-muted-foreground">
              <input
                type="checkbox"
                {...register('remember')}
                className="size-4 rounded border-input accent-primary"
              />
              Remember me
            </label>
            <RecoveryUnavailable />
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive" role="alert">
              <AlertCircle className="size-4 flex-0" />
              {error}
            </div>
          )}

          <Button className="w-full" type="submit" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Signing in...
              </>
            ) : (
              <>
                Sign in
                <ArrowRight className="ml-2 size-4" aria-hidden="true" />
              </>
            )}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          New to RAGFUSION? <Link className="link" to="/signup">Create an account</Link>
        </p>
      </div>
    </section>
  )
}
