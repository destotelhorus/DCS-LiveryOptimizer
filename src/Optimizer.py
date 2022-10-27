import argparse
import os
import logging
import zipfile
from typing import Union

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


def parse_livery(fileentries: dict, basepath, relpath, is_target: bool = True):
    completepath = os.path.join(basepath, relpath)

    for file in os.listdir(completepath):
        filename = os.fsdecode(file)
        if os.path.isdir(os.path.join(completepath, file)):
            logging.info("    ignoring directory \"%s\"", filename)
            continue
        else:
            entry = FileEntry(basepath, relpath, file, not is_target)
            logging.info("    processed FileEntry %s", entry)
            key = entry.relfilenamenoext.lower()
            if is_target and filename.lower() == 'description.lua':
                key = entry.relfilename.lower()
                logging.info("    found description.lua. parsing ...")
                desc = DescriptionLUA(basepath, entry)
                if desc.liveryblock_startindex > 0:
                    entry.linked_descriptions.append(desc)
                    fileentries['descriptions'][entry.relfilename.lower()] = desc

            if is_target:
                fileentries['bypath'][key] = entry
            else:
                fileentries['src_bypath'][key] = entry
            if entry.hashsize not in fileentries['byhash']:
                if is_target:
                    fileentries['byhash'][entry.hashsize] = []
                else:
                    fileentries['src_byhash'][entry.hashsize] = []
            if is_target:
                fileentries['byhash'][entry.hashsize].append(entry)
            else:
                fileentries['src_byhash'][entry.hashsize].append(entry)

def find_best_dedup(fileentries: dict, hashsize: str) -> Union[None, FileEntry]:
    #rules are simple ... prefer dedups with files that were existing in the version before also. saves space!
    if hashsize in fileentries['src_byhash'] and len(fileentries['src_byhash'][hashsize]) > 0:
        return fileentries['src_byhash'][hashsize][0]
    elif hashsize in fileentries['byhash'] and len(fileentries['byhash'][hashsize]) > 0:
        return fileentries['byhash'][hashsize][0]
    else:
        return None

