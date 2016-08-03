__author__ = 'bwall'
import re
import operator
import random
import logging
import math


# Exception to throw if the algorithm breaks like a condom on prom night
class AlgorithmFailException(Exception):
    def __init__(self):
        Exception.__init__(self)


# The core class of this project, learns based off input of sentences, and can then obfuscate and deobfuscate data
class MarkovKeyState:
    def __init__(self, new_base=16):
        """
        Constructor, new_base defines the base bytes are converted to from base 256
        Smaller values lead to larger obfuscated strings but faster production of strings
        :return:
        """
        self.words = set()
        # Set the --terminate-- character (acts as the first and last character of a sentence)
        self.raw_scores = {"--terminate--": {}}
        self.new_base = new_base

    @staticmethod
    def split_sentences_for_learning(book):
        """
        To change how sentences are created for learning, monkey patch/override this function
        :param book:
        :return:
        """
        return re.split("[\n\.]", book)

    @staticmethod
    def split_words_for_learning(sentence):
        """
        To change how words are created for learning, monkey patch/override this function
        :param sentence:
        :return:
        """
        return re.findall(r"\w[\w']*", sentence.lower())

    @staticmethod
    def join_obfuscated_string(string_parts):
        """
        When the string is obfuscated, what is produced is a list of "words", we can choose how these are joined
        together to provide smoother formatting to our obfuscated data
        :param string_parts:
        :return:
        """
        return " ".join(string_parts)

    @staticmethod
    def split_obfuscated_string(obfuscated_string):
        """
        When a string is being deobfuscated, it needs to be parsed for its parts. If we change our join_obfuscated_string
        then we need to change this function as well to handle results
        :param obfuscated_string:
        :return:
        """
        return obfuscated_string.split(' ')

    @staticmethod
    def get_sentence_terminator():
        """
        In the case you wish to change the sentence terminator symbol, monkey patch/override this function
        :return:
        """
        return "."

    def learn_sentence(self, sentence):
        """
        Learn based on the input sentence.

        :param sentence: Space separated sentence to apply to Markov model
        :return: No relevant return data
        """
        # Split the sentence into words/parts
        parts = self.split_words_for_learning(sentence)
        if len(parts) == 0:
            return

        # This is a speed optimized method to increment the relation count between --terminate-- and the last part
        try:
            self.raw_scores[parts[-1]]["--terminate--"] += 1
        except KeyError:
            try:
                self.raw_scores[parts[-1]]["--terminate--"] = 1
            except KeyError:
                self.raw_scores[parts[-1]] = {"--terminate--": 1}

        # Iterate through all the parts, and increment the relation counts for all adjacent parts
        last = "--terminate--"
        for x in xrange(len(parts)):
            current = parts[x]
            try:
                self.raw_scores[last][current] += 1
            except KeyError:
                try:
                    self.raw_scores[last][current] = 1
                except KeyError:
                    self.raw_scores[last] = {current: 1}
            last = current

        # If any of the parts of this sentence don't end up in the database, something is broken in the code
        for part in parts:
            if part not in self.raw_scores:
                raise

    def learn_book(self, book):
        sentences = self.split_sentences_for_learning(book)
        for s in sentences:
            self.learn_sentence(s)

    def print_most_likely_sentence(self):
        """
        This function is mostly for testing/fun.  It generates the most likely sentence from the Markov model
        :return: The sentence
        """
        last = "--terminate--"
        parts = []

        while True:
            # Get the most likely next word, and set as current
            current = sorted(self.raw_scores[last].items(), key=operator.itemgetter(1))[-1][0]

            # If the current value is --terminate--, we are done generating the sentence
            if current == "--terminate--":
                break

            parts.append(current)

            # Set current to last as we move into the next iteration
            last = current

        return " ".join(parts)

    def create_byte(self, last, byte_value):
        """
        Internal function to generate an obfuscated byte, which can be represented by multiple words/sentences

        :param last: The last word in the current obfuscated sentence
        :param byte_value: The byte value to append
        :return: A string of words to append
        """
        words = []
        # Do we need to use a long value or can we use a short value
        if len(self.raw_scores[last].items()) <= self.new_base:
            # conduct depth first search to solve byte stretching issue
            search_queue = [([last], byte_value, len(self.raw_scores[last].items()))]

            word_cache = {}

            while len(search_queue) > 0:
                words_to_use, remaining_value, count = search_queue.pop(0)

                if count < self.new_base:

                    # we need another word
                    if words_to_use[-1] in word_cache:
                        current_list = word_cache[words_to_use[-1]]
                    else:
                        current_list = sorted(
                            self.raw_scores[words_to_use[-1]].items(),
                            key=operator.itemgetter(1)
                        )[::-1]
                        word_cache[words_to_use[-1]] = current_list

                    # we need whichever is smaller, the remaining value or
                    # the length of values for the next word
                    upper_bound = remaining_value if remaining_value < len(current_list) - 1 else len(current_list) - 1

                    # Pick a random word that does not result in us going over our remaining value
                    indeces = []
                    if upper_bound == 0:
                        indeces.append(0)
                    else:
                        indeces.extend(range(upper_bound + 1))
                        random.shuffle(indeces)
                        #indeces = sorted(indeces, reverse=True)

                    # Decrement remaining value and push our word to our list of words
                    for index in indeces:
                        rv = remaining_value - index
                        wtu = words_to_use + [current_list[index][0]]

                        if current_list[index][0] in word_cache:
                            cl = word_cache[current_list[index][0]]
                        else:
                            cl = sorted(
                                self.raw_scores[current_list[index][0]].items(),
                                key=operator.itemgetter(1)
                            )[::-1]
                            word_cache[current_list[index][0]] = cl

                        c = len(cl)

                        if c + count >= self.new_base and c < rv + 1:
                            # constraint failed
                            continue

                        search_queue.insert(0, (wtu, rv, c + count))
                else:
                    # We have enough words
                    if words_to_use[-1] in word_cache:
                        current_list = word_cache[words_to_use[-1]]
                    else:
                        current_list = sorted(
                            self.raw_scores[words_to_use[-1]].items(),
                            key=operator.itemgetter(1)
                        )[::-1]
                        word_cache[words_to_use[-1]] = current_list

                    # If this is true, the algo has failed going down this random path, and should keep searching
                    if len(current_list) < remaining_value + 1:
                        continue

                    # Push our most common last word to terminate our long value
                    words_to_use.append(current_list[remaining_value][0])

                    # Clean out the "last" argument from list
                    words = words_to_use[1:]
                    break
        else:
            # w00t, we can use a short value!
            words.append(sorted(self.raw_scores[last].items(), key=operator.itemgetter(1))[::-1][byte_value][0])

        if len(words) == 0:
            raise AlgorithmFailException()
        return words

    @staticmethod
    def _char_to_base(chr_int, target_base):
        if chr_int == 0:
            return [0]
        return MarkovKeyState._char_to_base(chr_int / target_base, target_base) + [chr_int % target_base]

    @staticmethod
    def char_to_base(chr_int, target_base):
        r = MarkovKeyState._char_to_base(chr_int, target_base)
        r = [0] * ((int(math.ceil(math.log(256, target_base) + 1))) - len(r)) + r
        return r

    @staticmethod
    def base_to_chars(chr_ints, original_base):
        numbers_per_char = int(math.ceil(math.log(256, original_base))) + 1

        if len(chr_ints) % numbers_per_char != 0:
            logging.debug("Base conversion is borked...")

        results = []
        for index in xrange(len(chr_ints) / numbers_per_char):
            number = 0
            for position in xrange(numbers_per_char):
                x = (index * numbers_per_char) + ((numbers_per_char - 1) - position)
                number += chr_ints[x] * (original_base ** position)

            results.append(number)

        return results

    def obfuscate_string(self, s):
        """
        Obfuscate the input binary string with the Markov model

        :param s: Input string, can be binary string, we immediately convert to ints anyways
        :return: The obfuscated string
        """
        # Convert each byte of the string to an integer
        parts = map(ord, list(s))

        # Convert parts to be new_base numbers
        temp_parts = []
        for p in parts:
            temp_parts.extend(MarkovKeyState.char_to_base(p, self.new_base))

        parts = temp_parts

        # It'll work eventually...I really should do some graph theory to remove words that break the algo
        # But I'll do that later
        while True:
            try:
                # Start off with a random first word (word following --terminate--)
                result = self.create_byte("--terminate--", random.randint(0, self.new_base))
                last = result[-1]

                for x in parts:
                    # This function is deceptively simple because 99% of the work is done in create_byte
                    to_append = self.create_byte(last, x)

                    for current in to_append:
                        # If its a --terminate--, add in a period, else, add in the word
                        if current != "--terminate--":
                            result.append(current)
                        else:
                            result.append(self.get_sentence_terminator())
                        last = current
            except AlgorithmFailException:
                continue
            break

        # Join it all into a string
        return self.join_obfuscated_string(result)

    def deobfuscate_string(self, s):
        """
        Well...now we need to be able to deobfuscate a string, right?

        :param s: The string to deobfuscate
        :return: The deobfuscated string
        """
        # Split it up by spaces into words
        parts = self.split_obfuscated_string(s)

        # Start our loop out with last being the first word in the string
        last = "--terminate--"
        # Get our last_list based on the words that can follow last
        last_list = sorted(self.raw_scores[last].items(), key=operator.itemgetter(1))[::-1]
        result = []

        running_values = None
        running_list_lengths = None
        running_value = None

        # Loop until we have no words left
        while len(parts) != 0:
            # Once you pop, you just can't stop
            current_word = parts.pop(0)

            # Convert .'s to --terminate--, as . is our terminator (I'll be back...)
            if current_word == self.get_sentence_terminator():
                current_word = "--terminate--"

            # If it is an empty string, then we should just move on and pretend nothing happened here
            if current_word == "":
                continue

            # Grab the list of words that can follow our current word
            current_list = sorted(self.raw_scores[current_word].items(), key=operator.itemgetter(1))[::-1]
            current_value = None

            # We need the value of the current word
            for x in xrange(len(last_list)):
                if last_list[x][0] == current_word:
                    current_value = x
                    break

            # The multiple word transitions make everything way more complicated
            if running_values is not None:
                # Keep pushing lengths of potential values until we get over 256
                running_list_lengths.append(len(last_list))
                running_values.append(current_value)
                if sum(running_list_lengths) >= self.new_base:
                    # We made it!  Now add the running value and start again
                    result.append(sum(running_values))
                    # running_value = sum(running_values)
                    running_list_lengths = None
                    running_values = None
            elif running_value is not None:
                # I think this is deprecated, but I wrote this a while ago
                result.append(current_value + running_value)
                running_value = None
            elif len(last_list) < self.new_base:
                # Keep adding to the running values, we aren't home yet
                running_values = [current_value]
                running_list_lengths = [len(last_list)]
            else:
                # Good old simple single word transition byte, reminds me of a simpler time
                # Back before I decided to support Markov models which did not have sufficient relations between words
                result.append(current_value)

            last = current_word
            last_list = current_list

        # Shake out the remaining drop
        if running_value is not None:
            result.append(running_value)

        # Shake out the remaining drops
        if running_values is not None:
            result.append(sum(running_values))

        # Trim off first number
        result = result[1:]

        # Change the number base
        result = MarkovKeyState.base_to_chars(result, self.new_base)

        # Join the ints together as chrs, to live in harmony forevaaaa
        return "".join(map(chr, result))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Regular expression to split our training files on
    split_regex = r'\n'

    # File/book to read for training the Markov model (will be read into memory)
    training_file = "../datasets/98.txt"

    # Obfuscating Markov engine
    m = MarkovKeyState()

    # Read the shared key into memory
    with open(training_file, "r") as f:
        text = f.read()

    # Split learning data into sentences, in this case, based on periods.
    map(m.learn_sentence, re.split(split_regex, text))

    # Begin automated tests ######

    for i in xrange(3):
        # Run a random test
        rand_string = "".join([chr(random.randint(0, 255)) for k in xrange(64)])
        if rand_string != m.deobfuscate_string(m.obfuscate_string(rand_string)):
            print "Failed integrity test"

    # Proved to cause an infinite failure prefix
    #m.create_byte("ruinating", 217)

    # End automated tests ######

    # Our data to obfuscate
    test_string = "This is a test message to prove the concept."
    print "Original string: {0}".format(test_string)

    # Obfuscate the data
    s = m.obfuscate_string(test_string)
    print "Obfuscated string: {0}".format(s)

    # Other Markov engine
    m2 = MarkovKeyState()

    # Split learning data into sentences, in this case, based on periods.
    map(m2.learn_sentence, re.split(split_regex, text))

    # Print out the deobfuscated string
    print "Deobfuscated string: {0}".format(m2.deobfuscate_string(s))
