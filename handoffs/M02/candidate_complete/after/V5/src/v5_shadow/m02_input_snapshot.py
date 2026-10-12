"""M02-only extraction of fixed-F manager_plan._snapshot and input limits.

Original shared helpers remain authoritative. No manager/announcement business
module is imported. See handoffs/M02/candidate_complete/SOURCE_MAP.json.
"""
import hashlib
import os
import re
from v5_shadow.a_preselection import _relative
from v5_shadow.composition import no_symlinks
from v5_shadow.contracts import sha
from v5_shadow.digests import MAX_JSON_BYTES
from v5_shadow.module_api import _open_directory, _read_regular


def input_limit(relative):
    return 32 * 1024 * 1024 if re.fullmatch(
        r'announcement_agent_runs/[0-9a-f]{32}/evidence/body_corpus\.json', relative
    ) else MAX_JSON_BYTES


def snapshot(binding):
    if not isinstance(binding, dict) or set(binding) != {'root', 'files'} or not isinstance(binding['files'], dict):
        raise ValueError('M02_INPUT_BINDING')
    root = no_symlinks(binding['root'])
    result = {}; total = 0
    for relative, digest in binding['files'].items():
        sha(digest)
        path = _relative(root, relative)
        directory = _open_directory(path.parent)
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        finally:
            os.close(directory)
        try:
            raw = _read_regular(fd, input_limit(relative))
        finally:
            os.close(fd)
        total += len(raw)
        if total > 64 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('MANAGER_INPUT_SHA_OR_LIMIT')
        result[relative] = raw
    return result
