from markovobfuscate.obfuscation import MarkovKeyState


class LyricsObfuscator(MarkovKeyState):

    def __init__(self, *args):
        MarkovKeyState.__init__(self, *args)

    @staticmethod
    def get_sentence_terminator():
        return "\n"

    @staticmethod
    def join_obfuscated_string(string_parts):
        full_string = string_parts[0].title()
        previous = string_parts[0]
        for part in string_parts[1:]:
            if part == "\n" or previous == "\n":
                full_string += part.title()

            else:
                full_string += " " + part
            previous = part

        return full_string

    @staticmethod
    def split_obfuscated_string(obfuscated_string):
        parts = []

        # first split on our word separator
        words = obfuscated_string.split(" ")
        for word in words:
            word = word.lower()
            if "\n" in word:
                while "\n" in word and len(word) != 0:
                    first, second = word.split("\n", 1)
                    if len(first) != 0:
                        parts.append(first)
                    parts.append("\n")
                    word = second
                parts.append(word)
            else:
                parts.append(word)

        return parts


class BinaryObfuscator(MarkovKeyState):

    def __init__(self, *args):
        MarkovKeyState.__init__(self, *args)

    @staticmethod
    def get_sentence_terminator():
        return "\x00"

    @staticmethod
    def join_obfuscated_string(string_parts):
        return "".join(string_parts)

    @staticmethod
    def split_obfuscated_string(obfuscated_string):
        return list(obfuscated_string)

    @staticmethod
    def split_sentences_for_learning(book):
        return book.split("\x00")

    @staticmethod
    def split_words_for_learning(sentence):
        return list(sentence)
