import wave
from os.path import dirname, join as pjoin
from scipy.io import wavfile
import scipy.io
import matplotlib.pyplot as plt
import numpy as np
import re
from itertools import compress
from textwrap import wrap

_ONE = 8000
_ZERO = -12000
_BIAS = 2000
# TX_RATE = 9600 / 6
TX_RATE = 3600
# TX_RATE = 48000


def main():
    get_xxx_from_file(file_name = "Samples/4_shots.wav")

# --

def calculate_received_bit_counts(simple_sequence_list):
    received_bit_counts_no_round = []
    for pos in range(len(simple_sequence_list[0])):
        minimum = simple_sequence_list[0][pos]
        maximum = simple_sequence_list[0][pos]
        sum = 0

        for simple_sequence_pos in range(len(simple_sequence_list)):
            value = simple_sequence_list[simple_sequence_pos][pos]
            sum += value
            if value > maximum:
                maximum = value
            if value < minimum:
                minimum = value
        sum -= maximum
        sum -= minimum
        average = sum / (len(simple_sequence_list) - 2)
        received_bit_counts_no_round.append(average)

    if False:
        doubtful_samples = [value for value in received_bit_counts_no_round if 0.3 <= value - round(value, 0) <= 0.7]
        print(f'{doubtful_samples=}')

        print(f'{received_bit_counts_no_round=}')

    received_bit_counts = [int(round(value, 0)) for value in received_bit_counts_no_round]

    return received_bit_counts

# --

def convert_to_binary(received_bit_counts_no_round):
    converted_bits = []
    if received_bit_counts_no_round[0] > 5:
        converted_bits.append('START')
    res = list(zip(received_bit_counts_no_round[1:], received_bit_counts_no_round[2:] + received_bit_counts_no_round[:1]))

    for it in range(len(res)):
        if (abs(res[it][0]), abs(res[it][1])) == (4, 2):
            converted_bits.append('0')
        elif (abs(res[it][0]), abs(res[it][1])) == (1, 5):
            converted_bits.append('1')
        elif (abs(res[it][0])) == 8:
            converted_bits.append('END')

    return converted_bits

# --

def get_xxx_from_file(file_name):
    sample_rate, original_samples = wavfile.read(file_name)
    # print(f"number of channels = {original_samples.shape[1]}")
    samples_per_bit = sample_rate / TX_RATE
    binary_samples = [_ONE if sample >= _BIAS else _ZERO for sample in original_samples[:, 0]]

    if False:
        length = original_samples.shape[0] / sample_rate
        # print(f"length = {length}s")
        time = np.linspace(0., length, original_samples.shape[0])
        plt.plot(time, original_samples[:, 0], label="Left channel")
        # plt.plot(time, original_samples[:, 1], label="Right channel")
        plt.legend()
        plt.xlabel("Time [s]")
        plt.ylabel("Amplitude")
        print(f'{sample_rate=}; {TX_RATE=} => {samples_per_bit=}')
        print(original_samples.shape[0])
        print(type(original_samples.shape[0]))
        print(original_samples[:, 0])
        print(original_samples[:, 1])
        plt.show()
        plt.plot(time, binary_samples, label="Binary samples")
        plt.show()

    # --

    sampled_lengths = []
    current_value = binary_samples[0]
    current_length = 0

    for position in range(len(binary_samples)):
        if binary_samples[position] == current_value:
            current_length += 1
        else:
            sampled_lengths.append(current_length if current_value == _ONE else -current_length)
            current_value = binary_samples[position]
            current_length = 0

    # last sample
    sampled_lengths.append(current_length if current_value == _ONE else -current_length)
    if sampled_lengths[0] < -100:
        sampled_lengths = sampled_lengths[1:]
    print(f'{sampled_lengths=}')
    # --

    if False:
        received_bit_counts_1d = [round(sampled_length / samples_per_bit, 1) for sampled_length in sampled_lengths]
        print(f'{received_bit_counts_1d=}')

    received_bit_counts_no_round = [sampled_length / samples_per_bit for sampled_length in sampled_lengths]

    print(f'{received_bit_counts_no_round=}')

    # --

    doubtful_samples = [value for value in received_bit_counts_no_round if 0.4 <= value - round(value, 0) <= 0.7]
    print(f'{doubtful_samples=}')

    # --

    burst_list = []
    simple_sequence_list = []
    simple_sequence = []

    for bit_count in received_bit_counts_no_round:
        if abs(bit_count) >= 100:
            simple_sequence.append(bit_count)
            simple_sequence_list.append(simple_sequence)
            burst_list.append(simple_sequence_list)
            simple_sequence_list = []
            simple_sequence = []
        else:
            if len(simple_sequence)>0 and abs(bit_count) >= 20:
                simple_sequence_list.append(simple_sequence)
                simple_sequence = []

            simple_sequence.append(bit_count)

    # --

    received_bit_counts_list = []
    for simple_sequence_list in burst_list:
        received_bit_counts_no_round = calculate_received_bit_counts(simple_sequence_list)
        received_bit_counts_list.append(received_bit_counts_no_round)

        print(f'{received_bit_counts_no_round=}')

        formatted_bits = convert_to_binary(received_bit_counts_no_round)
        print(f'{formatted_bits=}')

        if False:
            for simple_sequence in simple_sequence_list:
                print(f'{simple_sequence=}')

            print('')

    # --

if False:
    received_bit_array = ['1' * bit_count if bit_count > 0 else '0' * -bit_count for bit_count in received_bit_counts]
    received_bit_string = ''.join(received_bit_array)
    num_ones = 8 - (len(received_bit_string) % 8)
    bit_string = '1' * (num_ones if num_ones < 8 else 0) + received_bit_string
    received_hex = hex(int(bit_string, 2))
    # received_bits_string = ''.join(received_bits)+'00000000'
    # received_bits_string = received_bits_string[0:int(len(received_bits_string)/8)*8]
    # print(''.join(received_bits))
    print(f'{received_hex=}')

# --

if False:
    # rev_x = re.findall('.{1,8}',x[::-1])
    # adjusted_x = rev_x[::-1]
    # if len(adjusted_x[0]) < 8:
    #	adjusted_x[0] = adjusted_x[0].rjust(8, "O")

    # print(adjusted_x)
    test = ''
    n = 0
    new = ''
    for s in test:
        if n % 2 == 0:
            new += '\\x'
        n += 1
        new += s
    # print(new)

if __name__ == '__main__':
    main()
