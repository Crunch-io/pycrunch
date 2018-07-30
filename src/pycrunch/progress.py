# -*- coding: utf-8 -*-
import sys

DEFAULT_PROGRESS_TIMEOUT = 30
DEFAULT_PROGRESS_INTERVAL = 0.5


class _ProgressTrackingConfig(object):
    """Base class for all progress tracking configurations."""
    def __init__(self, timeout, interval):
        self.timeout = timeout
        self.interval = interval

    def start_progress(self):
        raise NotImplementedError

    def on_progress(self, state, progress):
        raise NotImplementedError


class DefaultProgressTracking(_ProgressTrackingConfig):
    """Default progress tracking configuration.

    Waits for 30 seconds, polls every 0.5 seconds and
    does not report progress in any way.
    """
    def __init__(self, timeout=DEFAULT_PROGRESS_TIMEOUT,
                 interval=DEFAULT_PROGRESS_INTERVAL):
        super(DefaultProgressTracking, self).__init__(timeout, interval)

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
