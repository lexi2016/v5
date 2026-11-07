"""Loopback-only historical observation reader; no current activation, sampling or mutation."""
import datetime as dt,hashlib,json,time,socket,threading
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
import safeio
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PINS_SHA=None
HISTORY_SOURCE_DATE=None;HISTORY_DATE=None;HISTORY_SLOT=None;HISTORY_COUNT=None
SAFEIO_SHA='facce7970f4919034d62e59dde8375e94d7a6a165de214f2e5178dbb5615fff5'
def sha(b):return hashlib.sha256(b).hexdigest()
def load():
 if sha(safeio.local_bytes(HERE,'safeio.py'))!=SAFEIO_SHA:raise ValueError('SAFEIO_CHANGED')
 if PINS_SHA is None:raise ValueError('PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING')
 raw=safeio.local_bytes(HERE,'INPUT_PINS.json')
 if sha(raw)!=PINS_SHA:raise ValueError('PINS_CHANGED')
 pins=json.loads(raw);objects={}
 for name,pin in pins.items():
  data=safeio.local_bytes(ROOT,pin['path'])
  if len(data)!=pin['bytes'] or sha(data)!=pin['sha256']:raise ValueError('INPUT_CHANGED')
  objects[name]=(data,json.loads(data))
 raw,view=objects['historical_view'];contract=objects['daily_contract'][1];s=view['latest']
 if s['schema']!='OBSERVATION_SNAPSHOT_VIEW_V1' or s['analysis_admission']!='NOT_GRANTED' or s['formula_review']!='PENDING':raise ValueError('HISTORICAL_SCOPE')
 if (s['source_date'],s['observation_date'],s['slot'])!=(HISTORY_SOURCE_DATE,HISTORY_DATE,HISTORY_SLOT):raise ValueError('HISTORICAL_DATE')
 if s['daily_contract_sha256']!=pins['daily_contract']['sha256'] or contract['count']!=HISTORY_COUNT or len(contract['symbols'])!=HISTORY_COUNT or len(set(contract['symbols']))!=HISTORY_COUNT:raise ValueError('CONTRACT_BINDING')
 symbols=[r['symbol'] for r in s['rows']]
 if len(symbols)!=HISTORY_COUNT or set(symbols)!=set(contract['symbols']):raise ValueError('MEMBERSHIP')
 if contract.get('formula_or_chart_admission') is not False or contract.get('carry_forward') is not False:raise ValueError('NO_CARRY_FORWARD_REQUIRED')
 return raw,pins

class BoundedHTTPServer(HTTPServer):
 """Synchronous read-only server with idle, absolute request and total deadlines."""
 def __init__(self,*args,**kwargs):
  self.active={};self.active_lock=threading.Lock();self.expired=threading.Event();self.deadline=None
  super().__init__(*args,**kwargs)
 def get_request(self):
  connection,address=super().get_request()
  if self.expired.is_set():connection.close();raise OSError('SERVER_LIFETIME_EXPIRED')
  connection.settimeout(0.25)
  remaining=1.0 if self.deadline is None else max(0.001,min(1.0,self.deadline-time.monotonic()))
  timer=threading.Timer(remaining,self.close_connection,args=(connection,));timer.daemon=True
  with self.active_lock:self.active[connection]=timer
  timer.start()
  # Catch expiry racing between accept and active registration.
  if self.expired.is_set():self.close_connection(connection)
  return connection,address
 def close_connection(self,connection):
  try:connection.shutdown(socket.SHUT_RDWR)
  except OSError:pass
 def shutdown_request(self,connection):
  with self.active_lock:timer=self.active.pop(connection,None)
  if timer is not None:timer.cancel()
  super().shutdown_request(connection)
 def expire(self):
  self.expired.set()
  with self.active_lock:connections=list(self.active)
  for connection in connections:self.close_connection(connection)
 def server_close(self):
  self.expire()
  with self.active_lock:timers=list(self.active.values())
  for timer in timers:timer.cancel()
  super().server_close()

def create_server(port=0):
 raw,pins=load();status={'schema':'ISOLATED_OBSERVATION_READER_STATUS_V1','historical_source_date':HISTORY_SOURCE_DATE,'historical_observation_date':HISTORY_DATE,'historical_count':HISTORY_COUNT,'historical_bytes_verified':True,'historical_refs':pins,'current_contract':'UNKNOWN_NOT_BOUND','current_activation':'UNKNOWN_NOT_BOUND','current_snapshot':'UNKNOWN_NOT_BOUND','collector_running':False,'ten_minute_sampling_restored':False,'production_integrated':False,'natural_verified':False,'source_calls':0,'mutation_routes':False}
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def send(self,code,data):
   self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Observation-Scope','historical-only-no-current-admission');self.end_headers();self.wfile.write(data)
  def same_origin(self):
   hosts={'127.0.0.1:'+str(self.server.server_port),'localhost:'+str(self.server.server_port)};host=self.headers.get('Host');origin=self.headers.get('Origin')
   return host in hosts and (origin is None or origin=='http://'+host)
  def do_GET(self):
   if not self.same_origin():return self.send(403,b'{"error":"LOOPBACK_SAME_ORIGIN_ONLY"}')
   if self.path=='/observations/history/'+str(HISTORY_DATE):return self.send(200,raw)
   if self.path=='/status':return self.send(200,safeio.canonical(status))
   if self.path=='/observations/current':return self.send(409,safeio.canonical({'status':'BLOCKED_CURRENT_BINDING_UNKNOWN','missing':['current-day exact frozen contract','independent review and activation receipt','current real bucket and source receipts','original collector deployment binding'],'historical_fallback_used':False,'current_rows':None,'natural_verified':False}))
   return self.send(404,b'{"error":"NOT_FOUND"}')
  def do_POST(self):self.send(405,b'{"error":"READ_ONLY_NO_IMPORT_OR_CAPTURE"}')
  do_PUT=do_POST;do_DELETE=do_POST;do_PATCH=do_POST
 return BoundedHTTPServer(('127.0.0.1',port),Handler)

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=0);p.add_argument('--serve-seconds',type=int,default=30);a=p.parse_args()
 if not 1<=a.serve_seconds<=300:p.error('manual isolated lifetime must be 1..300 seconds')
 server=create_server(a.port);server.timeout=0.05
 server.deadline=time.monotonic()+a.serve_seconds
 watchdog=threading.Timer(a.serve_seconds,server.expire);watchdog.daemon=True;watchdog.start()
 print(json.dumps({'url':'http://127.0.0.1:'+str(server.server_port),'scope':'MANUAL_ISOLATED_HISTORICAL_ONLY','collector_running':False,'started_at':dt.datetime.now(dt.timezone.utc).isoformat()}),flush=True)
 try:
  while not server.expired.is_set() and time.monotonic()<server.deadline:server.handle_request()
 finally:
  watchdog.cancel();server.server_close()
if __name__=='__main__':main()
