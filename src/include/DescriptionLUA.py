import ntpath
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
    descriptionLUA = None  # type: DescriptionLUA

    def __init__(self, _match: Match, _descriptionLUA):
        self.match = _match
        self.name = _match.group(1)
        self.texturefile = _match.group(3)
        self.descriptionLUA = _descriptionLUA
        self.fileentry = None

    def __repr__(self):
        return "{{name: \"{}\", texturefile: \"{}\"}}".format(
            self.name,
            self.texturefile
        )

    @property
    def relativetexturefile(self):
        if not self.fileentry:
            return self.texturefile
        else:
            return os.path.relpath(os.path.splitext(self.fileentry.relfilename)[0], os.fsdecode(self.descriptionLUA.fileentry.relpath))

    @property
    def relativetexturefilewithext(self):
        if not self.fileentry:
            return self.texturefile
        else:
            return os.path.relpath(self.fileentry.relfilename, os.fsdecode(self.descriptionLUA.fileentry.relpath))

    def convertPathToUnix(self, path: str):
        import pathlib
        p = pathlib.PureWindowsPath(path)
        return p.as_posix()

    def convertPathToWin(self, path: str):
        return path.replace('/', '\\\\')

    @property
    def relfilename(self):
        return os.path.normpath(os.path.join(os.fsdecode(self.descriptionLUA.fileentry.relpath), self.convertPathToUnix(self.texturefile)))
class DescriptionLUA:
    rInnerMatches = r"{\s*\"([^\"]*)\"\s*,\s*(\S*)\s*,\s*\"([^\"]*)\"\s*,\s*(\S*)\s*}"
    rLiveryBlock = r".*livery\s*=\s*{((?:[^{}]*{[^}]+}\s*[;,])+[^{}]*)}"

    fileentry: FileEntry
    content: str
    filematches : list  # type: list[DescriptionLUATextureEntry]
    liveryblock_startindex = 0

    def generateModifiedDescriptionLUA(self) -> str:
        newcontent = self.content
        for fm in reversed(self.filematches):
            fm : DescriptionLUATextureEntry = fm
            if fm.fileentry and len(os.path.splitext(fm.texturefile)[1]) < 5 and fm.fileentry.filename.lower() == fm.texturefile.lower():
                newcontent = newcontent[:(self.liveryblock_startindex + fm.match.start(3))] + fm.convertPathToWin(fm.relativetexturefilewithext) + newcontent[(self.liveryblock_startindex + fm.match.end(3)):]
            else:
                newcontent = newcontent[:(self.liveryblock_startindex+fm.match.start(3))] + fm.convertPathToWin(fm.relativetexturefile) + newcontent[(self.liveryblock_startindex+fm.match.end(3)):]
        return newcontent

    def __init__(self, basepath: str, _fileentry: FileEntry):
        self.fileentry = _fileentry
        file = open(os.path.join(basepath, os.fsencode(_fileentry.relfilename)), "r")
        self.content = file.read()
        file.close()

        liveryblock = re.match(self.rLiveryBlock, self.content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if not liveryblock:
            logging.error("Could not find livery-block in description.lua. Exiting.")
            return
            --exit(2)
        self.liveryblock_startindex = liveryblock.start(1)
        self.filematches = []
        results = re.finditer(self.rInnerMatches, liveryblock.group(1), re.IGNORECASE | re.MULTILINE | re.DOTALL)
        for match in results:
            entry = DescriptionLUATextureEntry(match, self)
            self.filematches.append(entry)
            logging.info("      found texture \"%s\" pointing towards \"%s\"", entry.name, entry.texturefile)
        if len(self.filematches) == 0:
            logging.warning("No livery-texture links found. This is suspicious!")
