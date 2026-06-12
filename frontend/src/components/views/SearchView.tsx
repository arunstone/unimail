import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { truncate } from '../../lib/utils'
import { useTabsStore } from '../../stores/tabsStore'
import EmptyState from '../common/EmptyState'
import { SkeletonList } from '../common/Skeleton'
import EmailRowItem from './EmailRowItem'
import type { EmailRow, FileType } from '../../types'

const RESULT_LIMIT = 100

const FILE_TYPE_CHIPS: { id: FileType | null; label: string }[] = [
  { id: null, label: 'All' },
  { id: 'pdf', label: '📄 PDF' },
  { id: 'image', label: '🖼 Images' },
  { id: 'doc', label: '📃 Word' },
  { id: 'sheet', label: '📊 Sheets' },
  { id: 'archive', label: '🗜 Archives' },
]

export default function SearchView({
  query,
  fileType,
}: {
  query: string
  fileType?: FileType
}) {
  const [emails, setEmails] = useState<EmailRow[] | null>(null)
  const { navigate, openTab } = useTabsStore()

  useEffect(() => {
    setEmails(null)
    const params = new URLSearchParams({
      folder: 'all',
      search: query,
      limit: String(RESULT_LIMIT),
    })
    if (fileType) params.set('file_type', fileType)
    void api.get<EmailRow[]>(`/api/emails?${params}`).then(setEmails)
  }, [query, fileType])

  const openEmail = (email: EmailRow) => {
    openTab({
      kind: 'email',
      key: `email:${email.id}`,
      title: truncate(email.subject || '(no subject)', 30),
      location: { view: 'email', emailId: email.id, subject: email.subject },
      crumbPrefix: [
        {
          label: `Search “${truncate(query, 20)}”`,
          loc: { view: 'search', query, fileType },
        },
      ],
    })
  }

  const setStar = (id: string, starred: boolean) =>
    setEmails((prev) =>
      prev ? prev.map((e) => (e.id === id ? { ...e, is_starred: starred } : e)) : prev,
    )

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 border-b border-divider px-4 py-2.5">
        {FILE_TYPE_CHIPS.map((chip) => {
          const active = (chip.id ?? undefined) === fileType
          return (
            <button
              key={chip.label}
              onClick={() =>
                navigate({ view: 'search', query, fileType: chip.id ?? undefined })
              }
              className={`rounded-full border px-3 py-1 text-caption transition-colors ${
                active
                  ? 'border-accent bg-accent/15 text-primary'
                  : 'border-divider text-muted hover:border-accent hover:text-primary'
              }`}
            >
              {chip.label}
            </button>
          )
        })}
        <span className="ml-auto text-caption text-muted">
          {emails ? `${emails.length}${emails.length === RESULT_LIMIT ? '+' : ''} results` : '…'}
        </span>
      </div>

      {emails === null ? (
        <SkeletonList />
      ) : emails.length === 0 ? (
        <EmptyState
          icon="🔍"
          title="No matches"
          hint={fileType ? 'Try a different file type filter.' : `Nothing matched “${query}”.`}
        />
      ) : (
        <>
          <div className="px-4 py-2 text-caption text-muted">
            Tip: drag a result into the workspace panel on the right to collect it under a label.
          </div>
          {emails.map((email) => (
            <EmailRowItem
              key={email.id}
              email={email}
              onOpen={openEmail}
              onStarChange={setStar}
              showAccount
              draggable
            />
          ))}
        </>
      )}
    </div>
  )
}
