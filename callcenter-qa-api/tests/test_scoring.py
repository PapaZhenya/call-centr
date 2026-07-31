from app.qa_evaluation.scoring import ScoreEntry, clamp_score, compute_weighted_overall, has_critical_violation


def test_clamp_score_caps_above_max():
    assert clamp_score(999, max_score=5) == 5


def test_clamp_score_floors_below_min():
    assert clamp_score(-3, max_score=5) == 1.0


def test_clamp_score_within_range_unchanged():
    assert clamp_score(3, max_score=5) == 3.0


def test_compute_weighted_overall_empty_is_none():
    assert compute_weighted_overall([]) is None


def test_compute_weighted_overall_all_max_scores_five():
    entries = [ScoreEntry(5, 1.0, 5), ScoreEntry(5, 1.0, 5)]
    assert compute_weighted_overall(entries) == 5.0


def test_compute_weighted_overall_all_min_scores_one():
    entries = [ScoreEntry(1, 1.0, 5), ScoreEntry(1, 1.0, 5)]
    assert compute_weighted_overall(entries) == 1.0


def test_compute_weighted_overall_respects_weight():
    # heavily-weighted low score should pull the overall down more than a
    # lightly-weighted high score pulls it up
    entries = [ScoreEntry(5, 0.1, 5), ScoreEntry(1, 10.0, 5)]
    overall = compute_weighted_overall(entries)
    assert overall < 2.0


def test_compute_weighted_overall_normalizes_across_different_max_scores():
    # a perfect score on a 10-point criterion should count the same as a
    # perfect score on a 5-point criterion
    entries = [ScoreEntry(10, 1.0, 10), ScoreEntry(5, 1.0, 5)]
    assert compute_weighted_overall(entries) == 5.0


def test_has_critical_violation_true_when_below_threshold():
    entries = [ScoreEntry(1, 1.0, 5, is_critical=True)]
    assert has_critical_violation(entries) is True


def test_has_critical_violation_false_when_not_critical():
    entries = [ScoreEntry(1, 1.0, 5, is_critical=False)]
    assert has_critical_violation(entries) is False


def test_has_critical_violation_false_when_critical_scores_well():
    entries = [ScoreEntry(5, 1.0, 5, is_critical=True)]
    assert has_critical_violation(entries) is False
