# Unimail Checklist

## To build — customer-experience test findings (user narrated 2026-07-04, NOT yet approved to build)
- [x] **Breadcrumb separator invisible** (FIXED 2026-07-04) — NavBar.tsx does render a `›` between crumbs, but it's styled `text-divider` (same color as hairline borders) so it's effectively invisible; user reads it as "missing >". Fix: give the separator a visible color (e.g. text-muted). Also note single-crumb views (Home, Settings, account folders) legitimately show no separator.
- [x] **Duplicate Home tabs can't be closed** (FIXED 2026-07-04: × by id, + button removed) — the `+` (new tab) button in TabBar.tsx opens ANOTHER tab with kind 'home' (key home-1, home-2…); the × close button is hidden for every `kind === 'home'` tab, while the store only protects the one real `tab-home` id — so extra Home tabs are uncloseable zombies. User expectation: ONE static/pinned Home tab; content opens in new tabs. Fix: hide × only for `id === 'tab-home'` (extra tabs become closable) AND rethink `+` — either remove it or make it focus Home instead of duplicating it.

## Misimplementations — ALL FIXED & DEPLOYED 2026-07-04 (found in same-day full backend review)
- [x] 1. **Read/star changes revert within 5 min** — new services/imap_actions.py `push_flags` mirrors is_read/is_starred to IMAP (STORE \Seen/\Flagged) as a background task from patch_email. VERIFIED live: PATCH → doveadm shows \Seen \Flagged on server; manual sync no longer reverts.
- [x] 2. **Delete/move to trash was local-only** — `push_move` does IMAP MOVE (COPY+\Deleted+EXPUNGE fallback) to the account folder with the target role; UID detached, next sync reclaims it by Message-ID. VERIFIED live: PATCH folder_role=trash → message left server INBOX, appeared in server Trash, row reclaimed uid after sync. Archive stays local-only (server archive folders aren't synced — SKIP_FOLDERS).
- [x] 3. **Sent mail never reached the real Sent folder** — `push_sent_copy` APPENDs to the role=sent folder after send (only provider == "imap"; Gmail/Outlook/Yahoo auto-save). Sync gained Message-ID reclaim: any row with NULL imap_uid + matching message_id is updated in place instead of duplicated (covers appended sent copies, Gmail auto-saved copies, moved messages, UIDVALIDITY resets). VERIFIED live: send → server Sent has the message; after sync exactly 1 sent row (folder Sent, uid set), no dup.
- [x] 4. **Disconnect account 500'd once labels/graph/sync existed** — disconnect_account now bulk-deletes label_emails, email_embeddings, attachments, emails, folders, sync_log before the account row (also much faster than ORM cascade). NOTE: sync_log FK meant disconnect was broken for EVERY synced account, not just label/graph users. VERIFIED: synthetic account with label link + embedding + sync log → DELETE 204, all children gone.
- [x] 5. **SMTP port 465 unsupported** — smtp_service uses SMTP_SSL for port 465, STARTTLS otherwise; XOAUTH2 reply code now checked (raises on != 235).
- [x] 6. Minor batch: LIKE wildcards `%`/`_` escaped in all search endpoints (emails/contacts/graph); thread + contact recipient matching now matches the exact JSON `"email": "addr"` (no more jimbob@x.com hits for bob@x.com); UIDVALIDITY reset now NULLs stored UIDs so rows reclaim by Message-ID instead of colliding with stale UIDs; imap_uid/last_seen_uid/uidvalidity → BIGINT (models + manual ALTER TABLE, done in prod). SKIPPED deliberately: remote-image/tracking-pixel blocking — needs a "load images" UI toggle, that's a feature → add to "To build" if wanted.

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
- [x] Portainer brute-force protection (2026-07-04) — strict rate limit on its login endpoint (`location = /api/auth`, 10 req/min per IP). NOTE: full nginx basic-auth is NOT possible — Portainer's UI sends `Authorization: Bearer` which basic-auth would reject, breaking the app. Admin password confirmed strong by user 2026-07-04 → item closed.
- [x] nginx rate limiting (2026-07-04) — `/opt/nginx/conf.d/00-ratelimit.conf` defines 3 zones: `auth` 10r/min (Unimail /api/auth/ + Portainer login), `api` 10r/s burst 20 (Unimail + Pillar Square APIs), `general` 30r/s burst 50 (all sites incl. n8n, Open WebUI, msf-bot). Returns 429. Tested live: 7th rapid login attempt → 429.
- [x] Cloudflare in front of example.com (2026-07-04) — free plan, nameservers danica/keenan.ns.cloudflare.com; @/www/portainer/wa proxied (real IP hidden), `mail` DNS-only (email untouched, 10/10 intact), Universal SSL issued, all sites verified 200 via CF edge. `ollama` subdomain dropped: Open WebUI decommissioned same day (nginx block removed, container stopped + restart=no; ollama container stays internal for Unimail embeddings). Optional later: repeat for example.com. Found during checks: msf-bot container doesn't exist → wa. 502s (pre-existing, unrelated).
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
- [x] PTR / reverse DNS set at your VPS provider panel — verified 2026-07-02: YOUR_SERVER_IP → mail.example.com
- [x] Let's Encrypt cert for mail.example.com issued 2026-07-02 (expires 2026-09-30, auto-renews); compose swapped to SSL_TYPE=letsencrypt; renew cron got --deploy-hook "docker restart mailserver"; IMAPS/SMTPS verified serving LE cert, IMAP login OK
- [x] arun@example.com added to Unimail (IMAP) — verified 2026-07-02: account row sync_status=ok, 5-min scheduler pulling INBOX
- [x] Receive test PASSED 2026-07-02: Gmail → arun@example.com delivered (TLS 1.3, amavis Passed CLEAN, stored in INBOX, synced into Unimail). Inbound 25 open after your VPS provider panel firewall rules added (25/465/587/993/2222 — panel default only allowed 22/80/443)
- [x] Send test scored on mail-tester.com 2026-07-04: **10/10** — SPF pass, DKIM valid, TLS 1.3, no blacklists (sent through Unimail's send API, so the full app path is proven too)
- [x] Harden: smtpd_tls_auth_only=yes (2026-07-04) — via docker-data/dms/config/postfix-main.cf override. GOTCHA: docker-mailserver only applies overrides on container re-CREATION (`docker compose up -d --force-recreate`), not restart. Verified: port 587 no longer advertises AUTH before STARTTLS.
- [x] System email VERIFIED WORKING end-to-end (2026-07-04): forgot-password → self-hosted relay → Gmail accepted 250 OK (SPF record did the trick). May land in spam (relay has no DKIM) — acceptable for backup.

## Setup tasks (user)
- [ ] Add 5 DNS records at Namecheap (Domain List → example.com → Advanced DNS), then tell Claude to verify:
  1. TXT `@` → `brevo-code:1a350e15f58085052022d4b8c6fced80`
  2. CNAME `brevo1._domainkey` → `b1.example-com.dkim.brevo.com`
  3. CNAME `brevo2._domainkey` → `b2.example-com.dkim.brevo.com`
  4. TXT `_dmarc` → `v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com`
  5. ~~TXT `@` → `v=spf1 ip4:YOUR_SERVER_IP ~all`~~ ✅ DONE (verified in DNS 2026-07-04) — self-hosted relay is now SPF-authorized; records 1–4 (Brevo) still missing, but may be obsolete now that /opt/mailserver works
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
