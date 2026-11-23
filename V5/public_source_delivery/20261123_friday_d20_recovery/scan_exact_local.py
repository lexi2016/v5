"""Find exact Friday TDX members in on-disk raw files and ZIPs without modifying inputs."""
import hashlib, json, os, re, struct, sys, zipfile, zlib
from collections import defaultdict
from pathlib import Path
root = Path(sys.argv[1]).resolve()
work = Path(__file__).resolve().parent
mapp = work.parent/'d20_actual_candidate_restore_20261122/D20_NATIVE_RESIDUAL_199_SOURCE_MAP_20261122.json'
raw = mapp.read_bytes()
rows = {x['symbol']:x for x in json.loads(raw)['rows']}
wanted = defaultdict(list)
for s,r in rows.items():
    wanted[(r['native_bytes'],int(r['crc32'],16))].append(s)
found, prior = {}, defaultdict(set)
archives, raw_files, errors = 0, 0, []
def add(blob,path):
    cands=wanted.get((len(blob),zlib.crc32(blob)))
    if not cands or len(cands)!=1 or struct.unpack_from('<I',blob,len(blob)-32)[0]!=20261120:
        return
    s=cands[0]
    found.setdefault(s,dict(loc=path,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),crc32=rows[s]['crc32'],evidence='ZIP_CENTRAL_DIRECTORY_SIZE_AND_CRC_MATCH',formal=False))
for parent, dirs, names in os.walk(root,followlinks=False):
    dirs[:]=[x for x in dirs if not x.startswith('.') and x not in ('venv','node_modules','__pycache__')]
    for name in names:
        p=Path(parent)/name
        if p.is_symlink() or not p.is_file(): continue
        if name.lower().endswith('.day'):
            raw_files+=1
            try:
                blob=p.read_bytes()
                if blob and len(blob)%32==0:
                    add(blob,str(p.relative_to(root)))
                    date=struct.unpack_from('<I',blob,len(blob)-32)[0]
                    token=name[:-4].upper()
                    symbol=token if token in rows else token[2:]+'.'+token[:2] if re.fullmatch(r'(SH|SZ|BJ)\d{6}',token) else ''
                    if symbol in rows:
                        prior[symbol].add(date)
            except (OSError, struct.error) as e:
                errors.append(str(p.relative_to(root))+':'+type(e).__name__)
        elif name.lower().endswith('.zip'):
            archives+=1
            try:
                with zipfile.ZipFile(p) as z:
                    for info in z.infolist():
                        if (info.file_size,info.CRC) in wanted and info.filename.lower().endswith('.day'):
                            add(z.read(info),str(p.relative_to(root))+'!'+info.filename)
            except (OSError, RuntimeError, zipfile.BadZipFile) as e:
                errors.append(str(p.relative_to(root))+':'+type(e).__name__)
print(json.dumps(dict(data_date='2026-11-20',scope=len(rows),map_sha256=hashlib.sha256(raw).hexdigest(),zip_count=archives,raw_file_count=raw_files,exact_matches=found,raw_tails_for_target_symbols={s:sorted(v) for s,v in sorted(prior.items())},errors=errors,formal=False),ensure_ascii=False,indent=2))
