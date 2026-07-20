from animation.animation_clock import Clock


def fake_time_source(readings):
    values = iter(readings)
    return lambda: next(values)


def test_first_tick_after_construction_measures_elapsed_since_construction():
    clock = Clock(time_source=fake_time_source([0.0, 0.016]))
    assert clock.tick() == 16


def test_second_tick_measures_since_the_previous_tick_not_since_construction():
    clock = Clock(time_source=fake_time_source([0.0, 0.016, 0.033]))
    clock.tick()
    assert clock.tick() == 17


def test_zero_elapsed_time_returns_zero():
    clock = Clock(time_source=fake_time_source([1.0, 1.0]))
    assert clock.tick() == 0
