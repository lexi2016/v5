"""TEST ONLY: no real symbols, prices, source records or production input binding."""
from contextlib import ExitStack,contextmanager
from unittest.mock import patch
import json,observation_api as api
@contextmanager
def install():
 raw=json.dumps({'synthetic':True,'latest':{'rows':[{'id':'synthetic-a'},{'id':'synthetic-b'}],'analysis_admission':'NOT_GRANTED'}}).encode()
 with ExitStack() as stack:
  for name,value in {'HISTORY_SOURCE_DATE':'2000-01-01','HISTORY_DATE':'2000-01-02','HISTORY_SLOT':'1450','HISTORY_COUNT':2}.items():stack.enter_context(patch.object(api,name,value))
  stack.enter_context(patch.object(api,'load',return_value=(raw,{'synthetic_only':True})))
  yield
