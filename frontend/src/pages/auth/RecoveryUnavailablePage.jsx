import { Link } from 'react-router-dom'
export default function RecoveryUnavailablePage() {
  return <section className="mx-auto max-w-md space-y-4 p-8"><h1 className="text-2xl font-bold">Password recovery unavailable</h1><p>Self-service password recovery is not available. Contact your deployment administrator for account access assistance.</p><Link to="/login" className="underline">Return to sign in</Link></section>
}
