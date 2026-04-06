r"""
Cross-cutting infrastructure protocols.

Job enqueue, distributed locks, and screenshot run guards live in
``app.portability.job_messaging`` (interface-first, independently swappable adapters).
"""
