#!/usr/bin/env python3
"""
One-time Prophet / Stan setup — makes Prophet actually usable.

Prophet 1.1.x ships an INCOMPLETE bundled cmdstan
(prophet/stan_model/cmdstan-2.33.1/ — missing its makefile). Whenever that
directory is present, every `Prophet()` construction fails with a confusing
`AttributeError: 'Prophet' object has no attribute 'stan_backend'`.

This script makes Prophet work and keeps it working:

  1. ensures a real cmdstan toolchain is installed (~/.cmdstan, via cmdstanpy)
  2. disables Prophet's broken bundled cmdstan so Prophet falls back to (1)

It is idempotent — safe to run any number of times. RE-RUN IT after any
`pip install` that reinstalls prophet (a fresh install restores the broken dir):

    python scripts/setup_prophet.py
"""
import shutil
import sys
from pathlib import Path


def ensure_cmdstan() -> None:
    import cmdstanpy
    try:
        print(f"  cmdstan already installed: {cmdstanpy.cmdstan_path()}")
        return
    except Exception:
        print("  cmdstan not found — installing (compiles from source, a few minutes)...")
        cmdstanpy.install_cmdstan(overwrite=False, cores=4)
        print(f"  cmdstan installed: {cmdstanpy.cmdstan_path()}")


def disable_broken_bundled_cmdstan() -> None:
    import prophet
    stan_model = Path(prophet.__file__).parent / "stan_model"
    if not stan_model.is_dir():
        print("  prophet/stan_model not found — nothing to check")
        return

    fixed_any = False
    for d in sorted(stan_model.glob("cmdstan-*")):
        if not d.is_dir() or d.name.endswith(".disabled"):
            continue
        if (d / "makefile").exists():
            print(f"  bundled {d.name} looks complete — leaving it as-is")
            continue
        # Incomplete bundled cmdstan — disable it so Prophet uses the real one.
        disabled = d.parent / f"{d.name}.disabled"
        if disabled.exists():
            shutil.rmtree(d)
            print(f"  removed broken bundled {d.name} (a .disabled copy already exists)")
        else:
            d.rename(disabled)
            print(f"  disabled broken bundled cmdstan: {d.name} -> {disabled.name}")
        fixed_any = True
    if not fixed_any:
        print("  no broken bundled cmdstan present — good")


def verify() -> None:
    import pandas as pd
    from prophet import Prophet
    df = pd.DataFrame({
        "ds": pd.date_range("2021-01-01", periods=30, freq="MS"),
        "y": [100 + i for i in range(30)],
    })
    Prophet(weekly_seasonality=False, daily_seasonality=False).fit(df)
    print("  Prophet fit succeeded")


def main() -> int:
    print("Prophet / Stan setup")
    print("1. cmdstan toolchain")
    ensure_cmdstan()
    print("2. Prophet bundled cmdstan")
    disable_broken_bundled_cmdstan()
    print("3. verifying Prophet works")
    try:
        verify()
    except Exception as exc:  # noqa: BLE001 — surface any failure to the operator
        print(f"  Prophet still failing: {exc}", file=sys.stderr)
        return 1
    print("Done — Prophet is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
