"""Operator-only explicit CLI. Read does not produce, initialize or regenerate."""
import argparse
import hashlib
import json
from pathlib import Path
from .daily import M11Binding,capture,generate,read_owner_day
from .owner_sources import safe_root_class


def main(argv=None):
    p=argparse.ArgumentParser(description='M11 original research owner, private V5 binding')
    p.add_argument('--binding-file',type=Path,required=True)
    p.add_argument('--binding-sha256',required=True)
    sub=p.add_subparsers(dest='operation',required=True)
    for name in ('read','capture','generate'):
        cmd=sub.add_parser(name);cmd.add_argument('--date',required=True)
        if name!='read':
            cmd.add_argument('--cutoff',required=True);cmd.add_argument('--run-id',required=True)
            cmd.add_argument('--sources-file',type=Path,required=True);cmd.add_argument('--sources-sha256',required=True)
        if name=='capture':cmd.add_argument('--slot',required=True,choices=('09:25','09:35','10:00','11:30','14:00','15:00'))
    a=p.parse_args(argv)
    try:
        raw=safe_root_class()(a.binding_file.parent).read_bytes(a.binding_file.name)
        if hashlib.sha256(raw).hexdigest()!=a.binding_sha256:raise ValueError('binding SHA mismatch')
        values=json.loads(raw)
        if set(values)!={'state_root','archive_root','config_path','config_sha256','owner_manifest_sha256'}:raise ValueError('binding fields')
        for key in ('state_root','archive_root','config_path'):values[key]=Path(values[key])
        binding=M11Binding(**values)
        if a.operation=='read':result=read_owner_day(binding,a.date)
        else:
            source_raw=safe_root_class()(a.sources_file.parent).read_bytes(a.sources_file.name)
            if hashlib.sha256(source_raw).hexdigest()!=a.sources_sha256:raise ValueError('source times SHA mismatch')
            args={'target_date':a.date,'cutoff':a.cutoff,'run_id':a.run_id,'sources':json.loads(source_raw)}
            if a.operation=='capture':result=capture(binding,slot=a.slot,**args)
            else:result=generate(binding,**args)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,allow_nan=False))
        return 2 if result.get('status')=='BLOCKED' else 0
    except (ValueError,TypeError,OSError,KeyError):
        print(json.dumps({'status':'BLOCKED','error_code':'M11_CLI_BINDING_OR_INPUT_REFUSED','orders_sent':False}))
        return 2


if __name__=='__main__':raise SystemExit(main())
