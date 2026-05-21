import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getMe, api, getReadiness } from '../utils/api'
import { useScenarios, useDeleteScenario } from '../hooks/useScenarios'
import ScenarioCard from '../components/ScenarioCard'
import ScenarioForm from '../components/ScenarioForm'
import NowVsWait from '../components/NowVsWait'
import type { AffordabilityResult, UserProfile, Scenario, ReadinessResult } from '../types'
import styles from './Dashboard.module.css'

// ── Formatters ───────────────────────────────────────────────────────────────

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}
function fmtRate(r: number) {
  return `${r.toFixed(2)}%`
}

// ── Component ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { user, isLoggedIn } = useAuth()
  const navigate = useNavigate()

  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [result, setResult] = useState<AffordabilityResult | null>(null)
  const [readiness, setReadiness] = useState<ReadinessResult | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [calcError, setCalcError] = useState(false)

  const [activeTab, setActiveTab] = useState<'overview' | 'scenarios'>('overview')
  const [activeScenarioId, setActiveScenarioId] = useState<number | null>(null)
  const [showForm, setShowForm] = useState(false)

  const userId = user?.user_id
  const { data: scenarios = [], refetch: refetchScenarios } = useScenarios(userId)
  const deleteMutation = useDeleteScenario(userId ?? 0)

  useEffect(() => {
    if (!isLoggedIn || !user) {
      navigate('/login')
      return
    }

    let cancelled = false

    async function load() {
      setIsLoading(true)
      try {
        const me: UserProfile = await getMe(user!.user_id)
        if (cancelled) return
        setProfile(me)

        if (
          me.annual_income != null &&
          me.savings != null &&
          me.down_payment != null &&
          me.credit_score != null &&
          me.zip_code
        ) {
          const monthlyDebt =
            (me.monthly_debt_car ?? 0) +
            (me.monthly_debt_student ?? 0) +
            (me.monthly_debt_credit ?? 0) +
            (me.monthly_debt_other ?? 0)

          try {
            const { data: aff } = await api.post<AffordabilityResult>('/api/v1/affordability', {
              annual_income: me.annual_income,
              savings: me.savings,
              monthly_debt: monthlyDebt,
              credit_score: me.credit_score,
              down_payment: me.down_payment,
              zip_code: me.zip_code,
            })
            if (!cancelled) {
              setResult(aff)
              // Fetch backend readiness score using the actual rate + max price
              try {
                const r = await getReadiness({
                  scenario_type: 'buy',
                  annual_income: me.annual_income!,
                  savings: me.savings ?? 0,
                  down_payment: me.down_payment ?? 0,
                  credit_score: me.credit_score ?? 620,
                  monthly_debt_car: me.monthly_debt_car,
                  monthly_debt_student: me.monthly_debt_student,
                  monthly_debt_credit: me.monthly_debt_credit,
                  monthly_debt_other: me.monthly_debt_other,
                  cached_max_price: aff.max_price,
                  cached_monthly_payment: aff.monthly_payment,
                  rate_used: aff.rate_used,
                  liquid_savings: me.liquid_savings ?? undefined,
                  target_zip: me.zip_code ?? undefined,
                })
                if (!cancelled) setReadiness(r)
              } catch { /* readiness is optional — don't block dashboard */ }
            }
          } catch {
            if (!cancelled) setCalcError(true)
          }
        }
      } catch {
        // Profile not yet set up
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [isLoggedIn, user, navigate])

  const hasProfile =
    profile != null &&
    profile.annual_income != null &&
    profile.zip_code != null

  const firstName = user?.first_name ?? 'there'


  function handleDelete(scenarioId: number) {
    deleteMutation.mutate(scenarioId, {
      onSuccess: () => {
        if (activeScenarioId === scenarioId) setActiveScenarioId(null)
      },
    })
  }

  function handleScenarioCreated(s: Scenario) {
    setActiveScenarioId(s.id)
    setActiveTab('scenarios')  // switch to My Scenarios tab so the new scenario is visible
    refetchScenarios()
  }

  const previewScenarios = scenarios.slice(0, 3)

  return (
    <div className={styles.page}>
      <div className={styles.inner}>
        {/* Greeting */}
        <h1 className={styles.greeting}>Welcome back, {firstName}.</h1>
        <p className={styles.greetingSub}>Here's a snapshot of your home buying picture.</p>

        {/* Tab row */}
        <div className={styles.tabs}>
          <button
            className={`${styles.tabBtn} ${activeTab === 'overview' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </button>
          <button
            className={`${styles.tabBtn} ${activeTab === 'scenarios' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('scenarios')}
          >
            My Scenarios
          </button>
        </div>

        {/* ── OVERVIEW TAB ── */}
        {activeTab === 'overview' && (
          <div className={styles.mainLayout}>
            {/* Left column */}
            <div>
              {isLoading && (
                <div className={styles.loadingState}>
                  <div className={styles.spinner} />
                  Loading your profile…
                </div>
              )}

              {!isLoading && hasProfile && result && !calcError && (
                <div className={styles.statShelf}>
                  <div className={styles.statCell}>
                    <span className={styles.statLabel}>Max purchase price</span>
                    <span className={styles.statValue}>{fmt(result.max_price)}</span>
                    <span className={styles.statSub}>Based on current rates</span>
                  </div>
                  <div className={styles.statCell}>
                    <span className={styles.statLabel}>Est. monthly payment</span>
                    <span className={styles.statValue}>{fmt(result.monthly_payment)}</span>
                    <span className={styles.statSub}>Principal &amp; interest</span>
                  </div>
                  <div className={styles.statCell}>
                    <span className={styles.statLabel}>Rate used</span>
                    <span className={styles.statValue}>{fmtRate(result.rate_used)}</span>
                    <span className={styles.statSub}>Current 30-yr fixed</span>
                  </div>
                </div>
              )}

              {!isLoading && !hasProfile && (
                <div className={styles.noProfile}>
                  <h2 className={styles.noProfileTitle}>Complete your financial profile</h2>
                  <p className={styles.noProfileText}>
                    Add your income, savings, and debt to see your real home buying budget and browse
                    listings in your range.
                  </p>
                  <Link to="/onboarding" className={styles.noProfileBtn}>
                    Complete my profile →
                  </Link>
                </div>
              )}

              {/* Now vs Wait */}
              {!isLoading && hasProfile && result && profile && (
                <NowVsWait
                  profile={profile}
                  loanType={result.loan_type}
                />
              )}

              {/* Quick actions */}
              <div className={styles.quickActions}>
                <Link
                  to="/map"
                  state={result ? { maxPrice: result.max_price } : undefined}
                  className={styles.actionCard}
                >
                  <span className={styles.actionIcon}>🗺</span>
                  <span className={styles.actionLabel}>Browse the map</span>
                </Link>
                {profile?.zip_code && (
                  <Link to={`/forecast/${profile.zip_code}`} className={styles.actionCard}>
                    <span className={styles.actionIcon}>📈</span>
                    <span className={styles.actionLabel}>ZIP price forecast</span>
                  </Link>
                )}
                <button
                  className={styles.actionCard}
                  onClick={() => setShowForm(true)}
                >
                  <span className={styles.actionIcon}>＋</span>
                  <span className={styles.actionLabel}>Add scenario</span>
                </button>
              </div>

              {/* Preview scenarios */}
              <div className={styles.scenariosSection}>
                <h2 className={styles.sectionTitle}>Your Scenarios</h2>
                {scenarios.length === 0 ? (
                  <p className={styles.emptyState}>
                    Save different financial scenarios to compare what you could afford.
                  </p>
                ) : (
                  <div className={styles.scenarioGrid}>
                    {previewScenarios.map(s => (
                      <ScenarioCard
                        key={s.id}
                        scenario={s}
                        isActive={activeScenarioId === s.id}
                        onSelect={() => setActiveScenarioId(s.id)}
                        onDelete={() => handleDelete(s.id)}
                      />
                    ))}
                  </div>
                )}
                {scenarios.length > 3 && (
                  <button
                    className={styles.seeAllBtn}
                    onClick={() => setActiveTab('scenarios')}
                  >
                    See all {scenarios.length} scenarios →
                  </button>
                )}
              </div>
            </div>

            {/* Right column — Readiness score */}
            {readiness && (
              <div className={styles.scorePanel}>
                <p className={styles.scoreTitle}>Readiness Score</p>
                <div
                  className={styles.scoreRing}
                  style={{ '--score-pct': readiness.score } as React.CSSProperties}
                >
                  <span className={styles.scoreNumber}>{readiness.score}</span>
                </div>

                {/* Component breakdown */}
                <div className={styles.scoreBreakdown}>
                  {readiness.components.map((c) => (
                    <div key={c.label} className={styles.scoreRow}>
                      <span className={styles.scoreRowLabel}>
                        {c.label}
                        {c.label === 'Market fit' && readiness.market_fit_label && (
                          <span className={`${styles.marketFitBadge} ${styles[`marketFit${readiness.market_fit_label.replace(' ', '')}`]}`}>
                            {readiness.market_fit_label}
                          </span>
                        )}
                      </span>
                      <span className={styles.scoreRowPts}>
                        {c.points}<span className={styles.scoreRowMax}>/{c.max}</span>
                      </span>
                    </div>
                  ))}
                </div>

                {readiness.actions.length > 0 && (
                  <div className={styles.actionItems}>
                    {readiness.actions.map((a, i) => (
                      <div key={i} className={styles.actionItem}>{a}</div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── MY SCENARIOS TAB ── */}
        {activeTab === 'scenarios' && (
          <div>
            <div className={styles.scenariosHeader}>
              <h2 className={styles.sectionTitle}>My Scenarios</h2>
              <button
                className={styles.newScenarioBtn}
                onClick={() => setShowForm(true)}
              >
                New scenario +
              </button>
            </div>

            {scenarios.length === 0 ? (
              <p className={styles.emptyState}>
                No scenarios yet. Create one to start comparing your options.
              </p>
            ) : (
              <div className={styles.scenarioGrid}>
                {scenarios.map(s => (
                  <ScenarioCard
                    key={s.id}
                    scenario={s}
                    isActive={activeScenarioId === s.id}
                    onSelect={() => setActiveScenarioId(s.id)}
                    onDelete={() => handleDelete(s.id)}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Scenario form modal */}
      {showForm && userId != null && (
        <ScenarioForm
          userId={userId}
          onClose={() => setShowForm(false)}
          onCreated={handleScenarioCreated}
        />
      )}
    </div>
  )
}
