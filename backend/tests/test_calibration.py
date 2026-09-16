from hanjan.grind.calibration import Point, build_calibration, suggest_clicks


def cal(*pairs: tuple[int, float]):
    return build_calibration([Point(clicks, d50) for clicks, d50 in pairs])


def test_rows_use_median_per_click_setting():
    c = cal((10, 0.50), (10, 0.54), (10, 0.52), (20, 0.80))
    assert [(r.clicks, r.n, r.d50_median_mm, r.d50_min_mm, r.d50_max_mm) for r in c.rows] == [
        (10, 3, 0.52, 0.5, 0.54),
        (20, 1, 0.8, 0.8, 0.8),
    ]
    assert c.monotonic


def test_interpolates_inside_the_measured_range():
    s = suggest_clicks(cal((10, 0.5), (20, 0.8)), 0.65)
    assert s.clicks == 15
    assert "보간" in s.reason


def test_refuses_to_extrapolate_outside_the_measured_range():
    s = suggest_clicks(cal((10, 0.5), (20, 0.8)), 0.9)
    assert s.clicks is None
    assert "범위" in s.reason


def test_refuses_when_more_clicks_do_not_mean_coarser():
    s = suggest_clicks(cal((10, 0.6), (15, 0.5), (20, 0.8)), 0.7)
    assert s.clicks is None
    assert "커지지 않는" in s.reason


def test_needs_two_different_click_settings():
    assert suggest_clicks(cal((10, 0.5), (10, 0.6)), 0.55).clicks is None
