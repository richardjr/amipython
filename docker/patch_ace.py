#!/usr/bin/env python3
"""Patch ACE system.c for CLI compatibility.

ACE's systemCreate() unconditionally dereferences _WBenchMsg, which is
NULL when launched from CLI. This patch adds a NULL guard.
"""
import sys

path = sys.argv[1]
with open(path) as f:
    code = f.read()

code = code.replace(
    's_bpStartLock = CurrentDir(_WBenchMsg->sm_ArgList[0].wa_Lock);',
    'if(_WBenchMsg) { s_bpStartLock = CurrentDir(_WBenchMsg->sm_ArgList[0].wa_Lock); }'
)

with open(path, 'w') as f:
    f.write(code)

print("Patch applied successfully")
