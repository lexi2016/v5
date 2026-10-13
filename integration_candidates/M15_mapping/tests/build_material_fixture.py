"""Synthetic only: original producer, builder, archive store and native master."""
import sys,os,tempfile
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'runtime/V5/src'));sys.path.insert(0,str(BASE/'runtime/V5/tests'))
os.environ['V5_ARCHIVE_PRODUCER_SOURCE_ROOT']=str(BASE/'tests/producer_dependencies')
from test_archive_article_v2 import ArticleV2ChainTests
ArticleV2ChainTests.setUpClass()
x=ArticleV2ChainTests();x.root=BASE/'tests/fixtures/materials';x.root.mkdir(exist_ok=True)
x.capture_root=x.root/'capture';x.capture_root.mkdir(exist_ok=True)
(x.capture_root/'.v5-archive-acquisition').write_bytes(b'v5.archive-acquisition.v2\n')
x.output=x.root/'archive';x.output.mkdir(exist_ok=True);(x.output/'.v5-archive-article-v2').write_bytes(b'v5.archive-article.v2\n')
x.base=datetime.now(ZoneInfo('Asia/Shanghai')).replace(hour=0,minute=0,second=0,microsecond=0);x.day=x.base.strftime('%Y%m%d')
x.published=(x.base-timedelta(minutes=30)).isoformat();x.times=[(x.base+timedelta(microseconds=i+1)).isoformat() for i in range(4)]
x.topic_id='12345678901234567';x.body=x.synthetic_body(direct=True)
x.build_capture(x.capture_root,x.body);result=x.publish()
request=dict(target_date='20261014',now=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),inputs={})
# Existing helper derives identity date from the original context; it rejects
# historical target only relative to the explicit synthetic cutoff above.
x.bind_native_identity(request)
import json
(x.root/'fixture_context.json').write_text(json.dumps(dict(target_date=request['target_date'],cutoff=request['now']),indent=2))
print('PASS synthetic producer -> builder -> archive reader and native source fixture')
ArticleV2ChainTests.tearDownClass()
