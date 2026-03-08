import asyncio
import logging
from collections import Counter

logger = logging.getLogger(__name__)
_metrics = Counter()


def inc(metric_name, value=1):
    _metrics[metric_name] += value


def snapshot():
    return dict(_metrics)


async def periodic_metrics_log(interval_sec=60):
    while True:
        await asyncio.sleep(interval_sec)
        logger.info("metrics snapshot=%s", snapshot())
