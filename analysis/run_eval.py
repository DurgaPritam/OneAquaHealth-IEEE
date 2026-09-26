"""npm run eval: regenerate every evaluation report in eval/reports/."""

from __future__ import annotations

from analysis import calibration_sim, make_golden, sensitivity
from eval import run_vision_eval


def main() -> None:
    calibration_sim.main()
    sensitivity.main()
    run_vision_eval.main([])
    make_golden.main()
    try:
        from analysis import backtest
    except ImportError:
        print("backtest not available yet")
    else:
        backtest.main()


if __name__ == "__main__":
    main()
