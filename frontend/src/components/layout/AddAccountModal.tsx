import { useState } from 'react'
import { api, getToken } from '../../api/client'
import { useAccountsStore } from '../../stores/accountsStore'
import { toast } from '../../stores/toastStore'

const OAUTH_PROVIDERS = [
  { id: 'gmail', label: 'Gmail', color: '#EA4335', hint: 'Sign in with Google' },
  { id: 'outlook', label: 'Outlook', color: '#0078D4', hint: 'Sign in with Microsoft' },
]

export default function AddAccountModal({ onClose }: { onClose: () => void }) {
  const [mode, setMode] = useState<'pick' | 'imap'>('pick')
  const [form, setForm] = useState({
    email_address: '',
    imap_host: '',
    imap_port: 993,
    imap_username: '',
    imap_password: '',
    smtp_host: '',
    smtp_port: 587,
  })
  const [saving, setSaving] = useState(false)
  const refreshAll = useAccountsStore((s) => s.refreshAll)

  const startOAuth = (provider: string) => {
    window.location.href = `/api/accounts/oauth/${provider}/start?token=${getToken()}`
  }

  const presetYahoo = () => {
    setForm((f) => ({
      ...f,
      imap_host: 'imap.mail.yahoo.com',
      smtp_host: 'smtp.mail.yahoo.com',
      imap_port: 993,
      smtp_port: 587,
    }))
    setMode('imap')
  }

  const submitImap = async () => {
    setSaving(true)
    try {
      await api.post('/api/accounts/imap', {
        ...form,
        imap_username: form.imap_username || form.email_address,
      })
      toast.success('Account connected — first sync started')
      await refreshAll()
      onClose()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to connect account')
    } finally {
      setSaving(false)
    }
  }

  const input =
    'input-base px-3 py-2'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="max-h-full w-full max-w-md animate-scale-in overflow-y-auto rounded-xl border border-divider bg-panel p-6 shadow-card"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 text-head font-semibold text-primary">Add email account</h2>

        {mode === 'pick' ? (
          <div className="space-y-2">
            {OAUTH_PROVIDERS.map((p) => (
              <button
                key={p.id}
                onClick={() => startOAuth(p.id)}
                className="flex w-full items-center gap-3 rounded-lg border border-divider px-4 py-3 text-left hover:bg-surface"
              >
                <span
                  className="flex h-7 w-7 items-center justify-center rounded font-bold text-white"
                  style={{ backgroundColor: p.color }}
                >
                  {p.label[0]}
                </span>
                <span>
                  <span className="block text-body font-medium text-primary">{p.label}</span>
                  <span className="block text-caption text-muted">{p.hint}</span>
                </span>
              </button>
            ))}
            <button
              onClick={presetYahoo}
              className="flex w-full items-center gap-3 rounded-lg border border-divider px-4 py-3 text-left hover:bg-surface"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded bg-yahoo font-bold text-white">
                Y
              </span>
              <span>
                <span className="block text-body font-medium text-primary">Yahoo</span>
                <span className="block text-caption text-muted">
                  Connect with an app password
                </span>
              </span>
            </button>
            <button
              onClick={() => setMode('imap')}
              className="flex w-full items-center gap-3 rounded-lg border border-divider px-4 py-3 text-left hover:bg-surface"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded bg-imap font-bold text-white">
                @
              </span>
              <span>
                <span className="block text-body font-medium text-primary">Other (IMAP)</span>
                <span className="block text-caption text-muted">Manual server settings</span>
              </span>
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <input
              className={input}
              placeholder="Email address"
              value={form.email_address}
              onChange={(e) => setForm({ ...form, email_address: e.target.value })}
            />
            <div className="flex gap-2">
              <input
                className={input}
                placeholder="IMAP host"
                value={form.imap_host}
                onChange={(e) => setForm({ ...form, imap_host: e.target.value })}
              />
              <input
                className={`${input} w-24`}
                type="number"
                value={form.imap_port}
                onChange={(e) => setForm({ ...form, imap_port: +e.target.value })}
              />
            </div>
            <input
              className={input}
              placeholder="Username (defaults to email)"
              value={form.imap_username}
              onChange={(e) => setForm({ ...form, imap_username: e.target.value })}
            />
            <input
              className={input}
              type="password"
              placeholder="Password / app password"
              value={form.imap_password}
              onChange={(e) => setForm({ ...form, imap_password: e.target.value })}
            />
            <div className="flex gap-2">
              <input
                className={input}
                placeholder="SMTP host (for sending)"
                value={form.smtp_host}
                onChange={(e) => setForm({ ...form, smtp_host: e.target.value })}
              />
              <input
                className={`${input} w-24`}
                type="number"
                value={form.smtp_port}
                onChange={(e) => setForm({ ...form, smtp_port: +e.target.value })}
              />
            </div>
            <div className="flex justify-between pt-2">
              <button className="text-body text-muted hover:text-primary" onClick={() => setMode('pick')}>
                ← Back
              </button>
              <button
                disabled={saving || !form.email_address || !form.imap_host || !form.imap_password}
                onClick={submitImap}
                className="btn-primary px-4 py-2"
              >
                {saving ? 'Connecting…' : 'Connect'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
