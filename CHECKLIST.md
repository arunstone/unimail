# Unimail Checklist

## UI polish pass (added + BUILT & DEPLOYED 2026-06-13 — user: "look wise ui ux is not good")
- [x] 1. Theme refresh — blue-tinted dark palette (app #0a0d15…divider #262b3f), accent #5b8cff + accent2 #8b5cf6, bg-accent-gradient, shadow-card/shadow-glow tokens
- [x] 2. Auth pages glow-up — shared AuthShell (ambient glows, glass card, gradient wordmark + ✉ mark); Login/Register/Forgot/Reset/Verify rewritten on it; Login gained "Forgot password?" link
- [x] 3. Email list hierarchy — unread: gradient left bar + accent tint + dot; star fades in on hover (desktop); colored avatars/paperclip already existed
- [x] 4. Left panel — gradient logo, small-caps ACCOUNTS/LABELS headers, rounded pill rows with active shadow (unread badges already existed)
- [x] 5. Tabs & navbar — active tab gets inset accent top bar, inactive tabs lighten on hover; search bar rounded-full with focus ring
- [x] 6. Micro-interactions — global button transitions + :focus-visible ring (index.css @layer base); btn-primary gradient w/ hover-brighten + press-scale; modal scale-in + backdrop blur; skeleton shimmer; toasts with icon chips + slide-in
- [x] 7. Empty states — icon in raised rounded square, fade-up, optional action button prop
- [x] 8. Reading view — bubbles: mine = blue→violet gradient tint + shadow; day separators as pills; iframe email CSS updated to new palette (also LabelTimelineView)
- [x] 9. Shared primitives — src/components/common/ui.tsx (Button/Input/Card/Wordmark) + .btn-primary/.btn-outline/.input-base/.card recipes in index.css; adopted in auth pages, AddAccountModal, ComposePanel, WorkspacePanel, EmailBodyView

## Security hardening (server-wide, added 2026-06-12 session 4)
- [ ] Lock down Portainer — strong unique password at minimum; better: nginx basic auth in front (.htpasswd already exists in nginx container) or SSH-tunnel-only access
- [ ] nginx rate limiting — add `limit_req` zones (strict on login/auth endpoints, mild site-wide) to block brute-force and accidental overload
- [ ] Put Cloudflare (free tier) in front of both domains — DDoS protection + hides the server's real IP
- Skipped by user decision: SSH key hardening / disabling root password login

## Built & deployed 2026-06-12 session 5 (smoke-tested: register/login, labels CRUD, search+file_type, graph, forgot-password 202, ollama embed OK from backend)
- [x] Logout button in left panel — bottom section of LeftPanel, below "+ Add Account"
- [x] Settings icon (⚙) in left panel header → opens Settings tab (profile, connected accounts w/ disconnect, sign out)
- [x] Forgot password / reset via email link (dormant until SMTP configured, like verification; /forgot + /reset pages)
- [x] Longer login sessions — JWT expiry 24h → 720h (30 days)
- [x] Home folder click → per-account breakdown view (BreakdownView; "All accounts" row + per-account rows; breadcrumbs Home › Folder › Account)
- [x] Permanent "+" new-tab button in tab bar (new tabs start at Home, independent history)
- [x] Account badge (provider icon) on email rows in merged inbox / contact / search lists
- [x] Persistent search bar in NavBar on every view → SearchView (folder=all, sender/subject/body)
- [x] Attachment file-type filter (chips on search: PDF/Images/Word/Sheets/Archives; backend ?file_type=)
- [x] Labels workspace "lego panel" (4th panel 20/40/20/20 opens on search; drag results in, reorder, save as label; backend labels + label_emails tables + CRUD)
- [x] Label timeline view — WhatsApp-group style (bubbles left/right, day separators, sender ▶ recipient)
- [x] WhatsApp chat view for individual emails (EmailBodyView → thread bubbles via /api/emails/{id}/thread, subject+counterpart grouping; reply box at bottom)
- [x] Graph view real embeddings via ollama (nomic-embed-text, cached in email_embeddings table, lazy-fills 80/request, TF-IDF fallback)
- [x] Responsive mobile/narrow-window layout (2026-06-13 session 5): below 1024px viewport width (phones, split-screen desktop/mobile) the middle panel goes full-screen; left panel + contacts become slide-in drawers (☰ / 👤 buttons in NavBar) that auto-close on navigation; workspace becomes full-screen overlay; tab × always visible on touch; tap "＋" on rows adds to workspace (drag is desktop-only); AddAccountModal padded + scrollable, z-50. New stores/uiStore.ts. Known touch gaps: drag-reorder of tabs and workspace items.
- [x] Self-hosted backup mail relay (2026-06-12 session 5): `smtp` service in compose (boky/postfix, send-only, internal network); `.env` points SYSTEM_SMTP at it (STARTTLS=false, new config flag); system_mail.py gained Message-ID/Date headers (Gmail rejects without). BLOCKED on SPF record (#5 above) — Gmail hard-bounces unauthenticated senders, so verification/reset emails won't deliver until it's added. Will likely land in spam even then (no DKIM, fresh IP) — user accepted this for a backup.

## Own mail server — BUILT 2026-06-13 as separate project at /opt/mailserver (docker-mailserver v15)
- [x] Server running: mailserver container, ports 25/143/465/587/993, rspamd spam+DKIM, fail2ban, ClamAV off; healthy; IMAP login + local send/receive tested OK. Mailbox: arun@example.com (password in /opt/mailserver/CREDENTIALS.txt, chmod 600). DKIM keys generated (selector `mail`). Temp self-signed TLS cert.
- [x] DNS at Namecheap added by user + verified propagated 2026-07-02: A `mail`, MX `@` prio 10, TXT SPF, TXT `mail._domainkey` (DKIM)
- [ ] USER: set PTR / reverse DNS at your VPS provider panel: YOUR_SERVER_IP → mail.example.com (currently your-vps-hostname — critical for Gmail to accept mail)
- [x] Let's Encrypt cert for mail.example.com issued 2026-07-02 (expires 2026-09-30, auto-renews); compose swapped to SSL_TYPE=letsencrypt; renew cron got --deploy-hook "docker restart mailserver"; IMAPS/SMTPS verified serving LE cert, IMAP login OK
- [ ] USER: add arun@example.com to Unimail via web UI (+ Add Account → Other (IMAP)): IMAP mail.example.com:993 SSL, SMTP mail.example.com:465 SSL, password in /opt/mailserver/CREDENTIALS.txt
- [ ] USER: receive test — send Gmail → arun@example.com (proves inbound port 25 unblocked, still unconfirmed); then send test scored on mail-tester.com (do AFTER PTR is set)

## Setup tasks (user)
- [ ] Add 5 DNS records at Namecheap (Domain List → example.com → Advanced DNS), then tell Claude to verify:
  1. TXT `@` → `brevo-code:1a350e15f58085052022d4b8c6fced80`
  2. CNAME `brevo1._domainkey` → `b1.example-com.dkim.brevo.com`
  3. CNAME `brevo2._domainkey` → `b2.example-com.dkim.brevo.com`
  4. TXT `_dmarc` → `v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com`
  5. TXT `@` → `v=spf1 ip4:YOUR_SERVER_IP ~all`  ← SPF; makes the self-hosted backup relay deliverable (Gmail hard-rejects without it, tested 2026-06-12)
- [ ] After DNS propagates: press "Authenticate this domain" in Brevo, generate SMTP key (Settings → SMTP & API), give key to Claude → swap `.env` from self-hosted relay to Brevo (host smtp-relay.brevo.com, port 587, STARTTLS=true, username = Brevo login email, password = key)
- [ ] Upgrade email sending if volume grows (only when the 300/day Brevo free cap is actually hit): Brevo Starter ~$9/mo (5k/mo, no logo) or Amazon SES (~$0.10 per 1,000, needs AWS production-access request) — switch is just 5 `.env` lines + backend restart
- [ ] Gmail/Outlook OAuth credentials (steps in README.md) — redirect URI is now `https://www.example.com/api/accounts/oauth/<provider>/callback`
- ~~DNS A record + HTTPS for mail.example.com~~ — obsolete: app now served at https://www.example.com (2026-06-12 session 4); old HTTP URL still works as fallback

## Done & live
- [x] Core app: multi-account IMAP sync, unified inbox, send, folders, contacts (2026-06-12)
- [x] Email graph view, TF-IDF (2026-06-12)
- [x] Attachment download (2026-06-12)
- [x] Registration email verification (2026-06-12) — inactive until SMTP configured
- [x] Moved app to https://www.example.com with HTTPS via existing cert; n8n stays at /n8n/; .env URLs updated (2026-06-12 session 4)
