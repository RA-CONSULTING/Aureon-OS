from aureon.trading.aureon_power_station_turbo import PowerStationTurbo


class Trap:
    calls = 0

    def create_order(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("unreachable")


def test_pulses_are_never_submitted_or_accounted():
    for dry_run, status in ((True, "dry_run_not_submitted"), (False, "live_submission_disabled")):
        station = PowerStationTurbo(dry_run=dry_run)
        trap = Trap()
        station.relays["trap"] = trap
        before = station.state.net_energy_gain, station.state.total_fees_paid
        pulse = station._execute_pulse("trap", "BTC/USDT", "buy", 1.0)
        assert (pulse.success, pulse.status, pulse.truth_status) == (False, status, "no_data")
        assert pulse.price is pulse.value is pulse.fee is pulse.net_gain is None
        assert not (pulse.action_enabled or pulse.accounting_enabled or pulse.learning_enabled)
        assert trap.calls == 0
        assert before == (station.state.net_energy_gain, station.state.total_fees_paid)
        station.executor.shutdown(wait=True)
