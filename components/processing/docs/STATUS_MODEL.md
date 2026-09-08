# Status model

TSAO reports distinct status dimensions:

- artifact/software qualification;
- scientific technical approval;
- engineering design approval;
- process-safety approval;
- legal/IP approval;
- customer/regulatory qualification;
- industrial performance guarantee.

Only the first can be established by repository CI. The others default to `NOT_EVALUATED` and advance only through project-specific evidence and named approval. A summary must never collapse these dimensions into a single “validated” label.
