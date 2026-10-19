# -*- coding: utf-8 -*-
import sys

DEFAULT_PROGRESS_TIMEOUT = 30
DEFAULT_PROGRESS_INTERVAL = 0.5
# Transient gateway errors that are safe to retry on an individual poll.
DEFAULT_RETRY_STATUSES = (502, 503, 504)
DEFAULT_MAX_RETRIES = 3


class _ProgressTrackingConfig(object):
    """Base class for all progress tracking configurations."""
    def __init__(self, timeout, interval,
                 retry_statuses=DEFAULT_RETRY_STATUSES,
                 max_retries=DEFAULT_MAX_RETRIES):
        self.timeout = timeout
        self.interval = interval
        self.retry_statuses = tuple(retry_statuses)
        self.max_retries = max_retries

    def start_progress(self):
        raise NotImplementedError

    def on_progress(self, state, progress):
        raise NotImplementedError

    def should_retry(self, error, attempt):
        """Return whether a failed progress poll should be retried.

        ``error`` is the exception raised by the poll request and
        ``attempt`` is the number of retries already performed for the
        current poll. By default, retry responses whose HTTP status is in
        ``retry_statuses`` (transient gateway errors) up to ``max_retries``
        times. Override to implement a custom retry policy.
        """
        if attempt >= self.max_retries:
            return False
        response = getattr(error, "args", (None,))[0]
        status_code = getattr(response, "status_code", None)
        return status_code in self.retry_statuses


class DefaultProgressTracking(_ProgressTrackingConfig):
    """Default progress tracking configuration.

    Waits for 30 seconds, polls every 0.5 seconds and
    does not report progress in any way.
    """
    def __init__(self, timeout=DEFAULT_PROGRESS_TIMEOUT,
                 interval=DEFAULT_PROGRESS_INTERVAL,
                 retry_statuses=DEFAULT_RETRY_STATUSES,
                 max_retries=DEFAULT_MAX_RETRIES):
        super(DefaultProgressTracking, self).__init__(
            timeout, interval, retry_statuses, max_retries)

    def start_progress(self):
        return None

    def on_progress(self, state, progress):
        pass


class SimpleTextBarProgressTracking(DefaultProgressTracking):
    """Progress tracking config that displays a progress bar on stdout.

    Behaves like `DefaultProgressTracking` but provides a very simple
    textual progress bar, its purpose is mostly to showcase how a
    custom progress tracker can be implemented.
    """
    BAR_WIDTH = 40

    def start_progress(self):
        sys.stdout.write("[%s]" % (" " * self.BAR_WIDTH))
        sys.stdout.flush()
        sys.stdout.write("\b" * (self.BAR_WIDTH + 1))
        return dict(count=0)

    def on_progress(self, state, progress):
        if progress['progress'] in (-1, 0):
            return

        step = self.BAR_WIDTH / 100.0
        progress_value = step * progress['progress']
        while state['count'] < progress_value:
            sys.stdout.write("-")
            state['count'] += 1
        sys.stdout.flush()

        if progress['progress'] == 100:
            sys.stdout.write("\n")
