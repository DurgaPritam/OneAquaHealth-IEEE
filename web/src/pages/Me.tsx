import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import type { EngagementData } from '../lib/client'
import { useApp } from '../lib/context'
import type { SubmittedItem } from '../lib/db'
import { campaigns, leaderboard, MIN_QUALITY } from '../lib/engagement'
import type { Message } from '../lib/types'

export function Me({ cityId = 'CO' }: { cityId?: string }) {
  const { t } = useTranslation()
  const { client, observerId, store } = useApp()
  const [messages, setMessages] = useState<Message[] | null>(null)
  const [sent, setSent] = useState<SubmittedItem[]>([])
  const [data, setData] = useState<EngagementData | null>(null)

  useEffect(() => {
    client.listMessages(observerId).then(setMessages, () => setMessages([]))
    client.engagementData(cityId).then(setData, () => setData(null))
    void store.submitted.orderBy('synced_at').reverse().toArray().then(setSent)
  }, [client, observerId, store, cityId])

  const board = useMemo(() => (data ? leaderboard(data.observers, data.checkins, data.findings, data.scores) : null), [data])
  const campaign = useMemo(() => (data ? campaigns(data.latest, data.sites).slice(0, 5) : []), [data])
  const me = board?.people.find((p) => p.observer === observerId)
  const myTier = data?.observers.find((o) => o.id === observerId)
  const calibrated = Boolean((myTier?.calibration as { overall_kappa?: number } | undefined)?.overall_kappa !== undefined)

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <h1 className="h1">{t('me.heading')}</h1>
      <div className="card space-y-1">
        <p className="muted">{t('me.code', { code: observerId })}</p>
        <p className="font-semibold">
          {calibrated ? t('me.tier', { tier: t(`calib.tier_${myTier!.tier}`) }) : <Link className="underline" to="/practice">{t('me.tierNone')}</Link>}
        </p>
        <p className="text-lg font-semibold">{t('me.points', { points: me?.points ?? 0 })}</p>
        {me && <p className="muted">{t('me.counted', { counted: me.counted, ignored: me.ignored })}</p>}
        <p className="muted">{t('me.pointsHelp', { min: MIN_QUALITY })}</p>
      </div>

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

      <section aria-labelledby="camp-heading" className="card">
        <h2 id="camp-heading" className="h2">{t('me.campaignHeading')}</h2>
        <p className="muted mt-1">{t('me.campaignIntro')}</p>
        {data && campaign.length === 0 && <p className="mt-2">{t('me.campaignNone')}</p>}
        <ul className="mt-2 divide-y divide-slate-100">
          {campaign.map((c) => (
            <li key={c.site.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span>
                <span className="font-medium">{c.site.name}</span> <span className="muted">({c.site.id})</span>
                <span className="block text-sm text-slate-700">{t(`me.reason_${c.reason}`, { n: c.detail })}</span>
              </span>
              <Link to="/check" className="btn-secondary text-sm">{t('me.checkThis')}</Link>
            </li>
          ))}
        </ul>
      </section>

      {board && (
        <section aria-labelledby="board-heading" className="card space-y-3">
          <h2 id="board-heading" className="h2">{t('me.leaderHeading')}</h2>
          <p className="muted">{t('me.leaderIntro')}</p>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th scope="col" className="py-1">{t('me.team')}</th>
                <th scope="col" className="py-1">{t('me.members')}</th>
                <th scope="col" className="py-1">{t('me.perMember')}</th>
              </tr>
            </thead>
            <tbody>
              {board.teams.map((tm) => (
                <tr key={tm.team} className="border-b border-slate-100">
                  <td className="py-1">{tm.team}</td>
                  <td className="py-1 tabular-nums">{tm.members}</td>
                  <td className="py-1 tabular-nums">{tm.pointsPerMember}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3 className="font-semibold">{t('me.topObservers')}</h3>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th scope="col" className="py-1">{t('me.observer')}</th>
                <th scope="col" className="py-1">{t('me.tierCol')}</th>
                <th scope="col" className="py-1">{t('me.quality')}</th>
                <th scope="col" className="py-1">{t('me.pointsCol')}</th>
              </tr>
            </thead>
            <tbody>
              {board.people.slice(0, 8).map((p) => (
                <tr key={p.observer} className={`border-b border-slate-100 ${p.observer === observerId ? 'bg-brand-50 font-semibold' : ''}`}>
                  <td className="py-1 font-mono">{p.observer === observerId ? `${p.observer} (${t('me.you')})` : p.observer}</td>
                  <td className="py-1">{t(`calib.tier_${p.tier}`)}</td>
                  <td className="py-1 tabular-nums">{p.meanQuality.toFixed(2)}</td>
                  <td className="py-1 tabular-nums">{p.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted">{t('me.syntheticNote')}</p>
        </section>
      )}

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
