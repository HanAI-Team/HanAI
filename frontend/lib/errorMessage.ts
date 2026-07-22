export function parseErrorDetail(detail: unknown): string | null {
  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object' && typeof (item as any).msg === 'string') {
          return (item as any).msg.replace(/^Value error,\s*/, '')
        }
        return null
      })
      .filter((m): m is string => !!m)
    if (messages.length > 0) return messages.join(' / ')
  }

  return null
}
