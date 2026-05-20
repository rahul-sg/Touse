export function monthlyPayment(principal: number, annualRate: number, years = 30): number {
  const r = annualRate / 12
  const n = years * 12
  if (r === 0) return principal / n
  return (principal * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1)
}

export function maxLoanFromPayment(monthlyPmt: number, annualRate: number, years = 30): number {
  const r = annualRate / 12
  const n = years * 12
  if (r === 0) return monthlyPmt * n
  return (monthlyPmt * (Math.pow(1 + r, n) - 1)) / (r * Math.pow(1 + r, n))
}
