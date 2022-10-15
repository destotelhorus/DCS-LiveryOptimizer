import os
import re
from re import Match
import logging

from src.include.FileEntry import FileEntry

class DescriptionLUATextureEntry:
    name: str
    texturefile : str
    match: Match
    fileentry : FileEntry

    def __init__(self, _match: Match):
        self.match = _match
        self.name = _match.group(1)
        self.texturefile = _match.group(3)

    def __repr__(self):
        return "{{name: \"{}\", texturefile: \"{}\"".format(
            self.name,
            self.texturefile
        )

class DescriptionLUA:
    rInnerMatches = r"{\s*\"([^\"]*)\"\s*,\s*(\S*)\s*,\s*\"([^\"]*)\"\s*,\s*(\S*)\s*}"
    rLiveryBlock = r"livery\s*=\s*{((?:[^{}]*{[^}]+}\s*;)+[^{}]*)}"

    fileentry: FileEntry
    content: str
    filematches = []
    liveryblock_startindex = 0

    def __init__(self, basepath: str, _fileentry: FileEntry):
        self.fileentry = _fileentry
        file = open(os.path.join(basepath, _fileentry.relfilename), "r")
        self.content = file.read()
        file.close()

        liveryblock = re.match(self.rLiveryBlock, self.content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if not liveryblock:
            logging.error("Could not find livery-block in description.lua. Exiting.")
            exit(2)
        self.liveryblock_startindex = liveryblock.start(1)
        self.filematches.clear()
        results = re.finditer(self.rInnerMatches, liveryblock.group(1), re.IGNORECASE | re.MULTILINE | re.DOTALL)
        for match in results:
            entry = DescriptionLUATextureEntry(match)
            self.filematches.append(entry)
            logging.info("      found texture \"%s\" pointing towards \"%s\"", entry.name, entry.texturefile)
        if len(self.filematches) == 0:
            logging.warning("No livery-texture links found. This is suspicious!")
