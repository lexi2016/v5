"""Read-only ResearchView projection of explicitly bound original daily archives.

Archive material is a distinct peripheral; never reclassified into an hourly,
morning-news, wechat, timeline, or stock-research-day product.
"""
from datetime import datetime
import hashlib
import json
import re
from pathlib import Path
import capture_runtime as runtime


def _display_article(article):
 # Add presentation only after original cold validation; preserve every stored
 # article field and never relabel the summary as original body or quotation.
 semantics=article.get('acquisition_v2',{}).get('evidence_semantics',{})
 if semantics.get('quote_status')!='NOT_A_SOURCE_QUOTE':return article
 if semantics.get('kind')!='ORIGINAL_BUILDER_SUMMARY':raise ValueError('RESEARCH_LANE_EVIDENCE_KIND')
 if 'summary' in article or 'summary_display_only' in article:raise ValueError('RESEARCH_LANE_DISPLAY_FIELD_COLLISION')
 return {**article,'summary':'原owner派生摘要（非原文引句）：'+article['evidence_sentence'],'summary_display_only':True}


def research_lane(binding,query):
 if not isinstance(query,dict) or set(query) not in (set(),{'research_date'}):raise ValueError('RESEARCH_LANE_QUERY')
 requested=query.get('research_date')
 if 'research_date' in query:
  if not isinstance(requested,str) or not re.fullmatch('[0-9]{8}',requested):raise ValueError('RESEARCH_LANE_DATE')
  try:datetime.strptime(requested,'%Y%m%d')
  except ValueError as exc:raise ValueError('RESEARCH_LANE_DATE') from exc
 checked,records,outside=runtime.verified_records(binding)
 days={key[:-1]:row for key,row in records.items() if key.endswith('/')}
 day=requested if requested is not None else (max(days) if days else '')
 gaps=['M04_OTHER_LANES_NOT_CONFIGURED']
 out={'schema_version':'v3_5.research_lane.v1','research_date':day,'endpoint_mode':'EXACT' if requested is not None else 'LATEST','status':'NOT_MATERIALIZED','reason':'M04_ARCHIVE_DATE_NOT_MATERIALIZED','cannot_confirm':gaps,'write_policy':'read_only','recommendation_status':'RESEARCH_ONLY','source_run_id':None,'archive_materials':None,'out_of_scope_record_errors':outside,**runtime.SAFETY}
 if day not in days:return out
 record=days[day];archive=record['payload'];identity=record['binding']
 if archive.get('archive_date')!=day:raise ValueError('RESEARCH_LANE_ARCHIVE_DATE')
 if archive.get('article_count')!=len(archive.get('articles',[])):raise ValueError('RESEARCH_LANE_ARTICLE_COUNT')
 for key in ('production_allowed','buy_gate_updated','orders_sent'):
  if archive.get(key) is not False:raise ValueError('RESEARCH_LANE_SAFETY')
 refs={'archive_binding':binding,'archive_date':day,'payload_path':identity['payload_path'],'payload_sha256':binding['files'][identity['payload_path']],'receipt_path':identity['receipt_path'],'receipt_sha256':binding['files'].get(identity['receipt_path']),'manifest_sha256':binding['files']['manifest.json'],'source_input_sha256':archive.get('source_input_sha256'),'source_generated_at':archive.get('source_generated_at'),'original_reader':{'source_capsule_sha256':checked['source_capsule_sha256'],'article_v2_source_sha256':checked['article_v2_source_sha256']}}
 receipt=archive.get('acquisition_receipt')
 if receipt:
  name=receipt['path'];raw=runtime._raw_file(Path(binding['root']),name)
  if binding['files'].get(name)!=receipt['sha256'] or hashlib.sha256(raw).hexdigest()!=receipt['sha256'] or len(raw)!=receipt['bytes']:raise ValueError('RESEARCH_LANE_ACQUISITION_REF')
  acquisition=json.loads(raw);out['source_run_id']=acquisition.get('run_id')
  refs.update(acquisition_receipt=receipt,acquisition_run_id=out['source_run_id'])
 if not out['source_run_id']:gaps.append('M04_SOURCE_RUN_UNKNOWN')
 articles=archive['articles']
 missing=sum(not a.get('retrieved_at') or a.get('retrieved_at')=='UNKNOWN' or not a.get('available_at') or a.get('available_at')=='UNKNOWN' for a in articles)
 if missing:gaps.append('M04_ARTICLE_ACQUISITION_TIME_UNKNOWN')
 gaps.extend(archive.get('cannot_confirm',[]))
 out.update(status='LIVE_PERIPHERAL_ONLY',reason='M04_BOUND_ARCHIVE_MATERIALS_ONLY',archive_materials={'status':archive.get('status'),'articles':[_display_article(a) for a in articles],'article_count':archive['article_count'],'acquisition_status':'UNKNOWN' if missing else 'RECORDED','missing_acquisition_time_count':missing,'source_reference':refs,'source_counts':archive.get('source_counts',{}),'cannot_confirm':archive.get('cannot_confirm',[])})
 return out
