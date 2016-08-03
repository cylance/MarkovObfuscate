from markovobfuscate.formatters import LyricsObfuscator, BinaryObfuscator
from markovobfuscate.obfuscation import MarkovKeyState
from os.path import join
import unittest

import random


class TestLyricObfuscator(unittest.TestCase):

    @staticmethod
    def load_ts_lyric_obfuscators():
        lo0 = LyricsObfuscator(16)
        lo1 = LyricsObfuscator(16)

        with open(join("datasets", "ts_lyrics.lst"), "r") as f:
            text = f.read()

        lo0.learn_book(text)
        lo1.learn_book(text)

        return lo0, lo1

    def test_splitting_and_joining(self):
        test_string = "Test0 test1 test2\nTest3 test4 test5"
        split_string = LyricsObfuscator.split_obfuscated_string(test_string)
        joined_string = LyricsObfuscator.join_obfuscated_string(split_string)

        assert joined_string == test_string

    def test_ts_basic(self):
        lo0, lo1 = self.load_ts_lyric_obfuscators()
        obfuscated = lo0.obfuscate_string("test")
        deobfuscated = lo1.deobfuscate_string(obfuscated)

        assert deobfuscated == "test"


class TestMarkovObfuscator(unittest.TestCase):

    @staticmethod
    def load_ts_lyric_obfuscators():
        lo0 = MarkovKeyState(16)
        lo1 = MarkovKeyState(16)

        with open(join("datasets", "ts_lyrics.lst"), "r") as f:
            text = f.read()

        lo0.learn_book(text)
        lo1.learn_book(text)

        return lo0, lo1

    def test_splitting_and_joining(self):
        test_string = "test0 test1 test2\ntest3 test4 test5"
        split_string = MarkovKeyState.split_obfuscated_string(test_string)
        joined_string = MarkovKeyState.join_obfuscated_string(split_string)

        assert joined_string == test_string

    def test_ts_basic(self):
        lo0, lo1 = self.load_ts_lyric_obfuscators()
        obfuscated = lo0.obfuscate_string("test")
        deobfuscated = lo1.deobfuscate_string(obfuscated)

        assert deobfuscated == "test"

    def test_extended(self):
        lo0, lo1 = self.load_ts_lyric_obfuscators()

        for test in xrange(100):
            origial_string = "".join([chr(random.randint(0, 255)) for k in xrange(1024)])
            obfuscated = lo0.obfuscate_string(origial_string)
            deobfuscated = lo1.deobfuscate_string(obfuscated)

            assert deobfuscated == origial_string


class TestBinaryObfuscator(unittest.TestCase):

    @staticmethod
    def load_ts_lyric_obfuscators():
        lo0 = BinaryObfuscator(16)
        lo1 = BinaryObfuscator(16)

        with open(join("datasets", "ts_lyrics.lst"), "r") as f:
            text = f.read()

        lo0.learn_book(text)
        lo1.learn_book(text)

        return lo0, lo1

    @staticmethod
    def load_dash_obfuscators():
        lo0 = BinaryObfuscator(16)
        lo1 = BinaryObfuscator(16)

        with open(join("datasets", "dash"), "r") as f:
            text = f.read()

        lo0.learn_book(text)
        lo1.learn_book(text)

        return lo0, lo1

    def test_splitting_and_joining(self):
        test_string = "test0 test1 test2\ntest3 test4 test5"
        split_string = MarkovKeyState.split_obfuscated_string(test_string)
        joined_string = MarkovKeyState.join_obfuscated_string(split_string)

        assert joined_string == test_string

    def test_ts_basic(self):
        lo0, lo1 = self.load_ts_lyric_obfuscators()
        obfuscated = lo0.obfuscate_string("test")
        deobfuscated = lo1.deobfuscate_string(obfuscated)

        assert deobfuscated == "test"

    def test_trained_on_dash(self):
        lo0, lo1 = self.load_dash_obfuscators()
        obfuscated = lo0.obfuscate_string("test")
        deobfuscated = lo1.deobfuscate_string(obfuscated)

        assert deobfuscated == "test"

    def test_extended_trained_on_dash(self):
        lo0, lo1 = self.load_dash_obfuscators()

        for test in xrange(100):
            origial_string = "".join([chr(random.randint(0, 255)) for k in xrange(1024)])
            obfuscated = lo0.obfuscate_string(origial_string)
            deobfuscated = lo1.deobfuscate_string(obfuscated)

            assert deobfuscated == origial_string


if __name__ == '__main__':
    unittest.main()
