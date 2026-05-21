import React, { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useScenarios } from '../hooks/useScenarios'
import { getReadiness } from '../utils/api'
import type { Scenario, ReadinessResult } from '../types'
import styles from './ScenarioDetail.module.css'

// ── Formatters ───────────────────────────────────────────────────────────────

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

function fmtRate(r: number) {
  return `${r.toFixed(2)}%`
}

// ── Mortgage payment helper (for ARM worst-case display) ─────────────────────

function monthlyPayment(principal: number, annualRatePct: number, years = 30): number {
  const r = annualRatePct / 100 / 12
  const n = years * 12
  if (r === 0) return principal / n
  return (principal * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1)
}

// ── Summary paragraph ────────────────────────────────────────────────────────

function buildSummary(scenario: Scenario, r: ReadinessResult): string {
  const income = fmt(scenario.annual_income ?? 0)
  const maxPrice = scenario.cached_max_price ? fmt(scenario.cached_max_price) : 'not yet calculated'
  const dp = fmt(scenario.down_payment ?? 0)
  const rate = scenario.cached_rate_used ? fmtRate(scenario.cached_rate_used) : 'current market'
  const scoreLabel = r.score >= 80 ? 'strong' : r.score >= 60 ? 'solid' : r.score >= 40 ? 'developing' : 'early-stage'
  const highRate = r.rate_used > 6.5

  const outlook =
    r.score >= 80
      ? `You are in excellent shape to purchase. Consider acting sooner to lock in before rate changes erode your buying power.`
      : r.score >= 60
      ? `You are well-positioned to buy. A focused effort on ${r.dti_ratio_pct > 28 ? 'paying down monthly debt' : 'growing your down payment'} could push your score into the top tier.`
      : `Building your financial foundation now will significantly expand your options. Focus on the action items below for the highest impact.`

  return `Based on your "${scenario.name}" scenario, with an annual income of ${income} and ${dp} available for a down payment, you can afford homes priced up to ${maxPrice} at a ${rate} rate${highRate ? ' — note that the DTI threshold is tighter at current rates' : ''}. Your readiness score of ${r.score}/100 reflects a ${scoreLabel} financial position — driven by your ${r.credit_label.toLowerCase()} credit (${scenario.credit_score ?? '—'}) and a DTI of ${r.dti_ratio_pct}%. ${outlook}`
}

// ── Score ring ───────────────────────────────────────────────────────────────

function ScoreRing({ score }: { score: number }) {
  const color = score >= 80 ? '#1C3A2F' : score >= 60 ? '#B5935A' : '#9c9490'
  return (
    <div
      className={styles.scoreRing}
      style={{
        '--score-pct': score,
        '--score-color': color,
      } as React.CSSProperties}
    >
      <div className={styles.scoreInner}>
        <span className={styles.scoreNumber}>{score}</span>
        <span className={styles.scoreOf}>/100</span>
      </div>
    </div>
  )
}

// ── Component ────────────────────────────────────────────────────────────────