def parse_files(fileentries: dict, source_path: str, target_path: str):
    sourcedir = os.fsencode(source_path)
    targetdir = os.fsencode(target_path)

    logging.info("++ building simple source tree")
    for l1file in os.listdir(sourcedir):  # level: model
        if not os.fsdecode(l1file).startswith('SA'):  # todo: remove
            continue
        if os.path.isdir(os.path.join(sourcedir, l1file)):
            logging.info("stepping into model %s", l1file)
            for l2file in os.listdir(os.path.join(sourcedir, l1file)):  # level: livery
                logging.info("  stepping into livery %s", l2file)
                parse_livery(fileentries, os.path.join(sourcedir), os.path.join(l1file, l2file), is_target=False)
        else:
            logging.info("ignoring regular file %s", l1file)

    logging.info("++ building fileentry and description tree")
    for l1file in os.listdir(targetdir):  # level: model
        if os.path.isdir(os.path.join(targetdir, l1file)):
            if not os.fsdecode(l1file).startswith('SA'):  # todo: remove
                continue
            logging.info("stepping into model %s", l1file)
            for l2file in os.listdir(os.path.join(targetdir, l1file)):  # level: livery
                logging.info("  stepping into livery %s", l2file)
                parse_livery(fileentries, os.path.join(targetdir), os.path.join(l1file, l2file))
        elif os.path.splitext(os.fsdecode(l1file))[1].lower() == '.txt':
            entry = FileEntry(targetdir, os.fsencode(""), l1file, sourceonly=False)
            fileentries['bypath'][entry.relfilename.lower()] = entry
            # these do not need to be added to byhash
        else:
            logging.info("ignoring regular file %s", l1file)

    logging.info("- going through description liveries to build target tree")
    for desc in fileentries['descriptions'].values():
        desc: DescriptionLUA = desc
        logging.info("  going through \"%s\"", desc.fileentry.relfilename)
        for livery in desc.filematches:
            livery: DescriptionLUATextureEntry = livery
            livery_relfilename_lower = livery.relfilename.lower()
            if len(os.path.splitext(livery_relfilename_lower)[1]) < 5:
                livery_relfilename_lower = os.path.splitext(livery_relfilename_lower)[0]
            # trying to find a FileEntry for that liveryTexture
            if livery_relfilename_lower in fileentries['bypath']:
                logging.info("    trying to look up for \"%s\". FOUND!", livery_relfilename_lower)
                liveryFE = fileentries['bypath'][livery_relfilename_lower]  # type: FileEntry
                liveryFEdedup = find_best_dedup(fileentries, liveryFE.hashsize)
                if liveryFE != liveryFEdedup and liveryFE.relfilename != liveryFEdedup.relfilename:
                    logging.info("    substituting \"%s\" with \"%s\".", liveryFE.relfilename, liveryFEdedup.relfilename)
                if desc not in liveryFEdedup.linked_descriptions:
                    liveryFEdedup.linked_descriptions.append(desc)
                livery.fileentry = fileentries['bypath'][os.path.splitext(liveryFEdedup.relfilename)[0].lower()]
            else:
                logging.warning("    trying to look up for \"%s\". NOT FOUND! Trying in old livery pack.", livery.relfilename.lower())
                if livery_relfilename_lower in fileentries['src_bypath']:
                    logging.info("    file found in old livery pack!")
                    tmpFE = fileentries['src_bypath'][livery_relfilename_lower]  # type: FileEntry
                    tmpFEdedup = find_best_dedup(fileentries, tmpFE.hashsize)
                    if tmpFE != tmpFEdedup and tmpFE.relfilename != tmpFEdedup.relfilename:
                        logging.info("    substituting \"%s\" with \"%s\".", livery.relfilename, tmpFEdedup.relfilename)
                    if desc not in tmpFEdedup.linked_descriptions:
                        tmpFEdedup.linked_descriptions.append(desc)
                    livery.fileentry = tmpFEdedup
                else:
                    logging.warning("Could not find this referenced file in either the new or the old livery pack! this better be in the base game!")
    return

