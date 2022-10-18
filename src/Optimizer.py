import argparse
import os
import logging
import zipfile

from src.include.DescriptionLUA import DescriptionLUA, DescriptionLUATextureEntry
from src.include.FileEntry import FileEntry, FileEntrySource


def check_parameters(_args) -> bool:
    if not hasattr(_args, 'previous'):
        logging.warning("The argument for previous is missing")
        return False
    elif not os.path.isdir(_args.previous):
        logging.warning("The argument for previous livery pack directory \"%s\" is not pointing to a path",
                        _args.previous)
        return False
    if not hasattr(_args, 'next'):
        logging.warning("The argument for next is missing")
        return False
    elif not os.path.isdir(_args.next):
        logging.warning("The argument for next livery pack directory \"%s\" is not pointing to a path",
                        _args.next)
        return False
    if not hasattr(_args, 'savename'):
        logging.warning("The argument for savename is missing")
        return False

    return True


def parse_livery(fileentries: dict, basepath, relpath):
    completepath = os.path.join(basepath, relpath)

    for file in os.listdir(completepath):
        filename = os.fsdecode(file)
        if os.path.isdir(os.path.join(completepath, file)):
            logging.info("    ignoring directory \"%s\"", filename)
            continue
        else:
            entry = FileEntry(basepath, relpath, file)
            logging.info("    processed FileEntry %s", entry)
            fileentries['bypath'][entry.relfilename.lower()] = entry
            if entry.hashsize not in fileentries['byhash']:
                fileentries['byhash'][entry.hashsize] = []
            fileentries['byhash'][entry.hashsize].append(entry)
            if filename.lower() == 'description.lua':
                logging.info("    found description.lua. parsing ...")
                desc = DescriptionLUA(basepath, entry)
                if desc.liveryblock_startindex > 0:
                    fileentries['descriptions'][entry.relfilename.lower()] = desc


def parse_files(fileentries: dict, source_path: str, target_path: str):
    sourcedir = os.fsencode(source_path)
    targetdir = os.fsencode(target_path)

    logging.info("++ building fileentry and description tree")
    for l1file in os.listdir(targetdir):  # level: model
        if not os.fsdecode(l1file).startswith('F-14B'): #todo: remove
            continue
        if os.path.isdir(os.path.join(targetdir, l1file)):
            logging.info("stepping into model %s", l1file)
            for l2file in os.listdir(os.path.join(targetdir, l1file)):  # level: livery
                logging.info("  stepping into livery %s", l2file)
                parse_livery(fileentries, os.path.join(targetdir), os.path.join(l1file, l2file))
        else:
            logging.info("ignoring regular file %s", l1file)

    logging.info("- going through description liveries to build target tree")
    for desc in fileentries['descriptions'].values():
        desc: DescriptionLUA = desc
        logging.info("  going through \"%s\"", desc.fileentry.relfilename)
        for livery in desc.filematches:
            livery: DescriptionLUATextureEntry = livery
            # trying to find a FileEntry for that liveryTexture
            if livery.relfilename.lower() in fileentries['bypath']:
                logging.info("    trying to look up for \"%s\". FOUND!", livery.relfilename.lower())
                liveryFE = fileentries['bypath'][livery.relfilename.lower()]  # type: FileEntry
                liveryFEdedup = fileentries['byhash'][liveryFE.hashsize][0]  # type: FileEntry
                if liveryFE != liveryFEdedup:
                    logging.info("    substituting \"%s\" with \"%s\".", liveryFE.relfilename, liveryFEdedup.relfilename)
                if desc not in liveryFEdedup.linked_descriptions:
                    liveryFEdedup.linked_descriptions.append(desc)
                livery.fileentry = fileentries['bypath'][liveryFEdedup.relfilename.lower()]
            else:
                logging.warning("    trying to look up for \"%s\". NOT FOUND! Trying in old livery pack.", livery.relfilename.lower())
                potential_old_filename = os.path.join(source_path, livery.relfilename)
                if os.path.exists(potential_old_filename):
                    logging.info("    file found in old livery pack!")
                    tmpFE = FileEntry(source_path, os.fsdecode(desc.fileentry.relpath), livery.texturefile+".DDS")
                    tmpFE.datasource = FileEntrySource.SOURCE
                    if tmpFE.hashsize in fileentries['byhash']:
                        tmpFEdedup = fileentries['byhash'][tmpFE.hashsize][0]
                        if tmpFE != tmpFEdedup:
                            logging.info("    substituting \"%s\" with \"%s\".", livery.relfilename, tmpFEdedup.relfilename)
                        if desc not in tmpFEdedup.linked_descriptions:
                            tmpFEdedup.linked_descriptions.append(desc)
                        livery.fileentry = fileentries['bypath'][tmpFEdedup.relfilename.lower()]
                    else:
                        logging.warning("    pulling in \"%s\" from old liverypack version!", livery.relfilename)
                        if tmpFE.relfilename.lower() not in fileentries['bypath']:
                            fileentries['bypath'][tmpFE.relfilename.lower()] = tmpFE
                            if tmpFE.hashsize not in fileentries['byhash']:
                                fileentries['byhash'][tmpFE.hashsize] = []
                            fileentries['byhash'][tmpFE.hashsize].append(tmpFE)

                            if desc not in tmpFE.linked_descriptions:
                                tmpFE.linked_descriptions.append(desc)
                            livery.fileentry = tmpFE
                        else:
                            logging.error("this should be impossible!")
                else:
                    logging.error("Could not find this referenced file in either the new or the old livery pack! something is amiss here!")
                    exit(3)
    return

def savezips(fileentries: dict, source_path: str, target_path: str, prefix: str):
    with zipfile.ZipFile(prefix+"_full.zip", mode="w", compression=zipfile.ZIP_LZMA, compresslevel=6) as full_archive:
        for f in fileentries['bypath'].values():
            f: FileEntry = f
            if len(f.linked_descriptions) > 0:
                src_path = source_path if f.datasource == FileEntrySource.SOURCE else target_path
                src_fullpath = os.path.join(src_path, f.relfilename)
                logging.info("Adding \"%s\" to total-zip as \"%s\"", src_fullpath, f.relfilename)
                full_archive.write(src_fullpath, arcname=f.relfilename)

parser = argparse.ArgumentParser(
    description='Handles livery pack updates by optimizing files and producing automated deliverables')
parser.add_argument('previous', help='path to previous livery pack version', default=argparse.SUPPRESS, nargs='?')
parser.add_argument('next', help='path to next livery pack version', default=argparse.SUPPRESS, nargs='?')
parser.add_argument('savename', help='prefix for the saved data', default=argparse.SUPPRESS, nargs='?')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args()
    if not check_parameters(args):
        parser.print_help()
        exit(1)

    fileentries = {}
    fileentries['bypath'] = {}
    fileentries['byhash'] = {}
    fileentries['descriptions'] = {}
    parse_files(fileentries, args.previous, args.next)
    savezips(fileentries, args.previous, args.next, args.savename)

# scan target first
# resolve links in target first
# differentiate between files or referenced files
# warn if referenced file has no entry in destination OR source directory (if only in source, then deleted but needed)
# check source .. mark as deleted, or deleted_but_needed if it's part of a link or not
