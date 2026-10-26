"""The simulated world: three industrial suppliers, their buyers' tenders and their quote processes.

Everything here knows the truth (what each requirement really is, whether the supplier can meet it, where the
process really waits). Only ``rdw.evaluate`` may read what this package writes under ``data/truth``; the
workbench itself reads the documents and event logs a customer would hand over, nothing else.
"""
