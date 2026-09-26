import numpy as np

from analysis.calibration_sim import run


def test_simulation_runs_and_ds_is_not_worse_with_panels() -> None:
    res = run(panel_sizes=(1, 3), reps=3, n_items=60, pool_size=15, seed=1)
    for key in ("majority", "ds_ml", "dawid_skene", "ds_calibrated"):
        assert len(res[3][key]) == 3
    # a single observer: every method returns that observer's answer
    assert np.allclose(res[1]["majority"], res[1]["dawid_skene"], atol=0.05)
    assert np.mean(res[3]["dawid_skene"]) >= np.mean(res[3]["majority"]) - 0.02
