import logging
import sys


def setup_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def log_event(
    logger: logging.Logger,
    event: str,
    deck_id: str | None = None,
    slide_id: str | None = None,
    job_id: str | None = None,
    **kwargs: object,
) -> None:
    parts = [f"event={event}"]
    if deck_id:
        parts.append(f"deck_id={deck_id}")
    if slide_id:
        parts.append(f"slide_id={slide_id}")
    if job_id:
        parts.append(f"job_id={job_id}")
    for k, v in sorted(kwargs.items()):
        parts.append(f"{k}={v}")
    logger.info(" ".join(parts))
