__author__ = 'bwall'
from markovobfuscate.formatters import LyricsObfuscator, BinaryObfuscator
from markovobfuscate.obfuscation import MarkovKeyState
import logging
import random
import zlib
import sys


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    from argparse import ArgumentParser

    parser = ArgumentParser(
        prog=__file__,
        description="Random testing on datasets for markovobfuscate",
    )
    parser.add_argument('-f', '--format', default="book", choices=["book", "lyrics", "binary"])
    parser.add_argument('book', metavar='path', type=str, default="datasets/98.txt",
                        help="Paths to files or directories to scan")
    parser.add_argument('-d', '--deobfuscate', default=False, required=False, action='store_true',
                        help='If enabled, deobfuscate instead of obfuscate')
    parser.add_argument('data', metavar='file to obfuscate', type=str, help="File contents to obfuscate")

    args = parser.parse_args()

    # File/book to read for training the Markov model (will be read into memory)
    training_file = args.book

    obfuscator = None
    if args.format == "lyrics":
        obfuscator = LyricsObfuscator
    elif args.format == "binary":
        obfuscator = BinaryObfuscator
    else:
        obfuscator = MarkovKeyState

    # Obfuscating Markov engine
    m1 = obfuscator(64)
    m2 = obfuscator(64)

    # Read the shared key into memory
    with open(training_file, "r") as f:
        text = f.read()

    # Split learning data into sentences, in this case, based on periods.
    m1.learn_book(text)
    m2.learn_book(text)

    with open(args.data, "r") as f:
        data = f.read()

    if not args.deobfuscate:
        sys.stdout.write(m1.obfuscate_string(zlib.compress(data, 9)))
    else:
        sys.stdout.write(zlib.decompress(m2.deobfuscate_string(data)))
