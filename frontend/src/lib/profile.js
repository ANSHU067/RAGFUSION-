const colors = {
  slate: 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100',
  indigo: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-100',
  emerald: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-100',
  rose: 'bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-100',
  amber: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100',
}
export const avatarColorClass = (value) => colors[value] || colors.slate
export const initials = (name) => (name || 'User').trim().split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase()
