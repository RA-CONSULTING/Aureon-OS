from pathlib import Path
import json,re,subprocess
ROOT=Path(__file__).resolve().parent.parent
hist=json.loads((ROOT/'work/git-history-versions-utc.json').read_text())
selected={}
for e in hist:
    path=e.get('path','')
    if re.search(r'maeshowe|celtic|ogham|coligny|starwheel|legacy.system|ancient.convergence|sacred.calendar|dormant|runes.stars|dual.wheel',path,re.I):
        selected.setdefault(path,[]).append(e)
out=ROOT/'outputs/legacy-system-code-paths-20260912.json'
out.write_text(json.dumps(selected,indent=2)+'\n')
for path,versions in selected.items():
    if not re.search(r'grants/applications|\.docx|\.pdf|\.pyc|node_modules',path,re.I):
        print(json.dumps({'path':path,'versions':len(versions),'first':versions[0]},ensure_ascii=False))
print('TOTAL_MATCHED_PATHS',len(selected))
remote="git --git-dir=/projects/u6vs/hnc-organism/repo/Aureon-OS.git ls-tree -r --name-only d6cc2e5ef82fca17f194e314889daa366f24d817"
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=30','u6vs.aip2.isambard',remote],capture_output=True,check=True,timeout=55)
paths=[p for p in r.stdout.decode().splitlines() if re.search(r'maeshowe|celtic|ogham|coligny|starwheel|legacy.system|ancient.convergence|sacred.calendar|dormant|runes.stars|dual.wheel',p,re.I)]
(ROOT/'outputs/legacy-system-current-paths-20260912.json').write_text(json.dumps(paths,indent=2)+'\n')
print('CURRENT_NON_DOCUMENT_PATHS')
for p in paths:
    if not re.search(r'grants/applications|\.docx|\.pdf|\.pyc',p,re.I):print(p)