def savezips(fileentries: dict, source_path: str, target_path: str, prefix: str, dontwrite: bool = False):
    deleted_files = set()
    with zipfile.ZipFile(prefix + "_update.zip", mode="w", compression=zipfile.ZIP_LZMA, compresslevel=6) as update_archive:
        with zipfile.ZipFile(prefix+"_full.zip", mode="w", compression=zipfile.ZIP_LZMA, compresslevel=6) as full_archive:
            for f in fileentries['bypath'].values():
                f: FileEntry = f
                if f.filename == 'description.lua':
                    #generateModifiedDescriptionLUA
                    #full_archive.writestr(zinfo_or_arcname="cleanup.bat", data=deletebat_content)
                    src_path = source_path if f.datasource == FileEntrySource.SOURCE else target_path
                    src_fullpath = os.path.join(src_path, f.relfilename)
                    gen_desc_lua = f.linked_descriptions[0].generateModifiedDescriptionLUA()
                    logging.info("Adding \"%s\" to total-zip as \"%s\"", src_fullpath, f.relfilename)
                    if not dontwrite:
                        full_archive.writestr(zinfo_or_arcname=f.relfilename, data=gen_desc_lua)
                    if gen_desc_lua != f.linked_descriptions[0].content:
                        # todo: multithread this later
                        if f.datasource == FileEntrySource.TARGET:
                            logging.info("Adding \"%s\" to update-zip as \"%s\"", src_fullpath, f.relfilename)
                            if not dontwrite:
                                update_archive.writestr(zinfo_or_arcname=f.relfilename, data=gen_desc_lua)
                elif len(f.linked_descriptions) > 0:
                    src_path = source_path if f.datasource == FileEntrySource.SOURCE else target_path
                    src_fullpath = os.path.join(src_path, f.relfilename)
                    logging.info("Adding \"%s\" to total-zip as \"%s\"", src_fullpath, f.relfilename)
                    if not dontwrite:
                        full_archive.write(src_fullpath, arcname=f.relfilename)
                    #todo: multithread this later
                    if f.datasource == FileEntrySource.TARGET:
                        logging.info("Adding \"%s\" to update-zip as \"%s\"", src_fullpath, f.relfilename)
                        if not dontwrite:
                            update_archive.write(src_fullpath, arcname=f.relfilename)
                elif os.fsdecode(f.relpath) == "" and os.path.splitext(f.filename)[1].lower() == ".txt":
                    src_path = source_path if f.datasource == FileEntrySource.SOURCE else target_path
                    src_fullpath = os.path.join(src_path, f.relfilename)
                    logging.info("Adding \"%s\" to total-zip as \"%s\"", src_fullpath, f.relfilename)
                    logging.info("Adding \"%s\" to update-zip as \"%s\"", src_fullpath, f.relfilename)
                    if not dontwrite:
                        full_archive.write(src_fullpath, arcname=f.relfilename)
                        update_archive.write(src_fullpath, arcname=f.relfilename)
                else:
                    if f.relfilename.lower() in fileentries['src_bypath'] and len(fileentries['src_bypath'][f.relfilename.lower()].linked_descriptions) == 0:
                        deleted_files.add(f.relfilename)

            for f in fileentries['src_bypath'].values():
                f: FileEntry = f
                if len(f.linked_descriptions) > 0:
                    src_path = source_path if f.datasource == FileEntrySource.SOURCE else target_path
                    src_fullpath = os.path.join(src_path, f.relfilename)
                    logging.info("Adding \"%s\" to total-zip as \"%s\"", src_fullpath, f.relfilename)
                    if not dontwrite:
                        full_archive.write(src_fullpath, arcname=f.relfilename)
                    #todo: multithread this later
                    if f.datasource == FileEntrySource.TARGET:
                        logging.info("Adding \"%s\" to update-zip as \"%s\"", src_fullpath, f.relfilename)
                        if not dontwrite:
                            update_archive.write(src_fullpath, arcname=f.relfilename)
                elif f.relfilename.lower() not in fileentries['bypath']:
                    deleted_files.add(f.relfilename)

            deleted_files = list(deleted_files)
            deleted_paths = set()
            deletebat_content = """@ECHO OFF
cd /D "%~dp0"
ECHO Assuming the liveries root is in %CD%. Please abort if you don't want any files deleted! Otherwise press a key to continue and clean up unused files from the previous pack.
PAUSE
ECHO Removing unused files.
"""
            for df in deleted_files:
                deletebat_content += "\nDEL /F \"" + df + "\""
                deleted_paths.add(os.path.dirname(df))

            deletebat_content += "\nECHO Trying to remove directories that might now be empty."
            sorted_delpaths = sorted(list(deleted_paths), key=len, reverse=True)
            for p in sorted_delpaths:
                deletebat_content += "\nRMDIR \""+p+"\""

            deletebat_content += "\n"

            logging.info("saving cleanup.bat")
            if not dontwrite:
                full_archive.writestr(zinfo_or_arcname="cleanup.bat", data=deletebat_content)
                update_archive.writestr(zinfo_or_arcname="cleanup.bat", data=deletebat_content)


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
    fileentries['src_bypath'] = {}
    fileentries['src_byhash'] = {}
    fileentries['descriptions'] = {}
    parse_files(fileentries, args.previous, args.next)
    savezips(fileentries, args.previous, args.next, args.savename, dontwrite=False)

# scan target first
# resolve links in target first
# differentiate between files or referenced files
# warn if referenced file has no entry in destination OR source directory (if only in source, then deleted but needed)
# check source .. mark as deleted, or deleted_but_needed if it's part of a link or not
