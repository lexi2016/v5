"""Private registered delivery adapter. Empty registry; no network implementation.
Accepted != delivered. Unknown attempts never automatically retry.
Original owner context must hold its existing locks/resources/authorization.
"""
import hashlib,json,sqlite3,datetime as dt
from pathlib import Path
REGISTRY={}
NODES=('0810','1700','1900')
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def _config(key):
    if key not in REGISTRY:raise ValueError('NO_REVIEWED_DELIVERY_BINDING')
    c=REGISTRY[key]
    if c.get('authorized') is not True or c.get('node') not in NODES or not all(c.get(k) for k in ('task_id','environment_id','binding_version','authorization_ref','channel','destination','input_sha256','code_version','data_date','run_id')):raise ValueError('INCOMPLETE_AUTHORIZED_IDENTITY')
    if dt.datetime.strptime(c['data_date'],'%Y%m%d').strftime('%Y%m%d')!=c['data_date']:raise ValueError('DATE')
    if c['channel']!='chatgpt':raise ValueError('UNREVIEWED_CHANNEL')
    return c

def _connection(c):
    p=Path(c['output_root'])
    if not p.is_dir() or p.is_symlink() or p.resolve()!=p.absolute():raise ValueError('OUTPUT_ROOT')
    f=p/'outbox.sqlite3'
    if f.is_symlink():raise ValueError('DATABASE_SYMLINK')
    db=sqlite3.connect(f,timeout=0,isolation_level=None)
    db.execute('PRAGMA synchronous=FULL')
    db.execute('CREATE TABLE IF NOT EXISTS items (key TEXT PRIMARY KEY, identity BLOB NOT NULL, payload BLOB NOT NULL, state TEXT NOT NULL, receipt BLOB, updated TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, key TEXT NOT NULL, state TEXT NOT NULL, evidence BLOB, at TEXT NOT NULL)')
    return db

def _identity(c,body):
    return {k:c[k] for k in ('task_id','node','environment_id','binding_version','authorization_ref','channel','destination','input_sha256','code_version','data_date')}|{'payload_sha256':sha(body)}

def _key(identity):
    return sha(canonical({k:identity[k] for k in ('task_id','node','channel','destination','data_date','input_sha256','payload_sha256')}))

def _transition(db,key,state,evidence=None):
    raw=canonical(evidence) if evidence is not None else None
    db.execute('BEGIN IMMEDIATE')
    try:
        db.execute('UPDATE items SET state=?,receipt=?,updated=? WHERE key=?',(state,raw,now(),key))
        db.execute('INSERT INTO events(key,state,evidence,at) VALUES(?,?,?,?)',(key,state,raw,now()))
        db.execute('COMMIT')
    except BaseException:
        db.execute('ROLLBACK');raise

def prepare(registration_id,text):
    c=_config(registration_id)
    if not isinstance(text,str) or not text.strip():raise ValueError('EMPTY_MESSAGE')
    body=text.encode();identity=_identity(c,body);raw=canonical(identity);key=_key(identity)
    with c['owner_context']():
        if c['gate']() is not True:raise ValueError('ORIGINAL_GATE_FAILED')
        db=_connection(c)
        try:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT identity,payload,state FROM items WHERE key=?',(key,)).fetchone()
            if row:
                if row[:2]!=(raw,body):raise ValueError('OUTBOX_CHANGED')
                _,state,_=_read(db,c,key)
                reused=True
            else:
                db.execute('INSERT INTO items VALUES(?,?,?,?,?,?)',(key,raw,body,'PREPARED',None,now()))
                db.execute('INSERT INTO events(key,state,at) VALUES(?,?,?)',(key,'PREPARED',now()))
                reused=False;state='PREPARED'
            db.execute('COMMIT')
            return {'key':key,'state':state,'reused':reused,'sent':False,'delivery_verified':False}
        except BaseException:
            if db.in_transaction:db.execute('ROLLBACK')
            raise
        finally:db.close()

