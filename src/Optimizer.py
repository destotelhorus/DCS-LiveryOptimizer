import argparse
import os
import logging

from src.include.DescriptionLUA import DescriptionLUA
from src.include.FileEntry import FileEntry


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

    return True


def parse_livery(fileentries: dict, descriptions: dict, basepath, relpath):
    completepath = os.path.join(basepath, relpath)

    for file in os.listdir(completepath):
        filename = os.fsdecode(file)
        if os.path.isdir(os.path.join(completepath, file)):
            logging.info("    ignoring directory \"%s\"", filename)
            continue
        else:
            entry = FileEntry(basepath, relpath, file)
            logging.info("    processed FileEntry %s", entry)
            fileentries[entry.relfilename] = entry
            if filename.lower() == 'description.lua':
                logging.info("    found description.lua. parsing ...")
                descriptions[entry.relfilename] = DescriptionLUA(basepath, entry)


def parse_target(fileentries: dict, descriptions: dict, path: str):
    directory = os.fsencode(path)

    for l1file in os.listdir(directory):  # level: model
        if os.path.isdir(os.path.join(directory, l1file)):
            logging.info("stepping into model %s", l1file)
            for l2file in os.listdir(os.path.join(directory, l1file)):  # level: livery
                logging.info("  stepping into livery %s", l2file)
                parse_livery(fileentries, descriptions, os.path.join(directory), os.path.join(l1file, l2file))
        else:
            logging.info("ignoring regular file %s", l1file)


parser = argparse.ArgumentParser(
    description='Handles livery pack updates by optimizing files and producing automated deliverables')
parser.add_argument('previous', help='path to previous livery pack version', default=argparse.SUPPRESS, nargs='?')
parser.add_argument('next', help='path to next livery pack version', default=argparse.SUPPRESS, nargs='?')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args()
    if not check_parameters(args):
        parser.print_help()
        exit(1)

    fileentries = {}
    descriptions = {}
    parse_target(fileentries, descriptions, args.next)

# scan target first
# resolve links in target first
# differentiate between files or referenced files
# warn if referenced file has no entry in destination OR source directory (if only in source, then deleted but needed)
# check source .. mark as deleted, or deleted_but_needed if it's part of a link or not
