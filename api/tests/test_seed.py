from sqlmodel import Session, select

from api import models as m
from api import seed, synthetic


def test_seed_loads_real_sites_and_labelled_synthetic_records(session: Session) -> None:
    sites = seed.load_sites()
    assert len(sites) == 106
    assert seed.seed_sites(session, sites) == 106
    assert seed.seed_sites(session, sites) == 0  # idempotent
    observers, checkins = seed.seed_synthetic(session, sites, "CO")
    assert observers == 12 and checkins > 50
    assert all(not s.synthetic for s in session.exec(select(m.Site)).all())
    for table in (m.Observer, m.CheckIn, m.Finding):
        rows = session.exec(select(table)).all()
        assert rows and all(r.synthetic for r in rows), table.__name__
    for c in session.exec(select(m.CheckIn)).all():
        assert c.lat == round(c.lat, 3) and c.lon == round(c.lon, 3)
        assert c.consent is True


def test_scenario_is_deterministic() -> None:
    sites = seed.load_sites()
    a = synthetic.scenario(sites, seed=7)[2]
    b = synthetic.scenario(sites, seed=7)[2]
    assert a == b


def test_biased_observer_reports_banks_as_natural() -> None:
    import random

    obs = synthetic.ObserverProfile("X", accuracy=1.0, bias={"bank_right_CC": {"extensive": "present"}})
    rng = random.Random(0)
    reports = [synthetic.report("extensive", "bank_right_CC", synthetic.APE, obs, rng) for _ in range(200)]
    assert 0.7 < reports.count("present") / 200 < 0.9
