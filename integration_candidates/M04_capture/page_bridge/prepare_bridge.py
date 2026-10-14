"""Write a standalone bridge candidate only when the original preimage matches."""
import argparse,hashlib,json
from pathlib import Path
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 here=Path(__file__).resolve().parent;identity=json.loads((here/'BRIDGE_IDENTITY.json').read_bytes())
 source=Path(a.source)
 if source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest()!=identity['original_sha256']:raise ValueError('RESEARCH_BRIDGE_PREIMAGE_MISMATCH')
 raw=(here/'research_workbench_readonly.py').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=identity['candidate_sha256']:raise ValueError('RESEARCH_BRIDGE_CANDIDATE_SHA')
 with Path(a.output).open('xb') as stream:stream.write(raw)