def _read(db,c,key):
    row=db.execute('SELECT identity,payload,state,receipt FROM items WHERE key=?',(key,)).fetchone()
    if not row:raise ValueError('NOT_PREPARED')
    raw,body,state,receipt=row
    if raw!=canonical(_identity(c,body)) or _key(json.loads(raw))!=key:raise ValueError('INPUT_OR_BINDING_CHANGED')
    latest=db.execute('SELECT state,evidence FROM events WHERE key=? ORDER BY id DESC LIMIT 1',(key,)).fetchone()
    if latest is None or latest!=(state,receipt):raise ValueError('STATE_JOURNAL_MISMATCH')
    if state not in ('PREPARED','ATTEMPT_UNKNOWN','ACCEPTED','DELIVERED_VERIFIED'):raise ValueError('INVALID_STATE')
    parsed=json.loads(receipt) if receipt else None
    if state in ('ACCEPTED','DELIVERED_VERIFIED') and (not isinstance(parsed,dict) or not parsed.get('message_id') or parsed.get('channel')!=c['channel'] or parsed.get('destination')!=c['destination'] or parsed.get('payload_sha256')!=sha(body)):raise ValueError('RECEIPT_INVALID')
    return body,state,parsed

def attempt(registration_id,key):
    c=_config(registration_id)
    with c['owner_context']():
        if c['gate']() is not True:raise ValueError('ORIGINAL_GATE_FAILED')
        db=_connection(c)
        try:
            body,state,receipt=_read(db,c,key)
            if state!='PREPARED':return {'key':key,'state':state,'attempted':False,'reason':'NO_AUTOMATIC_RESEND','delivery_verified':False}
            # Durable pre-send marker: a crash after this point requires reconciliation.
            _transition(db,key,'ATTEMPT_UNKNOWN',{'started_at':now(),'run_id':c['run_id'],'environment_id':c['environment_id']})
            try:
                result=c['sender'](channel=c['channel'],destination=c['destination'],text=body.decode())
                # Normalized trusted connector receipt, not a job's arbitrary output.
                if not isinstance(result,dict) or result.get('channel')!=c['channel'] or result.get('destination')!=c['destination'] or result.get('status')!='accepted' or not isinstance(result.get('message_id'),str) or not result['message_id']:raise ValueError('UNCONFIRMED_ACCEPTANCE')
                accepted={k:result[k] for k in ('channel','destination','status','message_id')}
                accepted['payload_sha256']=sha(body)
                _transition(db,key,'ACCEPTED',accepted)
                return {'key':key,'state':'ACCEPTED','message_id':accepted['message_id'],'attempted':True,'delivery_verified':False}
            except Exception as e:
                _transition(db,key,'ATTEMPT_UNKNOWN',{'error_type':type(e).__name__,'reconciliation_required':True})
                return {'key':key,'state':'ATTEMPT_UNKNOWN','attempted':True,'delivery_verified':False}
        finally:db.close()

def reconcile(registration_id,key):
    c=_config(registration_id)
    with c['owner_context']():
        if c['gate']() is not True:raise ValueError('ORIGINAL_GATE_FAILED')
        db=_connection(c)
        try:
            body,state,receipt=_read(db,c,key)
            if state=='PREPARED':return {'key':key,'state':state,'delivery_verified':False}
            proof=c['reconciler'](identity=_identity(c,body),receipt=receipt)
            # Absence in a search is not proof of failed send; no retry/reset here.
            if not isinstance(proof,dict) or proof.get('delivery_confirmed') is not True or proof.get('payload_sha256')!=sha(body) or proof.get('channel')!=c['channel'] or proof.get('destination')!=c['destination'] or not proof.get('message_id') or not proof.get('evidence_ref'):
                return {'key':key,'state':state,'delivery_verified':False,'reason':'NO_EXPLICIT_DELIVERY_EVIDENCE'}
            if state in ('ACCEPTED','DELIVERED_VERIFIED') and proof['message_id']!=receipt['message_id']:raise ValueError('MESSAGE_ID_MISMATCH')
            _transition(db,key,'DELIVERED_VERIFIED',proof)
            return {'key':key,'state':'DELIVERED_VERIFIED','message_id':proof['message_id'],'delivery_verified':True}
        finally:db.close()
