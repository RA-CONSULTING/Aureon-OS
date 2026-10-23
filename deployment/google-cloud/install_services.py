"""Install the commissioning profile after complete authenticated restoration."""
import json, os, pathlib, pwd, shutil, subprocess, sys
from cloud_organ import ENABLED, DEFERRED

ROOT = pathlib.Path('/srv/aureon/runtime/workspace')
VENV = pathlib.Path('/srv/aureon/venv')
IMPORT = pathlib.Path('/srv/aureon/import')
if os.geteuid() != 0 or not (ROOT/'aureon_fusion'/'queen_mind.py').exists():
    raise RuntimeError('Run as root only after restoring the complete workspace')

# Preserve imported process metadata. PIDs and dormant settings belong to the
# original Windows host and cannot be applied to this new Linux host.
registry_file = ROOT/'aureon_fusion'/'state'/'organ_registry.json'
original = IMPORT/'original-organ-registry.json'
if registry_file.exists() and not original.exists():
    shutil.copy2(registry_file, original)
if not (IMPORT/'services-installed.json').exists():
    data={'organs': {name:{'pid':None,'dormant':False} for name in ENABLED}}
    data['organs'].update({name:{'pid':None,'dormant':True,'dormant_reason':reason} for name,reason in DEFERRED.items()})
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    registry_file.write_text(json.dumps(data, indent=2))

subprocess.run([str(VENV/'bin/python'), '-m', 'pip', 'install', '--disable-pip-version-check',
                '-r', str(ROOT/'aureon-os-upstream'/'requirements-linux.txt')], check=True)
subprocess.run([str(VENV/'bin/python'), '-m', 'pip', 'check'], check=True)
(IMPORT/'installed-python-packages.txt').write_text(subprocess.check_output([str(VENV/'bin/python'), '-m', 'pip', 'freeze'], text=True))
subprocess.run([str(VENV/'bin/python'), str(ROOT/'deployment/google-cloud/test_deployment_hold.py')], check=True,
               env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})

cache=pathlib.Path('/srv/aureon/cache')
cache.mkdir(exist_ok=True)
account=pwd.getpwnam('aureon')
os.chown('/srv/aureon', 0, account.pw_gid)
os.chmod('/srv/aureon', 0o750)
subprocess.run(['chmod', '-R', 'a+rX', str(VENV)], check=True)
for base in (ROOT.parent, cache):
    subprocess.run(['chown','-R',str(account.pw_uid)+':'+str(account.pw_gid),str(base)],check=True)
    os.chmod(base,0o750)

unit=f'''[Unit]
Description=Aureon Sero organ %i (commissioning HOLD)
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=4

[Service]
Type=simple
User=aureon
Group=aureon
WorkingDirectory={ROOT}
Environment=SERO_WORKSPACE={ROOT}
Environment=PYTHONPATH={ROOT}:{ROOT}/aureon-os-upstream
Environment=AUREON_DEPLOYMENT_HOLD=1
Environment=AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1
Environment=AUREON_AUDIT_MODE=1
Environment=AUREON_SELF_QUESTIONING_AI=0
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=XDG_CACHE_HOME={cache}
Environment=MPLCONFIGDIR={cache}/matplotlib
ExecStart={VENV}/bin/python {ROOT}/deployment/google-cloud/cloud_organ.py %i
Restart=on-failure
RestartSec=20
TimeoutStopSec=35
KillMode=control-group
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths={ROOT.parent} {cache}
CapabilityBoundingSet=
RestrictSUIDSGID=true
LockPersonality=true
RestrictRealtime=true
TasksMax=256
Slice=aureon.slice

[Install]
WantedBy=multi-user.target
'''
pathlib.Path('/etc/systemd/system/aureon-organ@.service').write_text(unit)
pathlib.Path('/etc/systemd/system/aureon.slice').write_text('[Slice]\nMemoryMax=6500M\nTasksMax=1800\n')
for name in ('queen_mind','hnc_core','soul_protection_daemon','sero_autonomous_expansion','aureon_radar_bridge','mind_neural_canvas'):
    dropin=pathlib.Path('/etc/systemd/system')/('aureon-organ@'+name+'.service.d')
    dropin.mkdir(exist_ok=True)
    (dropin/'network.conf').write_text('[Service]\nIPAddressDeny=any\nIPAddressAllow=localhost\n')
subprocess.run(['systemd-analyze','verify','/etc/systemd/system/aureon-organ@.service'], check=True)
subprocess.run(['systemctl','daemon-reload'], check=True)
for name in ENABLED:
    subprocess.run(['systemctl','enable','--now','aureon-organ@'+name+'.service'], check=True)
(IMPORT/'services-installed.json').write_text(json.dumps({'enabled':ENABLED,'deferred':DEFERRED,'deployment_hold':True},indent=2))
print('Commissioning services installed; validate liveness and outputs before declaring ready', flush=True)
