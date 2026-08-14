#!/usr/bin/env python3
"""Patch ACE system.c for CLI and Amiberry compatibility.

Patches applied:
1. NULL-guard _WBenchMsg dereference (crashes when launched from CLI)
2. Disable _ace_dbg file I/O (causes systemUnuse hang on Amiberry's
   virtual filesystem — the Open() call keeps disk DMA active, then
   systemFlushIo deadlocks waiting for the filesystem handler)

Every patch is verified: if an expected pattern is missing (upstream ACE
changed), the script exits non-zero so the Docker build fails loudly
instead of producing an image with the crash/deadlock reintroduced.
"""
import sys

path = sys.argv[1]
with open(path) as f:
    code = f.read()

errors = []

# Patch 1: NULL-guard _WBenchMsg. Required — an unguarded dereference
# crashes any binary launched from the CLI.
P1_ORIG = 's_bpStartLock = CurrentDir(_WBenchMsg->sm_ArgList[0].wa_Lock);'
P1_PATCHED = ('if(_WBenchMsg) { s_bpStartLock = '
              'CurrentDir(_WBenchMsg->sm_ArgList[0].wa_Lock); }')
if P1_PATCHED in code:
    print("Patch 1 (_WBenchMsg guard): already applied")
elif P1_ORIG in code:
    code = code.replace(P1_ORIG, P1_PATCHED)
    print("Patch 1 (_WBenchMsg guard): applied")
else:
    errors.append(
        "Patch 1 FAILED: _WBenchMsg dereference pattern not found — "
        "upstream ACE changed; update patch_ace.py before building"
    )

# Patch 2: Disable _ace_dbg. Latest ACE removed the function entirely, so
# its absence is fine — but if it EXISTS and our pattern doesn't match,
# the Amiberry systemFlushIo deadlock would come back silently.
P2_ORIG = (
    'static void _ace_dbg(const char *msg) {\n'
    '\tBPTR fh = Open("SYS:ace_debug.log", 1006);\n'
    '\tif(fh) { Seek(fh,0,1); Write(fh,(APTR)msg,strlen(msg)); Close(fh); }\n'
    '}'
)
P2_PATCHED = 'static void _ace_dbg(const char *msg) { (void)msg; }'
if '_ace_dbg' not in code:
    print("Patch 2 (_ace_dbg): not present upstream (removed) — nothing to do")
elif P2_PATCHED in code:
    print("Patch 2 (_ace_dbg): already applied")
elif P2_ORIG in code:
    code = code.replace(P2_ORIG, P2_PATCHED)
    print("Patch 2 (_ace_dbg): applied")
else:
    errors.append(
        "Patch 2 FAILED: _ace_dbg exists but does not match the expected "
        "pattern — upstream ACE changed; update patch_ace.py before building"
    )

if errors:
    for e in errors:
        print(e, file=sys.stderr)
    sys.exit(1)

with open(path, 'w') as f:
    f.write(code)

print("Patches applied successfully")