export default function ScenarioDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user, isLoggedIn } = useAuth()

  const { data: scenarios = [], isLoading: scenariosLoading } = useScenarios(isLoggedIn ? user?.user_id : undefined)
  const [readiness, setReadiness] = useState<ReadinessResult | null>(null)
  const [readinessLoading, setReadinessLoading] = useState(false)

  const scenarioId = Number(id)
  const scenario = scenarios.find((s) => s.id === scenarioId)

  useEffect(() => {
    if (!scenario || scenario.annual_income == null) return
    setReadinessLoading(true)
    getReadiness({
      annual_income: scenario.annual_income,
      savings: scenario.savings ?? 0,
      down_payment: scenario.down_payment ?? 0,
      credit_score: scenario.credit_score ?? 620,
      monthly_debt_car: scenario.monthly_debt_car,
      monthly_debt_student: scenario.monthly_debt_student,
      monthly_debt_credit: scenario.monthly_debt_credit,
      monthly_debt_other: scenario.monthly_debt_other,
      cached_max_price: scenario.cached_max_price ?? undefined,
      rate_used: scenario.cached_rate_used ?? undefined,
    })
      .then(setReadiness)
      .catch(() => setReadiness(null))
      .finally(() => setReadinessLoading(false))
  }, [scenario?.id])

  if (!isLoggedIn) {
    navigate('/login')
    return null
  }

  if (scenariosLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingState}>
          <div className={styles.spinner} />
          Loading scenario…
        </div>
      </div>
    )
  }

  if (!scenario) {
    return (
      <div className={styles.page}>
        <div className={styles.notFound}>
          <h2>Scenario not found</h2>
          <Link to="/dashboard">← Back to dashboard</Link>
        </div>
      </div>
    )
  }

  const summary = readiness ? buildSummary(scenario, readiness) : null
  const totalDebt = scenario.monthly_debt_car + scenario.monthly_debt_student + scenario.monthly_debt_credit + scenario.monthly_debt_other

  const typeBadgeClass = scenario.scenario_type === 'rent' ? styles.badgeRent : styles.badgeBuy

  const loanTypeLabel: Record<string, string> = {
    conventional: 'Conventional',
    fha: 'FHA',
    va: 'VA',
    usda: 'USDA',
    arm_5_1: 'ARM 5/1',
    jumbo: 'Jumbo',
  }
  const loanLabel = loanTypeLabel[scenario.loan_type] ?? scenario.loan_type?.toUpperCase()

  return (
    <div className={styles.page}>
      <div className={styles.inner}>

        {/* Back link */}
        <Link to="/dashboard" className={styles.backLink}>← Back to dashboard</Link>

        {/* Header */}
        <div className={styles.header}>
          <div>
            <div className={styles.headerTop}>
              <span className={`${styles.badge} ${typeBadgeClass}`}>
                {scenario.scenario_type === 'rent' ? 'RENT' : 'BUY'}
              </span>
              {scenario.scenario_type === 'buy' && loanLabel && (
                <span className={`${styles.badge} ${styles.badgeLoan}`}>{loanLabel}</span>
              )}
              <h1 className={styles.title}>{scenario.name}</h1>
            </div>
            {scenario.zip_code && (
              <p className={styles.meta}>{scenario.zip_code}</p>
            )}
          </div>

          {scenario.cached_max_price && (
            <div className={styles.maxPrice}>
              <span className={styles.maxPriceLabel}>
                {scenario.scenario_type === 'rent' ? 'Max monthly rent' : 'Max home price'}
              </span>
              <span className={styles.maxPriceVal}>{fmt(scenario.cached_max_price)}</span>
              {scenario.cached_monthly_payment && (
                <span className={styles.maxPriceSub}>
                  {fmt(scenario.cached_monthly_payment)}/mo · {scenario.cached_rate_used ? fmtRate(scenario.cached_rate_used) : '—'} rate
                </span>
              )}
            </div>
          )}
        </div>

        <div className={styles.layout}>
          {/* Left column */}
          <div className={styles.left}>

            {/* Summary paragraph */}
            {summary && (
              <div className={styles.summaryCard}>
                <p className={styles.summaryEyebrow}>Your situation</p>
                <p className={styles.summaryText}>{summary}</p>
              </div>
            )}

            {/* ARM worst-case callout */}
            {scenario.loan_type === 'arm_5_1' && scenario.cached_rate_used != null && scenario.cached_max_price != null && scenario.down_payment != null && (
              <div className={styles.armCallout}>
                <p className={styles.armCalloutTitle}>Rate risk — ARM 5/1</p>
                <p className={styles.armCalloutBody}>
                  Your initial rate is <strong>{scenario.cached_rate_used.toFixed(2)}%</strong>.
                  After year 5, if rates rise to the lifetime cap (+5%), your monthly payment could reach{' '}
                  <strong>
                    {fmt(Math.round(monthlyPayment(
                      scenario.cached_max_price - scenario.down_payment,
                      scenario.cached_rate_used + 5,
                    )))}
                    /mo
                  </strong>{' '}
                  — up from {fmt(scenario.cached_monthly_payment ?? 0)}/mo today.
                </p>
              </div>
            )}

            {/* Financial breakdown */}
            <div className={styles.card}>
              <h2 className={styles.cardTitle}>Financial breakdown</h2>
              <div className={styles.breakdownGrid}>
                <div className={styles.breakdownItem}>
                  <span className={styles.breakdownLabel}>Annual income</span>
                  <span className={styles.breakdownVal}>{fmt(scenario.annual_income ?? 0)}</span>
                </div>
                <div className={styles.breakdownItem}>
                  <span className={styles.breakdownLabel}>Total savings</span>
                  <span className={styles.breakdownVal}>{fmt(scenario.savings ?? 0)}</span>
                </div>
                {scenario.scenario_type === 'buy' && (
                  <div className={styles.breakdownItem}>
                    <span className={styles.breakdownLabel}>Down payment</span>
                    <span className={styles.breakdownVal}>{fmt(scenario.down_payment ?? 0)}</span>
                  </div>
                )}
                <div className={styles.breakdownItem}>
                  <span className={styles.breakdownLabel}>Credit score</span>
                  <span className={styles.breakdownVal}>
                    {scenario.credit_score ?? '—'}
                    {readiness && <span className={styles.creditLabel}> · {readiness.creditLabel}</span>}
                  </span>
                </div>
              </div>

              <h3 className={styles.debtTitle}>Monthly debt obligations</h3>
              <div className={styles.debtGrid}>
                {scenario.monthly_debt_car > 0 && (
                  <div className={styles.debtItem}>
                    <span>Car / auto</span>
                    <span>{fmt(scenario.monthly_debt_car)}/mo</span>
                  </div>
                )}
                {scenario.monthly_debt_student > 0 && (
                  <div className={styles.debtItem}>
                    <span>Student loans</span>
                    <span>{fmt(scenario.monthly_debt_student)}/mo</span>
                  </div>
                )}
                {scenario.monthly_debt_credit > 0 && (
                  <div className={styles.debtItem}>
                    <span>Credit card minimums</span>
                    <span>{fmt(scenario.monthly_debt_credit)}/mo</span>
                  </div>
                )}
                {scenario.monthly_debt_other > 0 && (
                  <div className={styles.debtItem}>
                    <span>Other</span>
                    <span>{fmt(scenario.monthly_debt_other)}/mo</span>
                  </div>
                )}
                <div className={`${styles.debtItem} ${styles.debtTotal}`}>
                  <span>Total monthly debt</span>
                  <span>{fmt(totalDebt)}/mo</span>
                </div>
              </div>
            </div>

            {/* CTA */}
            <button
              className={styles.mapBtn}
              onClick={() =>
                navigate('/map', {
                  state: {
                    maxPrice: scenario.cached_max_price ?? 600_000,
                    scenarioName: scenario.name,
                    scenarioId: scenario.id,
                  },
                })
              }
            >
              View homes on the map →
            </button>
          </div>

          {/* Right column — readiness score */}
          {(readiness || readinessLoading) && (
            <div className={styles.scorePanel}>
              <p className={styles.scorePanelTitle}>Readiness Score</p>

              {readinessLoading ? (
                <div className={styles.loadingState}>
                  <div className={styles.spinner} />
                </div>
              ) : readiness ? (
                <>
                  <ScoreRing score={readiness.score} />

                  <div className={styles.scoreBreakdown}>
                    <div className={styles.scoreRow}>
                      <span className={styles.scoreRowLabel}>Debt-to-income</span>
                      <div className={styles.scoreBar}>
                        <div className={styles.scoreBarFill} style={{ width: `${(readiness.components.dti_pts / 35) * 100}%` }} />
                      </div>
                      <span className={styles.scoreRowPts}>{readiness.components.dti_pts}/35</span>
                    </div>
                    <div className={styles.scoreRow}>
                      <span className={styles.scoreRowLabel}>Down payment</span>
                      <div className={styles.scoreBar}>
                        <div className={styles.scoreBarFill} style={{ width: `${(readiness.components.dp_pts / 25) * 100}%` }} />
                      </div>
                      <span className={styles.scoreRowPts}>{readiness.components.dp_pts}/25</span>
                    </div>
                    <div className={styles.scoreRow}>
                      <span className={styles.scoreRowLabel}>Credit score</span>
                      <div className={styles.scoreBar}>
                        <div className={styles.scoreBarFill} style={{ width: `${(readiness.components.credit_pts / 25) * 100}%` }} />
                      </div>
                      <span className={styles.scoreRowPts}>{readiness.components.credit_pts}/25</span>
                    </div>
                    <div className={styles.scoreRow}>
                      <span className={styles.scoreRowLabel}>Savings cushion</span>
                      <div className={styles.scoreBar}>
                        <div className={styles.scoreBarFill} style={{ width: `${(readiness.components.cushion_pts / 15) * 100}%` }} />
                      </div>
                      <span className={styles.scoreRowPts}>{readiness.components.cushion_pts}/15</span>
                    </div>
                    {readiness.rate_used > 6.5 && (
                      <p className={styles.rateNote}>
                        DTI ceiling tightened to {readiness.dti_ceiling_pct}% at current {readiness.rate_used.toFixed(2)}% rates
                      </p>
                    )}
                  </div>

                  {readiness.actions.length > 0 && (
                    <div className={styles.actionItems}>
                      <p className={styles.actionTitle}>Action plan</p>
                      {readiness.actions.map((a, i) => (
                        <div key={i} className={styles.actionItem}>
                          <span className={styles.actionBullet}>{i + 1}</span>
                          <span>{a}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
