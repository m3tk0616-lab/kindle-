"""Detect whether a Kindle page has actually changed between two screenshots."""

import time
from pathlib import Path

import imagehash
from PIL import Image


# Perceptual hash difference > this value means the page changed.
# Range 0–64; 10 is a good balance between sensitivity and noise.
DEFAULT_THRESHOLD = 10


def compute_hash(image_path: str) -> imagehash.ImageHash:
    return imagehash.phash(Image.open(image_path).convert("L"))


def pages_differ(path_a: str, path_b: str, threshold: int = DEFAULT_THRESHOLD) -> bool:
    """Return True if the two screenshots represent different pages."""
    return (compute_hash(path_a) - compute_hash(path_b)) > threshold


class PageChangeWaiter:
    """
    After triggering a page turn, poll screenshots until the content
    changes or the timeout expires.
    """

    def __init__(
        self,
        capture_fn,          # callable(save_path: str) -> str
        timeout: float = 10.0,
        poll_interval: float = 0.5,
        threshold: int = DEFAULT_THRESHOLD,
    ):
        self._capture = capture_fn
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.threshold = threshold

    def wait_for_change(self, reference_path: str, tmp_path: str) -> bool:
        """
        Poll until the screen differs from reference_path.
        Returns True if a change was detected, False on timeout.
        """
        ref_hash = compute_hash(reference_path)
        deadline = time.monotonic() + self.timeout

        while time.monotonic() < deadline:
            time.sleep(self.poll_interval)
            self._capture(tmp_path)
            cur_hash = compute_hash(tmp_path)
            if (ref_hash - cur_hash) > self.threshold:
                return True

        return False
