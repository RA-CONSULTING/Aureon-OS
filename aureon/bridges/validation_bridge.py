#!/usr/bin/env python3
"""
Validation Bridge - Coordinates both Schumann and Aura validators
Manages the 10-minute live proof protocol and data synchronization
"""

from aureon.core.aureon_baton_link import link_system as _baton_link
import subprocess
import json
import time
import threading
import queue
import sys
import math
from pathlib import Path

class ValidationBridge:
    def __init__(self):
        self.auris_process = None
        self.aura_process = None
        self.data_queue = queue.Queue()
        self.running = False
        self.epoch = 0
        self.current_label = "baseline"
        
    def start_validators(self):
        """Explicitly start both validator processes after construction."""
        try:
            _baton_link(__name__)
            # Start Auris validator
            self.auris_process = subprocess.Popen(
                [sys.executable, 'validator_auris.py'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            
            # Start Aura validator  
            self.aura_process = subprocess.Popen(
                [sys.executable, 'aura_validator.py'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            
            print("✓ Both validators started successfully")
            self.running = True
            return True
            
        except Exception as e:
            print(f"✗ Failed to start validators: {e}")
            return False
    
    def stop_validators(self):
        """Stop both validator processes"""
        self.running = False
        
        if self.auris_process:
            self.auris_process.terminate()
            self.auris_process.wait()
            
        if self.aura_process:
            self.aura_process.terminate()
            self.aura_process.wait()
            
        print("✓ Validators stopped")
    
    def send_auris_data(self, sample_data, fund_hz=7.83, harmonics=None, gain=1.0, receipt=None):
        """Send data to Auris validator"""
        if not self.auris_process or not self.running:
            return
            
        if harmonics is None:
            harmonics = [7.83, 14.3, 20.8, 27.3, 33.8]
            
        data = {
            "t": receipt["source_timestamp"] if receipt else time.time(),
            "epoch": self.epoch,
            "label": self.current_label,
            "sample": sample_data,
            "fund_hz": fund_hz,
            "harmonics": harmonics,
            "gain": gain
        }
        if receipt:
            data.update({
                "source_id": receipt["source_id"],
                "source_timestamp": receipt["source_timestamp"],
                "received_at": receipt["received_at"],
                "receipt_id": receipt["receipt_id"],
                "truth_status": receipt["truth_status"],
                "generated_values": receipt["generated_values"],
            })
        
        try:
            json_line = json.dumps(data) + "\n"
            self.auris_process.stdin.write(json_line)
            self.auris_process.stdin.flush()
        except Exception as e:
            print(f"Error sending Auris data: {e}")
    
    def send_aura_data(self, bands=None, hrv_rmssd=0.0, gsr_uS=0.0, resp_bpm=0.0, receipt=None):
        """Send data to Aura validator"""
        if not self.aura_process or not self.running:
            return
            
        if bands is None:
            bands = {"alpha": 0.5, "theta": 0.3, "beta": 0.2}
            
        data = {
            "t": receipt["source_timestamp"] if receipt else time.time(),
            "epoch": self.epoch,
            "label": self.current_label,
            "bands": bands,
            "hrv_rmssd": hrv_rmssd,
            "gsr_uS": gsr_uS,
            "resp_bpm": resp_bpm
        }
        if receipt:
            data.update({
                "source_id": receipt["source_id"],
                "source_timestamp": receipt["source_timestamp"],
                "received_at": receipt["received_at"],
                "receipt_id": receipt["receipt_id"],
                "truth_status": receipt["truth_status"],
                "generated_values": receipt["generated_values"],
            })
        
        try:
            json_line = json.dumps(data) + "\n"
            self.aura_process.stdin.write(json_line)
            self.aura_process.stdin.flush()
        except Exception as e:
            print(f"Error sending Aura data: {e}")
    
    def set_phase(self, epoch: int, label: str):
        """Update current validation phase"""
        self.epoch = epoch
        self.current_label = label
        print(f"Phase changed: Epoch {epoch} - {label}")
    
    @staticmethod
    def _no_data_protocol(blocker):
        return {
            "truth_status": "no_data",
            "actionable": False,
            "generated_values": False,
            "blocker": blocker,
            "receipts": [],
        }

    @staticmethod
    def _receipt_blocker(receipt, now, max_age_sec):
        required = (
            "source_id", "source_timestamp", "received_at", "receipt_id",
            "truth_status", "generated_values", "sample_data", "fund_hz",
            "harmonics", "gain", "bands", "hrv_rmssd", "gsr_uS", "resp_bpm",
        )
        if not isinstance(receipt, dict):
            return "invalid_receipt"
        missing = [key for key in required if receipt.get(key) is None]
        if missing:
            return "missing_receipt_fields:" + ",".join(missing)
        if receipt["truth_status"] != "real_observed":
            return "truth_status_not_real_observed"
        if receipt["generated_values"] is not False:
            return "generated_values_not_false"
        if not str(receipt["source_id"]).strip() or not str(receipt["receipt_id"]).strip():
            return "missing_source_or_receipt_id"
        try:
            source_timestamp = float(receipt["source_timestamp"])
            received_at = float(receipt["received_at"])
        except (TypeError, ValueError):
            return "invalid_receipt_time"
        if not all(math.isfinite(value) and value > 0 for value in (source_timestamp, received_at)):
            return "invalid_receipt_time"
        if source_timestamp > now + 5 or received_at > now + 5:
            return "future_receipt_time"
        if now - source_timestamp > max_age_sec or now - received_at > max_age_sec:
            return "stale_receipt"
        return ""

    def run_validation_protocol(self, receipts=None, max_age_sec=60.0):
        """Forward only fresh provider-observed receipts to explicitly started validators."""
        if not self.running:
            return self._no_data_protocol("validators_not_started")
        if not isinstance(receipts, list) or not receipts:
            return self._no_data_protocol("missing_provider_receipts")
        try:
            max_age_sec = float(max_age_sec)
        except (TypeError, ValueError):
            return self._no_data_protocol("invalid_freshness_window")
        if not math.isfinite(max_age_sec) or max_age_sec <= 0:
            return self._no_data_protocol("invalid_freshness_window")

        now = time.time()
        for receipt in receipts:
            blocker = self._receipt_blocker(receipt, now, max_age_sec)
            if blocker:
                return self._no_data_protocol(blocker)

        for receipt in receipts:
            self.set_phase(int(receipt.get("epoch", self.epoch)), str(receipt.get("label", self.current_label)))
            self.send_auris_data(
                receipt["sample_data"],
                fund_hz=receipt["fund_hz"],
                harmonics=receipt["harmonics"],
                gain=receipt["gain"],
                receipt=receipt,
            )
            self.send_aura_data(
                bands=receipt["bands"],
                hrv_rmssd=receipt["hrv_rmssd"],
                gsr_uS=receipt["gsr_uS"],
                resp_bpm=receipt["resp_bpm"],
                receipt=receipt,
            )

        return {
            "truth_status": "real_observed",
            "actionable": True,
            "generated_values": False,
            "receipts": [receipt["receipt_id"] for receipt in receipts],
        }

def main():
    bridge = ValidationBridge()
    
    try:
        if not bridge.start_validators():
            return 1
            
        # Run the validation protocol
        bridge.run_validation_protocol()
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        bridge.stop_validators()
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
