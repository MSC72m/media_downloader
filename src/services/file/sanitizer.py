"""Filename sanitizer service."""

import re
import unicodedata


class FilenameSanitizer:
    """Service for sanitizing filenames."""

    MAX_FILENAME_LENGTH = 255 - 10  # Leave room for extension and potential suffix

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename to make it safe for all operating systems.

        Args:
            filename: The original filename

        Returns:
            A sanitized filename
        """
        # Remove invalid characters
        valid_chars = re.compile(r'[^\w\s.\-]')
        filename = valid_chars.sub('_', filename)

        # Normalize unicode characters
        try:
            filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode('ASCII')
        except UnicodeError:
            # Fallback: replace problematic characters
            filename = unicodedata.normalize('NFKC', filename)
            filename = re.sub(r'[^\w\s.\-]', '_', filename)

        # Limit length
        if len(filename) > self.MAX_FILENAME_LENGTH:
            filename = filename[:self.MAX_FILENAME_LENGTH]

        return filename.strip()