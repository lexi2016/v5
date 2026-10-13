"""Standalone M03 quote-only source chain; help never imports an owner."""
import argparse
import json
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True,
                        help='local USSourceRequest JSON; network capture defaults to disabled')
    args = parser.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
    from v5_shadow.us_source_daily import _request_from_dict, run_us_source
    try:
        values = json.loads(args.request.read_text())
        if values.get('market_snapshot_only', True) is not True:
            raise ValueError('M03_STANDALONE_MARKET_ONLY_REQUIRED')
        values['market_snapshot_only'] = True
        result = run_us_source(_request_from_dict(values))
        print(json.dumps(result, sort_keys=True))
        return 0 if result['status'] == 'VALIDATED_SOURCE_BINDING' else 3
    except Exception as exc:
        print(json.dumps({'status': 'FAILED', 'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
