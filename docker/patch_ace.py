#!/usr/bin/env python3
"""Patch ACE system.c for CLI and Amiberry compatibility.

Patches applied:
1. NULL-guard _WBenchMsg dereference (crashes when launched from CLI)
2. Disable _ace_dbg file I/O (causes systemUnuse hang on Amiberry's
   virtual filesystem — the Open() call keeps disk DMA active, then
   systemFlushIo deadlocks waiting for the filesystem handler)
"""
import sys

path = sys.argv[1]
with open(path) as f:
    code = f.read()

# Patch 1: NULL-guard _WBenchMsg
code = code.replace(
    's_bpStartLock = CurrentDir(_WBenchMsg->sm_ArgList[0].wa_Lock);',
    'if(_WBenchMsg) { s_bpStartLock = CurrentDir(_WBenchMsg->sm_ArgList[0].wa_Lock); }'
)

# Patch 2: Disable _ace_dbg to prevent filesystem deadlock in Amiberry
# The original opens SYS:ace_debug.log on every call, which triggers disk
# DMA that makes systemFlushIo hang via WaitPort on the filesystem handler.
code = code.replace(
    'static void _ace_dbg(const char *msg) {\n'
    '\tBPTR fh = Open("SYS:ace_debug.log", 1006);\n'
    '\tif(fh) { Seek(fh,0,1); Write(fh,(APTR)msg,strlen(msg)); Close(fh); }\n'
    '}',
    'static void _ace_dbg(const char *msg) { (void)msg; }'
)

with open(path, 'w') as f:
    f.write(code)

print("Patches applied successfully")
