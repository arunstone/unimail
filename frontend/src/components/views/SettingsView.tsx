import { PROVIDER_COLORS } from '../../lib/utils'
import { useAccountsStore } from '../../stores/accountsStore'
import { useAuthStore } from '../../stores/authStore'
import { toast } from '../../stores/toastStore'
import ProviderIcon from '../common/ProviderIcon'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-divider bg-panel shadow-card">
      <h2 className="border-b border-divider px-4 py-2.5 text-caption font-bold uppercase tracking-wide text-muted">
        {title}
      </h2>
      <div className="p-4">{children}</div>
    </section>
  )
}

export default function SettingsView() {
  const { user, logout } = useAuthStore()
  const { accounts, disconnect } = useAccountsStore()

  const handleDisconnect = async (accountId: string, email: string) => {
    if (!window.confirm(`Disconnect ${email}? Its synced emails will be removed.`)) return
    try {
      await disconnect(accountId)
      toast.success('Account disconnected')
    } catch {
      toast.error('Failed to disconnect account')
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
      <h1 className="text-head font-bold text-primary">⚙ Settings</h1>

      <Section title="Profile">
        <div className="flex flex-col gap-1">
          <div className="text-body font-medium text-primary">{user?.name}</div>
          <div className="text-body text-muted">{user?.email}</div>
          <div className="text-caption text-muted">
            {user?.is_verified ? '✓ Email verified' : 'Email not verified'}
          </div>
        </div>
      </Section>

      <Section title="Connected accounts">
        {accounts.length === 0 ? (
          <div className="text-body text-muted">No mail accounts connected.</div>
        ) : (
          <div className="flex flex-col gap-2">
            {accounts.map((account) => (
              <div key={account.id} className="flex items-center gap-3">
                <ProviderIcon provider={account.provider} size={20} />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-body text-primary">{account.email_address}</div>
                  <div className="text-caption" style={{ color: PROVIDER_COLORS[account.provider] }}>
                    {account.provider}
                  </div>
                </div>
                <button
                  onClick={() => handleDisconnect(account.id, account.email_address)}
                  className="rounded border border-divider px-2.5 py-1 text-caption text-muted transition-colors hover:border-red-400 hover:text-red-400"
                >
                  Disconnect
                </button>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Session">
        <button
          onClick={logout}
          className="rounded-lg border border-divider px-4 py-2 text-body font-medium text-muted transition-colors hover:border-red-400 hover:text-red-400"
        >
          Sign out
        </button>
      </Section>
    </div>
  )
}
