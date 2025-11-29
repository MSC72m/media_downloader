import re
import unicodedata


class FilenameSanitizer:
    MAX_FILENAME_LENGTH = 255 - 10

    def sanitize_filename(self, filename: str) -> str:
        valid_chars = re.compile(r"[^\w\s.\-]")
        filename = valid_chars.sub("_", filename)

        try:
            filename = (
                unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore").decode("ASCII")
            )
        except UnicodeError:
            filename = unicodedata.normalize("NFKC", filename)
            filename = re.sub(r"[^\w\s.\-]", "_", filename)

        if len(filename) > self.MAX_FILENAME_LENGTH:
            filename = filename[: self.MAX_FILENAME_LENGTH]

        return filename.strip()
