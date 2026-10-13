"""Launch the existing read-only module API from an explicitly selected checkout."""
import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', required=True, help='Isolated complete P0 checkout after candidate application')
    parser.add_argument('--config', required=True, help='Existing isolated module API configuration')
    parser.add_argument('--port', type=int, default=0, help='Loopback port; 0 chooses a free port')
    args = parser.parse_args()
    raw = Path(args.checkout)
    if not raw.is_absolute() or '..' in raw.parts or any(p.is_symlink() for p in (raw, *raw.parents)):
        parser.error('checkout must be an absolute non-symlink path')
    source = raw / 'V5' / 'src'
    if any(p.is_symlink() for p in (source, *source.parents)):
        parser.error('checkout source must not traverse symlinks')
    if not (source / 'v5_shadow' / 'm14_readonly.py').is_file():
        parser.error('candidate must be applied to the selected complete checkout')
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source))
    from v5_shadow.module_api import main as entry
    return entry(['--config', args.config, '--port', str(args.port)])


if __name__ == '__main__':
    main()
