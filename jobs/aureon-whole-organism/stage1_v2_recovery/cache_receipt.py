"""Verify compiler caches stay in a new allocation-local tree."""
import argparse,json,os,shutil,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--ready',action='store_true');a=p.parse_args()
    base=Path(os.environ['STAGE1_CACHE_BASE']).resolve();local=Path(os.environ['LOCALDIR']).resolve()
    assert local in base.parents and base.is_dir()
    assert base.name.startswith('stage1-v2-'+os.environ['SLURM_JOB_ID']+'.')
    kind=subprocess.check_output(['stat','-f','--format=%T',str(base)],text=True).strip()
    assert kind in ('tmpfs','ext2/ext3','ext4','xfs','btrfs'),('Cache is not a verified local filesystem',kind)
    free=shutil.disk_usage(base).free;assert free>2*1024**3,('Insufficient cache space',free)
    paths={k:Path(os.environ[k]).resolve() for k in ['VLLM_CACHE_ROOT','TRITON_CACHE_DIR','TORCHINDUCTOR_CACHE_DIR']}
    assert all(base in path.parents for path in paths.values())
    ranks=sorted(paths['VLLM_CACHE_ROOT'].glob('torch_compile_cache/*/rank_*'))
    if a.ready:
        assert {p.name for p in ranks}=={'rank_0_0','rank_1_0','rank_2_0','rank_3_0'},ranks
        assert all(base in p.resolve().parents for p in ranks)
    result=dict(cache_base=str(base),localdir=str(local),filesystem=kind,free_bytes=free,
                environment={k:str(v) for k,v in paths.items()},rank_cache_paths=[str(p) for p in ranks],
                runtime_rank_paths_checked=a.ready)
    Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
