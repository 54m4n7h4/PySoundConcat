#!/usr/bin/env python

"""Command line interface for matching databases"""

import argparse
import audiofile
import logging
from fileops import loggerops
import pdb
import os
import __builtin__
from database import AudioDatabase, Matcher

filename = os.path.splitext(__file__)[0]
logger = loggerops.create_logger(log_filename='./{0}.log'.format(filename))

###########################################################################
# File open and closing monitoring
openfiles = set()
oldfile = __builtin__.file

class newfile(oldfile):
    def __init__(self, *args):
        self.x = args[0]
        logger.debug("OPENING %s" % str(self.x))
        oldfile.__init__(self, *args)
        openfiles.add(self)

    def close(self):
        logger.debug("CLOSING %s" % str(self.x))
        oldfile.close(self)
        openfiles.remove(self)
oldopen = __builtin__.open
def newopen(*args):
    return newfile(*args)
__builtin__.file = newfile
__builtin__.open = newopen

def printOpenFiles():
    logger.debug("%d OPEN FILES: [%s]" % (len(openfiles), ", ".join(f.x for f in openfiles)))

###########################################################################

def main():
    """Parse arguments then generate database."""
    logger.info('Started')
    parser = argparse.ArgumentParser(
        description='Generate a database at argument 1 based on files in '
        'argument 2.'
    )
    parser.add_argument(
        'source',
        type=str,
        help='Source database directory'
    )
    parser.add_argument(
        'target',
        type=str,
        help='Target database directory'
    )
    parser.add_argument(
        '--analyse',
        '-a',
        nargs='*',
        help='Specify analyses to be created. Valid analyses are: \'rms\''
        '\'f0\' \'atk\' \'fft\'',
        default=["rms", "zerox", "fft", "spccntr", "spcsprd", "f0"]
    )
    args = parser.parse_args()
    source_db = AudioDatabase(
        args.source,
        analysis_list=args.analyse,
    )
    # Create/load a pre-existing database
    source_db.load_database(reanalyse=False)

    target_db = AudioDatabase(
        args.target,
        analysis_list=args.analyse,
    )
    # Create/load a pre-existing database
    target_db.load_database(reanalyse=False)

    analysis_dict = {
        "f0": "median",
        "rms": "mean",
        #"fft": "raw",
        "zerox": "mean",
        "spccntr": "mean",
        "spcsprd": "mean",
    }

    matcher = Matcher(source_db, target_db, analysis_dict)
    matcher.match(matcher.brute_force_matcher, grain_size=100, overlap=2)

if __name__ == "__main__":
    main()
