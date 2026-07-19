"""Turn a benchmark run's normalized records into a step stats summary.

ARCH has no counterexample validator yet, so a run is judged only on whether its
results file was well-formed: any parsed run is "green". We tally the tool's
verdicts into ARCH's three buckets (anything unrecognized counts as unknown).
"""

#: The buckets shown, in reading order.
ARCH_VERDICTS = ["verified", "falsified", "unknown"]

_VERIFIED = {"verified", "holds", "unsat", "safe"}
_FALSIFIED = {"falsified", "violated", "sat", "unsafe"}


def _bucket(result: str) -> str:
    r = (result or "").strip().lower()
    if r in _VERIFIED:
        return "verified"
    if r in _FALSIFIED:
        return "falsified"
    return "unknown"


def summarize(records) -> dict | None:
    """A ``{summary, severity}`` payload for the step, or ``None`` when there is
    nothing to summarize (no records → malformed/empty file, so no green summary)."""
    if not records:
        return None
    verdicts = {v: 0 for v in ARCH_VERDICTS}
    for rec in records:
        verdicts[_bucket(rec.result)] += 1
    return {
        "summary": {"instances": len(records), "verdicts": verdicts, "order": ARCH_VERDICTS},
        "severity": "success",
    }
