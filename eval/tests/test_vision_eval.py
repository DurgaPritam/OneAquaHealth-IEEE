from eval.run_vision_eval import evaluate, synthetic_cards, write_report


def test_eval_pipeline_runs_on_synthetic_cards(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import eval.run_vision_eval as ev

    monkeypatch.setattr(ev, "REPORTS", tmp_path)
    result = evaluate(synthetic_cards())
    assert result["n"] > 10 and result["available_rate"] == 1.0
    text = write_report(result, synthetic=True).read_text()
    assert "Synthetic inputs" in text and "Mock provider" in text
