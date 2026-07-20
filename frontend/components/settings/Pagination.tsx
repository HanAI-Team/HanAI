'use client'

interface PaginationProps {
  page: number
  totalPages: number
  totalCount: number
  onPageChange: (page: number) => void
  itemLabel?: string
}

function getPageNumbers(current: number, total: number): (number | '...')[] {
  const pages = new Set<number>()
  pages.add(1)
  pages.add(total)
  for (let i = current - 2; i <= current + 2; i++) {
    if (i >= 1 && i <= total) pages.add(i)
  }
  const sorted = Array.from(pages).sort((a, b) => a - b)
  const result: (number | '...')[] = []
  let prev = 0
  for (const p of sorted) {
    if (prev && p - prev > 1) result.push('...')
    result.push(p)
    prev = p
  }
  return result
}

export default function Pagination({ page, totalPages, totalCount, onPageChange, itemLabel = '건' }: PaginationProps) {
  if (totalPages <= 1) return null

  return (
    <div className="flex items-center justify-center gap-3 py-4 flex-wrap">
      <button
        onClick={() => onPageChange(Math.max(1, page - 1))}
        disabled={page === 1}
        className="px-3 py-1.5 text-xs rounded-md border border-border text-subtext hover:text-text hover:border-text transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        &lt; 이전
      </button>
      {getPageNumbers(page, totalPages).map((p, i) =>
        p === '...' ? (
          <span key={`ellipsis-${i}`} className="px-1.5 text-xs text-subtext">
            ...
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={`px-2.5 py-1.5 text-xs rounded-md transition-colors ${
              p === page ? 'bg-[#EF6600] text-white' : 'border border-border text-subtext hover:text-text'
            }`}
          >
            {p}
          </button>
        )
      )}
      <button
        onClick={() => onPageChange(Math.min(totalPages, page + 1))}
        disabled={page === totalPages}
        className="px-3 py-1.5 text-xs rounded-md border border-border text-subtext hover:text-text hover:border-text transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        다음 &gt;
      </button>
      <span className="text-xs text-subtext ml-2">총 {totalCount}{itemLabel}</span>
    </div>
  )
}
