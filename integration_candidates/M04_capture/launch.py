#!/usr/bin/env python3
"""Run from any working directory using the existing approved interpreter."""
import argparse,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import capture_runtime as runtime

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('command',choices=['validate','init','capture','resume','read','lane'])
 parser.add_argument('--date');parser.add_argument('--slot');parser.add_argument('--run-id')
 parser.add_argument('--research-date')
 parser.add_argument('--execute-acquisition',action='store_true')
 args=parser.parse_args()
 try:
  runtime.verify_sources()
  raw=sys.stdin.buffer.read(runtime.MAX_JSON_BYTES+1)
  if len(raw)>runtime.MAX_JSON_BYTES:raise ValueError('REQUEST_SIZE')
  data=json.loads(raw)
  if args.command=='validate':runtime.validate(data);out={'status':'VALID_CONFIG','real_acquisition':'NOT_RUN',**runtime.SAFETY}
  elif args.command=='init':out=runtime.initialize(data)
  elif args.command=='read':out=runtime.materials(data)
  elif args.command=='lane':
   from research_lane import research_lane
   out=research_lane(data,{'research_date':args.research_date} if args.research_date is not None else {})
  elif args.command=='resume':out=runtime.resume(data,args.run_id)
  else:
   if not args.execute_acquisition:raise ValueError('EXPLICIT_ACQUISITION_REQUIRED')
   out=runtime.capture(data,args.date,args.slot,args.run_id)
  print(runtime.canonical_bytes(out).decode());return 0
 except Exception as exc:
  print(json.dumps({'status':'FAILED','reason':type(exc).__name__+':'+str(exc),**runtime.SAFETY}));return 1
if __name__=='__main__':raise SystemExit(main())
