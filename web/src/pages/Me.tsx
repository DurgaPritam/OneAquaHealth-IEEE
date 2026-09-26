import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useApp } from '../lib/context'
import type { SubmittedItem } from '../lib/db'
import type { Message } from '../lib/types'

export function Me() {
  const { t } = useTranslation()
  const { client, observerId, store } = useApp()
  const [messages, setMessages] = useState<Message[] | null>(null)
  const [sent, setSent] = useState<SubmittedItem[]>([])

  useEffect(() => {
    client.listMessages(observerId).then(setMessages, () => setMessages([]))
    void store.submitted.orderBy('synced_at').reverse().toArray().then(setSent)
  }, [client, observerId, store])

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <h1 className="h1">{t('me.heading')}</h1>
      <p className="muted">{t('me.code', { code: observerId })}</p>
      <section aria-labelledby="msg-heading" className="card">
        <h2 id="msg-heading" className="h2">{t('me.messagesHeading')}</h2>
        {messages && messages.length === 0 && <p className="mt-2">{t('me.noMessages')}</p>}
        <ul className="mt-2 space-y-3">
          {(messages ?? []).map((m) => (
            <li key={m.id} className={`rounded-lg border-l-4 p-3 ${m.kind === 'action_taken' ? 'border-brand-600 bg-brand-50' : 'border-sky-500 bg-sky-50'}`}>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-700">{t(`me.kind_${m.kind}`)}</p>
              <p className="mt-1">{m.text}</p>
              <p className="muted mt-1">{new Date(m.created_at).toLocaleDateString()}</p>
            </li>
          ))}
        </ul>
      </section>
      <section aria-labelledby="sent-heading" className="card">
        <h2 id="sent-heading" className="h2">{t('me.sentHeading')}</h2>
        {sent.length === 0 && <p className="mt-2">{t('me.noSent')}</p>}
        <ul className="mt-2 divide-y divide-slate-100">
          {sent.map((s) => (
            <li key={s.client_uuid} className="py-2">
              {s.site_id} · {new Date(s.observed_at).toLocaleString()}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
