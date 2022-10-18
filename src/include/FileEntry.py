import os.path
from enum import Enum
import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.include.DescriptionLUA import DescriptionLUA


class FileEntrySource(Enum):
    SOURCE = 0
    TARGET = 1


class FileEntry:
    relpath: str
    bfilename: str
    linked_from = None  # type: FileEntry
    checksum: str
    size: int
    datasource: FileEntrySource = FileEntrySource.TARGET
    linked_descriptions: list  # type : list[DescriptionLUA]

    def __init__(self, basepath: str, _relpath: str, _filename: str, sourceonly: bool = False):
        self.linked_descriptions = [] # putting this into class definition means it's static
        self.bfilename = _filename
        self.relpath = _relpath
        self.size = os.stat(os.path.join(basepath, _relpath, _filename)).st_size
        file = open(os.path.join(basepath, _relpath, _filename), "rb")
        self.checksum = hashlib.sha256(file.read()).hexdigest()
        file.close()
        if sourceonly:
            self.datasource = FileEntrySource.SOURCE

    def __repr__(self):
        if not self.linked_from:
            return "{{name: \"{}\", size: {}, checksum: {}, datasource: {}}}".format(
                self.filename,
                self.size,
                self.checksum,
                self.datasource
            )
        else:
            return "{{name: \"{}\", size: {}, checksum: {}, linked_from: {}}}".format(
                self.filename,
                self.size,
                self.checksum,
                os.path.join(self.linked_from.relpath, self.linked_from.filename)
            )

    @property
    def relfilename(self):
        return os.fsdecode(os.path.join(self.relpath, self.bfilename))

    @property
    def filename(self):
        return os.fsdecode(self.bfilename)

    @property
    def hashsize(self):
        return str(self.size) + ":" + self.checksum
