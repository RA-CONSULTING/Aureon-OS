"""Keep one registry-owned organ under systemd supervision."""
import os, signal, sys, threading

ENABLED = (
    'real_time_data_feeder', 'schumann_real_daemon', 'planetary_monitor_daemon',
    'solar_system_collector', 'sero_space_weather', 'sero_autonomous_expansion',
    'aureon_radar_bridge', 'hnc_core', 'soul_protection_daemon',
    'mind_neural_canvas', 'queen_mind', 'heartbeat_daemon',
)
DEFERRED = {
    'aureon_radar_suite': 'Live trading remains on deployment HOLD',
    'mind_thought_action_hub': 'Action endpoints require a separate activation review',
    'self_questioning_ai': 'Requires Ollama; native Queen reasoning is active separately',
}

def main():
    if os.environ.get('AUREON_DEPLOYMENT_HOLD') != '1':
        raise RuntimeError('This commissioning service requires deployment HOLD')
    name = sys.argv[1]
    if name not in ENABLED:
        raise RuntimeError('Organ is outside this commissioning service profile')
    import psutil
    from aureon_fusion import organ_registry as registry
    stopped = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())
    result = registry.start(name)
    if result.get('state') != 'started':
        print('Organ startup refused: '+str(result.get('state')), flush=True)
        return 1
    process = psutil.Process(result['pid'])
    print('Registry started '+name+' pid='+str(process.pid), flush=True)
    try:
        while not stopped.wait(3):
            if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
                return 1
    finally:
        registry.stop(name)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
