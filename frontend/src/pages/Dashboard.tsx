import React, { useEffect, useState, useMemo, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Map as MapIcon, TrendingUp, Plus } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { getMe, getReadiness, setPrimaryScenario } from '../utils/api'
import { useScenarios, useDeleteScenario } from '../hooks/useScenarios'
import ScenarioCard from '../components/ScenarioCard'
import ScenarioForm from '../components/ScenarioForm'
import NowVsWait from '../components/NowVsWait'
import type { UserProfile, Scenario, ReadinessResult } from '../types'
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
  const [readiness, setReadiness] = useState<ReadinessResult | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'scenarios'>('overview')
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  const userId = user?.user_id
  const { data: scenarios = [], isLoading: scenariosLoading, refetch: refetchScenarios } =
    useScenarios(userId)
  const deleteMutation = useDeleteScenario(userId ?? 0)

  const loadProfile = useCallback(() => {
    if (!user) return
    getMe(user.user_id).then(setProfile).catch(() => {})
  }, [user])

  useEffect(() => {
    if (!isLoggedIn || !user) {
      navigate('/login')
      return
    }
    loadProfile()
  }, [isLoggedIn, user, navigate, loadProfile])

  // ── Primary scenario: the one the dashboard headlines ──────────────────────
  // Priority: the user's explicit pick → their only scenario → none.
  const primaryScenario = useMemo<Scenario | null>(() => {
    if (scenarios.length === 0) return null
    if (profile?.primary_scenario_public_id) {
      const found = scenarios.find(s => s.public_id === profile.primary_scenario_public_id)
      if (found) return found
    }
    if (scenarios.length === 1) return scenarios[0]
    return null
  }, [scenarios, profile?.primary_scenario_public_id])

  // Headline numbers come straight from the primary scenario's saved affordability.
  const headline = useMemo(() => {
    if (!primaryScenario || primaryScenario.cached_max_price == null) return null
    return {
      maxPrice: primaryScenario.cached_max_price,
      monthlyPayment: primaryScenario.cached_monthly_payment ?? 0,
      rateUsed: primaryScenario.cached_rate_used,
      scenarioType: primaryScenario.scenario_type,
    }
  }, [primaryScenario])

  // Compute the readiness score from the primary scenario's inputs.
  useEffect(() => {
    let cancelled = false
    if (!primaryScenario || primaryScenario.annual_income == null) {
      setReadiness(null)
      return
    }
    getReadiness({
      scenario_type: primaryScenario.scenario_type,
      annual_income: primaryScenario.annual_income,
      savings: primaryScenario.savings ?? 0,
      down_payment: primaryScenario.down_payment ?? 0,
      credit_score: primaryScenario.credit_score ?? 620,
      monthly_debt_car: primaryScenario.monthly_debt_car,
      monthly_debt_student: primaryScenario.monthly_debt_student,
      monthly_debt_credit: primaryScenario.monthly_debt_credit,
      monthly_debt_other: primaryScenario.monthly_debt_other,
      cached_max_price: primaryScenario.cached_max_price ?? undefined,
      cached_monthly_payment: primaryScenario.cached_monthly_payment ?? undefined,
      rate_used: primaryScenario.cached_rate_used ?? undefined,
      target_zip: primaryScenario.zip_code ?? undefined,
    })
      .then(r => { if (!cancelled) setReadiness(r) })
      .catch(() => { if (!cancelled) setReadiness(null) })
    return () => { cancelled = true }
  }, [primaryScenario])

  const firstName = user?.first_name ?? 'there'
  const isLoading = scenariosLoading
  const isRent = headline?.scenarioType === 'rent'

  function handleDelete(publicId: string) {
    deleteMutation.mutate(publicId, {
      onSuccess: () => {
        if (activeScenarioId === publicId) setActiveScenarioId(null)
        loadProfile()  // primary pointer may have been cleared server-side
      },
    })
  }

  async function handleSetPrimary(publicId: string) {
    try {
      await setPrimaryScenario(publicId)
      setProfile(p => (p ? { ...p, primary_scenario_public_id: publicId } : p))
    } catch {
      /* ignore — star stays where it was */
    }
  }

  function handleScenarioCreated(s: Scenario) {
    setActiveScenarioId(s.public_id)
    setActiveTab('scenarios')
    refetchScenarios()
    loadProfile()  // first scenario is auto-set as primary server-side
  }

  const previewScenarios = scenarios.slice(0, 3)

  function renderScenarioCard(s: Scenario) {
    return (
      <ScenarioCard
        key={s.public_id}
        scenario={s}
        isActive={activeScenarioId === s.public_id}
        isPrimary={primaryScenario?.public_id === s.public_id}
        onSelect={() => setActiveScenarioId(s.public_id)}
        onDelete={() => handleDelete(s.public_id)}
        onSetPrimary={() => handleSetPrimary(s.public_id)}
      />
    )
  }

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
                  Loading your scenarios…
                </div>
              )}

              {/* Headline — driven by the primary scenario */}
              {!isLoading && headline && primaryScenario && (
                <>
                  <p className={styles.primaryLabel}>
                    Primary scenario: <strong>{primaryScenario.name}</strong>
                    {primaryScenario.zip_code ? ` · ${primaryScenario.zip_code}` : ''}
                  </p>
                  <div className={styles.statShelf}>
                    <div className={styles.statCell}>
                      <span className={styles.statLabel}>
                        {isRent ? 'Max monthly rent' : 'Max purchase price'}
                      </span>
                      <span className={styles.statValue}>{fmt(headline.maxPrice)}</span>
                      <span className={styles.statSub}>From your primary scenario</span>
                    </div>
                    <div className={styles.statCell}>
                      <span className={styles.statLabel}>
                        {isRent ? 'Recommended rent' : 'Est. monthly payment'}
                      </span>
                      <span className={styles.statValue}>{fmt(headline.monthlyPayment)}</span>
                      <span className={styles.statSub}>
                        {isRent ? 'Comfortable target' : 'Principal & interest'}
                      </span>
                    </div>
                    {!isRent && headline.rateUsed != null && (
                      <div className={styles.statCell}>
                        <span className={styles.statLabel}>Rate used</span>
                        <span className={styles.statValue}>{fmtRate(headline.rateUsed)}</span>
                        <span className={styles.statSub}>30-yr fixed</span>
                      </div>
                    )}
                  </div>
                </>
              )}

              {/* No scenarios yet */}
              {!isLoading && scenarios.length === 0 && (
                <div className={styles.noProfile}>
                  <h2 className={styles.noProfileTitle}>See your home buying power</h2>
                  <p className={styles.noProfileText}>
                    Create your first scenario — income, savings, loan type — to see what you can
                    afford and browse listings in your range.
                  </p>
                  <button className={styles.noProfileBtn} onClick={() => setShowForm(true)}>
                    Create my first scenario →
                  </button>
                </div>
              )}

              {/* Scenarios exist but none is primary */}
              {!isLoading && scenarios.length > 0 && !primaryScenario && (
                <div className={styles.noProfile}>
                  <h2 className={styles.noProfileTitle}>Choose a primary scenario</h2>
                  <p className={styles.noProfileText}>
                    Tap the ☆ on a scenario below to make it your primary — it drives this
                    dashboard, the map, and your forecast.
                  </p>
                </div>
              )}

              {/* Now vs Wait — buy scenarios only */}
              {!isLoading && primaryScenario && primaryScenario.scenario_type === 'buy' && (
                <NowVsWait
                  profile={primaryScenario}
                  loanType={primaryScenario.loan_type}
                />
              )}

              {/* Quick actions */}
              <div className={styles.quickActions}>
                <Link
                  to="/map"
                  state={{
                    maxPrice: headline?.maxPrice,
                    targetZip: primaryScenario?.zip_code ?? undefined,
                  }}
                  className={styles.actionCard}
                >
                  <MapIcon className={styles.actionIcon} size={26} strokeWidth={1.6} />
                  <span className={styles.actionLabel}>Browse the map</span>
                </Link>
                {primaryScenario?.zip_code && (
                  <Link
                    to={`/forecast/${primaryScenario.zip_code}${
                      primaryScenario.home_type && primaryScenario.home_type !== 'all'
                        ? `?type=${primaryScenario.home_type}`
                        : ''
                    }`}
                    className={styles.actionCard}
                  >
                    <TrendingUp className={styles.actionIcon} size={26} strokeWidth={1.6} />
                    <span className={styles.actionLabel}>ZIP price forecast</span>
                  </Link>
                )}
                <button className={styles.actionCard} onClick={() => setShowForm(true)}>
                  <Plus className={styles.actionIcon} size={26} strokeWidth={1.6} />
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
                    {previewScenarios.map(renderScenarioCard)}
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
                {scenarios.map(renderScenarioCard)}
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
