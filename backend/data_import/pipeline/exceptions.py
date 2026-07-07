from typing import Any, Dict, List


class FileImportException(Exception):
    def dict(self) -> Dict[str, Any]:
        raise NotImplementedError()


class FileParseException(FileImportException):
    def __init__(self, filename: str, line_num: int, message: str):
        self.filename = filename
        self.line_num = line_num
        self.message = message

    def __str__(self):
        return f"ParseError: You cannot parse line {self.line_num} in {self.filename}: {self.message}"

    def dict(self):
        return {"filename": self.filename, "line": self.line_num, "message": self.message}


class MaximumFileSizeException(FileImportException):
    def __init__(self, filename: str, max_size: int):
        self.filename = filename
        self.max_size = max_size

    def __str__(self):
        return f"The maximum file size that can be uploaded is {self.max_size/1024/1024} MB"

    def dict(self):
        return {"filename": self.filename, "line": -1, "message": str(self)}


class FileTypeException(FileImportException):
    def __init__(self, filename: str, filetype: str, allowed_types=None):
        self.filename = filename
        self.filetype = filetype
        self.allowed_types = allowed_types

    def __str__(self):
        return f"The file type {self.filetype} is unexpected. Expected: {self.allowed_types}"

    def dict(self):
        return {"filename": self.filename, "line": -1, "message": str(self)}


class FileFormatException(FileImportException):
    def __init__(self, file_format: str):
        self.file_format = file_format

    def dict(self):
        message = f"Unknown file format: {self.file_format}"
        return {"message": message}


class FieldTooLongException(FileImportException):
    """
    Raised when a value destined for a fixed-length DB column (e.g. a
    label type's `text`) exceeds that column's max_length. Postgres'
    own "value too long for type character varying(N)" error doesn't
    say which column or which row caused it, so we check proactively
    and report the field name + offending value(s) instead.
    """

    def __init__(self, filename: str, field_name: str, values: List[str], max_length: int):
        self.filename = filename
        self.field_name = field_name
        self.values = values
        self.max_length = max_length

    def __str__(self):
        def describe(value: str) -> str:
            preview = value if len(value) <= 50 else f"{value[:50]}..."
            return f"'{preview}' ({len(value)} characters)"

        shown = ", ".join(describe(v) for v in self.values[:5])
        remaining = len(self.values) - 5
        more = f", and {remaining} more" if remaining > 0 else ""
        return (
            f"The '{self.field_name}' value exceeds the maximum allowed length "
            f"of {self.max_length} characters: {shown}{more}"
        )

    def dict(self):
        return {"filename": self.filename, "line": -1, "message": str(self)}
