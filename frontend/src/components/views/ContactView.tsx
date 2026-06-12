import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { truncate } from '../../lib/utils'
import { useAccountsStore } from '../../stores/accountsStore'
import { useTabsStore } from '../../stores/tabsStore'
import Avatar from '../common/Avatar'
import EmptyState from '../common/EmptyState'
import ProviderIcon from '../common/ProviderIcon'
import { SkeletonList } from '../common/Skeleton'
import EmailRowItem from './EmailRowItem'
import type { Contact, ContactSubTab, EmailRow } from '../../types'

const SUB_TABS: { id: ContactSubTab; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'inbox', label: 'Inbox' },
  { id: 'sent', label: 'Sent' },
  { id: 'drafts', label: 'Drafts' },
]

export default function ContactView({
  contactId,
  sub,
}: {
  contactId: string
  sub: ContactSubTab
}) {
  const [contact, setContact] = useState<Contact | null>(null)
  const [emails, setEmails] = useState<EmailRow[] | null>(null)
  const { navigate, openTab, activeTab } = useTabsStore()
  const accounts = useAccountsStore((s) => s.accounts)
  const tab = activeTab()

  useEffect(() => {
    void api.get<Contact>(`/api/contacts/${contactId}`).then(setContact)
  }, [contactId])

  useEffect(() => {
    setEmails(null)
    void api
      .get<EmailRow[]>(`/api/contacts/${contactId}/emails?folder=${sub}&limit=100`)
      .then(setEmails)
  }, [contactId, sub])

  const openEmail = (email: EmailRow) => {
    openTab({
      kind: 'email',
      key: `email:${email.id}`,
      title: truncate(email.subject || '(no subject)', 30),
      location: { view: 'email', emailId: email.id, subject: email.subject },
      crumbPrefix: [
        {
          label: contact?.name || contact?.email || 'Contact',
          loc: { view: 'contact', contactId, sub },
        },
      ],
    })
  }

  const setStar = (id: string, starred: boolean) =>
    setEmails((prev) =>
      prev ? prev.map((e) => (e.id === id ? { ...e, is_starred: starred } : e)) : prev,
    )

  if (!contact) return <SkeletonList rows={3} />

  const sourceAccounts = accounts.filter((a) => contact.account_ids.includes(a.id))

  return (
    <div>
      <div className="border-b border-divider p-6">
        <div className="flex items-center gap-4">
          <Avatar name={contact.name} email={contact.email} size={56} />
          <div className="min-w-0">
            <h2 className="text-head font-semibold text-primary">
              {contact.name || contact.email}
            </h2>
            <div className="font-mono text-body text-muted">{contact.email}</div>
            <div className="mt-1 flex items-center gap-1.5">
              {sourceAccounts.map((a) => (
                <span key={a.id} className="flex items-center gap-1 text-caption text-muted">
                  <ProviderIcon provider={a.provider} size={14} />
                  {a.email_address}
                </span>
              ))}
            </div>
          </div>
          <div className="ml-auto text-right">
            <div className="text-head font-bold text-primary">{contact.email_count}</div>
            <div className="text-caption text-muted">emails</div>
          </div>
        </div>
      </div>

      <div className="flex gap-1 border-b border-divider px-4">
        {SUB_TABS.map((s) => (
          <button
            key={s.id}
            onClick={() => {
              if (s.id !== sub) navigate({ view: 'contact', contactId, sub: s.id })
            }}
            className={`border-b-2 px-4 py-2.5 text-body transition-colors ${
              s.id === sub
                ? 'border-accent font-medium text-primary'
                : 'border-transparent text-muted hover:text-primary'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {emails === null ? (
        <SkeletonList />
      ) : emails.length === 0 ? (
        <EmptyState title="No emails here" hint={`Nothing in ${sub} with ${tab.title}.`} />
      ) : (
        emails.map((email) => (
          <EmailRowItem
            key={email.id}
            email={email}
            onOpen={openEmail}
            onStarChange={setStar}
            showAccount
          />
        ))
      )}
    </div>
  )
}
