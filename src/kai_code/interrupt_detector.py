"""ESC key interrupt detector for cancelling operations.

Provides a cross-platform way to detect ESC key presses during async execution.
"""

import sys
import threading
import tty
import termios
from contextlib import contextmanager


class InterruptDetector:
    """Detects ESC key presses during execution.

    Runs a background thread that monitors for ESC key presses.
    Thread-safe and can be used across different parts of the application.
    """

    def __init__(self) -> None:
        """Initialize the interrupt detector."""
        self._interrupted = False
        self._listening = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start_listening(self) -> None:
        """Start listening for ESC key presses in background."""
        with self._lock:
            if self._listening:
                return

            self._interrupted = False
            self._listening = True
            self._thread = threading.Thread(target=self._listen_for_esc, daemon=True)
            self._thread.start()

    def stop_listening(self) -> None:
        """Stop listening for ESC key presses."""
        with self._lock:
            self._listening = False
            self._interrupted = False

    def check_interrupted(self) -> bool:
        """Check if ESC was pressed and clear the flag.

        Returns:
            True if ESC was pressed since last check, False otherwise.
        """
        with self._lock:
            result = self._interrupted
            self._interrupted = False
            return result

    def _listen_for_esc(self) -> None:
        """Background thread that listens for ESC key."""
        try:
            with self._raw_mode():
                while self._listening:
                    # Check if we should stop listening
                    with self._lock:
                        if not self._listening:
                            break

                    # Non-blocking read with timeout
                    ch = self._get_char(timeout=0.1)

                    if ch == "\x1b":  # ESC character
                        with self._lock:
                            self._interrupted = True
                            self._listening = False
                        break
                    elif ch == "\x03":  # Ctrl+C
                        # Let Ctrl+C be handled by the main KeyboardInterrupt handler
                        with self._lock:
                            self._listening = False
                        break
        except Exception:
            # Silently fail if terminal manipulation fails
            # (e.g., when not in a TTY)
            pass

    def _get_char(self, timeout: float = 0.1) -> str:
        """Get a single character from stdin with timeout.

        Args:
            timeout: Seconds to wait for input.

        Returns:
            Single character, or empty string if timeout.
        """
        import select

        # Check if data is available
        if not select.select([sys.stdin], [], [], timeout)[0]:
            return ""

        # Read the character
        ch = sys.stdin.read(1)
        return ch

    @contextmanager
    def _raw_mode(self):
        """Context manager for raw terminal mode.

        Yields control with terminal in raw mode, restores on exit.
        """
        if not sys.stdin.isatty():
            # Not a TTY, just yield without changing mode
            yield
            return

        # Save original settings
        original_settings = termios.tcgetattr(sys.stdin)

        try:
            # Set raw mode
            tty.setraw(sys.stdin.fileno())
            yield
        finally:
            # Restore original settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_settings)


# Global singleton instance
_detector: InterruptDetector | None = None
_detector_lock = threading.Lock()


def get_interrupt_detector() -> InterruptDetector:
    """Get the global interrupt detector singleton.

    Returns:
        The shared InterruptDetector instance.
    """
    global _detector

    with _detector_lock:
        if _detector is None:
            _detector = InterruptDetector()
        return _detector
