import { useState } from 'react'
import { api } from '../../api/client'
import { toast } from '../../stores/toastStore'

export interface ComposeSeed {
  accountId: string
  to: string
  cc?: string
  subject: string
  body?: string
  replyToId?: string
}

export default function ComposePanel({
  seed,
  onClose,
  onSent,
}: {
  seed: ComposeSeed
  onClose: () => void
  onSent?: () => void
}) {
  const [to, setTo] = useState(seed.to)
  const [cc, setCc] = useState(seed.cc ?? '')
  const [subject, setSubject] = useState(seed.subject)
  const [body, setBody] = useState(seed.body ?? '')
  const [sending, setSending] = useState(false)

  const parseAddrs = (s: string) =>
    s.split(/[,;]/).map((a) => a.trim()).filter(Boolean)

  const send = async () => {
    setSending(true)
    try {
      await api.post('/api/emails/send', {
        account_id: seed.accountId,
        to: parseAddrs(to),
        cc: parseAddrs(cc),
        bcc: [],
        subject,
        body,
        reply_to_id: seed.replyToId ?? null,
      })
      toast.success('Email sent')
      onSent?.()
      onClose()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to send')
    } finally {
      setSending(false)
    }
  }

  const input =
    'w-full border-b border-divider bg-transparent px-3 py-2 text-body text-primary outline-none placeholder:text-muted focus:border-accent'

  return (
    <div className="animate-slide-up absolute inset-x-0 bottom-0 z-10 border-t border-divider bg-panel shadow-2xl">
      <div className="flex items-center justify-between border-b border-divider px-4 py-2">
        <span className="text-body font-medium text-primary">New message</span>
        <button onClick={onClose} className="rounded px-2 text-muted hover:text-primary">
          ×
        </button>
      </div>
      <input className={input} placeholder="To" value={to} onChange={(e) => setTo(e.target.value)} />
      <input className={input} placeholder="Cc" value={cc} onChange={(e) => setCc(e.target.value)} />
      <input
        className={input}
        placeholder="Subject"
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
      />
      <textarea
        className="h-40 w-full resize-none bg-transparent px-3 py-2 text-body text-primary outline-none placeholder:text-muted"
        placeholder="Write your message…"
        value={body}
        onChange={(e) => setBody(e.target.value)}
      />
      <div className="flex justify-end gap-2 border-t border-divider px-4 py-2">
        <button onClick={onClose} className="rounded-lg px-4 py-1.5 text-body text-muted hover:text-primary">
          Discard
        </button>
        <button
          onClick={send}
          disabled={sending || !to.trim()}
          className="btn-primary px-4 py-1.5"
        >
          {sending ? 'Sending…' : 'Send'}
        </button>
      </div>
    </div>
  )
}
