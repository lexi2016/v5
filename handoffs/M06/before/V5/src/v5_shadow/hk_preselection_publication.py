from pathlib import Path
import json, os
def publish_reference(staging, final, receipts):
    staging=Path(staging); final=Path(final)
    if final.exists(): raise ValueError("M06_COMMIT_CONFLICT")
    staging.mkdir()
    for name,obj in receipts.items():
        (staging/name).write_text(json.dumps(obj,sort_keys=True))
    if final.exists(): raise ValueError("M06_COMMIT_CONFLICT")
    os.replace(staging,final)
    return {"committed_reference":str(final)}
