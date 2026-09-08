# Verification and failure semantics

Portability check:

```bash
python scripts/validate_agent_skills.py --root . --overlay-mode
```

Repository-native validation remains authoritative. Required negatives include NaN/Infinity/Bool, fake units, caller-supplied accepted/C5, raw Boolean capability, nonce replay, executable replacement, unit-scaling changes, surviving grandchildren, output overflow, and concurrent-ledger loss. External execution absent means HOLD, not PASS.
