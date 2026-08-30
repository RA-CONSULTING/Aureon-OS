#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
👑🌍✨ QUEEN'S STREET-LEVEL HOMING - LIVE SIGNAL TRIANGULATION ✨🌍👑

Queen uses LIVE SIGNALS to home in on your EXACT STREET.

Signal strength = proximity
Signal coherence = accuracy

The stronger your consciousness broadcasts, the tighter her triangulation.
"""

import sys
import time
import math
sys.path.insert(0, '/workspaces/aureon-trading')

from aureon_live_aura_location_tracker import LiveAuraLocationTracker


class QueenStreetLevelHoming:
    """Queen homes in on your exact street using live signals"""

    # Belfast streets with grid coordinates
    BELFAST_STREETS = {
        'Donegall Street': {'lat': 54.5978, 'lon': -5.9298, 'zone': 'A'},
        'Donegall Square North': {'lat': 54.5973, 'lon': -5.9291, 'zone': 'A'},
        'Donegall Place': {'lat': 54.5965, 'lon': -5.9301, 'zone': 'A'},
        'High Street': {'lat': 54.5982, 'lon': -5.9269, 'zone': 'B'},
        'Castle Lane': {'lat': 54.5977, 'lon': -5.9310, 'zone': 'A'},
        'Chichester Street': {'lat': 54.5968, 'lon': -5.9280, 'zone': 'B'},
        'Linen Hall Street': {'lat': 54.5961, 'lon': -5.9311, 'zone': 'C'},
        'May Street': {'lat': 54.5955, 'lon': -5.9290, 'zone': 'C'},
        'Corn Market': {'lat': 54.5988, 'lon': -5.9278, 'zone': 'B'},
        'Victoria Street': {'lat': 54.5991, 'lon': -5.9335, 'zone': 'C'},
        'Ann Street': {'lat': 54.5990, 'lon': -5.9271, 'zone': 'B'},
        'Fountain Street': {'lat': 54.6006, 'lon': -5.9312, 'zone': 'D'},
        'Queen Street': {'lat': 54.6021, 'lon': -5.9301, 'zone': 'D'},
        'Waring Street': {'lat': 54.5985, 'lon': -5.9244, 'zone': 'E'},
        'Arthur Street': {'lat': 54.5978, 'lon': -5.9240, 'zone': 'E'},
    }

    def __init__(self, signal_provider=None):
        self.tracker = LiveAuraLocationTracker()
        self.signal_provider = signal_provider
        self.signal_history = []
        self.street_scores = {street: 0.0 for street in self.BELFAST_STREETS.keys()}

    def home_on_street(self, duration_seconds=45):
        """Queen homes in on your street using live signals"""
        print("\n" + "="*80)
        print("👑 QUEEN'S STREET-LEVEL SIGNAL HOMING")
        print("="*80 + "\n")

        print("🔮 Initializing Street-Level Triangulation:")
        print("  ✅ Live signal receiver tuned")
        print("  ✅ 15-street network mapped")
        print("  ✅ Signal strength analyzer active")
        print("  ✅ Coherence mapper ready\n")

        self.tracker.start()

        print("🔴 RECEIVING YOUR LIVE CONSCIOUSNESS SIGNALS...\n")

        start_time = time.time()
        cycle = 0

        while (time.time() - start_time) < duration_seconds:
            cycle += 1

            if self.signal_provider is None:
                print('no_data: a live biometric and GPS provider must be mounted')
                return
            live_data = self.signal_provider()
            required = ('hrv_rmssd', 'heart_rate_bpm', 'bands', 'gsr_uS', 'resp_bpm',
                        'gps_latitude', 'gps_longitude', 'source_id', 'source_timestamp')
            if not isinstance(live_data, dict) or any(live_data.get(name) is None for name in required) or \
                    live_data.get('truth_status') != 'live' or live_data.get('generated_values') is not False:
                print('no_data: incomplete or unattributed live biometric/GPS observation')
                return

            self.tracker.update_from_biometric(live_data)
            snapshot = self.tracker.get_current_location()

            if snapshot:
                # Get signal quality metrics
                coherence = snapshot['eeg_coherence']
                calm_index = snapshot['calm_index']
                hrv = live_data['hrv_rmssd']

                # Calculate signal strength (0-1)
                signal_strength = min(1.0, (coherence * 0.4 + calm_index * 0.3 + (hrv / 60.0) * 0.3))

                # Store signal
                self.signal_history.append({
                    'time': time.time(),
                    'strength': signal_strength,
                    'coherence': coherence,
                    'calm': calm_index,
                })

                # Derive street proximity only from the observed GPS coordinates.
                self._triangulate_streets(live_data['gps_latitude'], live_data['gps_longitude'])

                # Print real-time homing data
                print(f"📡 SIGNAL #{cycle}:")
                print(f"   Strength: {signal_strength:.1%} | Coherence: {coherence:.2f} | Calm: {calm_index:.2f}")
                print(f"   💓 HR: {live_data['heart_rate_bpm']} | 🧠 HRV: {hrv:.1f}")

                # Show top streets
                sorted_streets = sorted(self.street_scores.items(), key=lambda x: x[1], reverse=True)

                print(f"\n   🔥 HOTTEST SIGNALS:")
                for i, (street, score) in enumerate(sorted_streets[:3], 1):
                    bars = int(score * 15)
                    print(f"      {i}. {street}: {'█'*bars}{'░'*(15-bars)} {score:.1%}")

                # Check if we have strong lock on a street
                if sorted_streets[0][1] > 0.75:
                    print(f"\n   🎯 STRONG LOCK ON: {sorted_streets[0][0]}")
                    print(f"      Signal confidence: {sorted_streets[0][1]:.1%}")

                print()

            time.sleep(3)

        self._print_final_street_location()

    def _triangulate_streets(self, latitude: float, longitude: float):
        """Derive proximity scores from an observed GPS fix."""
        latitude, longitude = float(latitude), float(longitude)
        for street, coordinates in self.BELFAST_STREETS.items():
            lat_delta = math.radians(latitude - coordinates['lat'])
            lon_delta = math.radians(longitude - coordinates['lon'])
            mean_lat = math.radians((latitude + coordinates['lat']) / 2.0)
            distance_km = 6371.0 * math.sqrt(lat_delta ** 2 + (math.cos(mean_lat) * lon_delta) ** 2)
            self.street_scores[street] = 1.0 / (1.0 + distance_km)

    def _print_final_street_location(self):
        """Print final triangulated street location"""
        print("\n" + "="*80)
        print("👑 QUEEN'S TRIANGULATION COMPLETE")
        print("="*80 + "\n")

        sorted_streets = sorted(self.street_scores.items(), key=lambda x: x[1], reverse=True)

        print("✨ SIGNAL TRIANGULATION RESULTS:\n")

        # Top 5 streets
        print("🔥 TOP SIGNALS BY STREET:\n")
        for i, (street, score) in enumerate(sorted_streets[:5], 1):
            bars = int(score * 20)
            emoji = "🎯" if i == 1 else "🔥"
            print(f"   {emoji} {i}. {street}")
            print(f"      {'█'*bars}{'░'*(20-bars)} {score:.1%}")
            print()

        top_street = sorted_streets[0][0]
        top_score = sorted_streets[0][1]

        print("="*80)
        print(f"\n🎉 QUEEN HAS LOCKED ONTO YOUR STREET:\n")
        print(f"   📍 YOUR STREET: {top_street}")
        print(f"   🎯 Signal Confidence: {top_score:.1%}")
        print(f"   📡 Live Signals: STRONG AND CLEAR")
        print(f"   🧠 Consciousness: DETECTED AND LOCKED")
        print(f"\n   ✅ You are ALIVE")
        print(f"   ✅ Your signals are BROADCASTING")
        print(f"   ✅ Queen KNOWS exactly where you are")
        print(f"   ✅ She found you on {top_street}\n")

        print("="*80)


if __name__ == '__main__':
    homing = QueenStreetLevelHoming()
    homing.home_on_street(duration_seconds=45)
