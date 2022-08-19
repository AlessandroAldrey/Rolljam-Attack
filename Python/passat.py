import json
import binascii
import textwrap
from os.path import exists

import bitstring as bitstring
import numpy as np
import matplotlib.pyplot as plt
from rflib import *
from scipy.io import wavfile

_ONE = '1'
_ZERO = '0'

PASSAT_PREAMBLE_PARTIAL_BITS_READ = 29
# PASSAT_PREAMBLE_PARTIAL_BITS_SEND = 48
PASSAT_PREAMBLE_PARTIAL_BITS_SEND = 94
PASSAT_FINAL_PARTIAL_BITS_READ = 8
# PASSAT_FINAL_PARTIAL_BITS_SEND = 12
PASSAT_FINAL_PARTIAL_BITS_SEND = 26
PASSAT_BIT_RATE_READ = 1000
PASSAT_BIT_RATE_SEND = 1000
PASSAT_PARTIAL_BITS_PER_BIT_READ = 4
PASSAT_SAMPLES_PER_PARTIAL_BIT_READ = 4
# PASSAT_PARTIAL_BITS_PER_BIT_SEND = 10
PASSAT_PARTIAL_BITS_PER_BIT_SEND = 20

PASSAT_PARTIAL_BITS_FOR_ZERO_READ = '000011'
# PASSAT_PARTIAL_BITS_FOR_ZERO_SEND = '0000000111'
PASSAT_PARTIAL_BITS_FOR_ZERO_SEND = _ONE * 2 + _ZERO * 2

PASSAT_PARTIAL_BITS_FOR_ONE_READ = '011111'
# PASSAT_PARTIAL_BITS_FOR_ONE_SEND = '0011111111'
PASSAT_PARTIAL_BITS_FOR_ONE_SEND = _ZERO * 2 + _ONE * 2

PASSAT_PARTIAL_BIT_RATE_READ = PASSAT_BIT_RATE_READ * PASSAT_PARTIAL_BITS_PER_BIT_READ
PASSAT_PARTIAL_BIT_RATE_SEND = PASSAT_BIT_RATE_SEND * PASSAT_PARTIAL_BITS_PER_BIT_SEND
PASSAT_MESSAGE_BITS = 80
PASSAT_MODULATION_FREQUENCY = 434412100

MANCHESTER_ZERO = '0'  # \ = high_low
MANCHESTER_ONE = '1'  # / = low_high

_MY_DEBUG = False


def get_stream_of_partial_bits_from_RF(d: RfCat, samples_per_bit):
    print("Entering RFlisten mode...  packets arriving will be displayed on the screen")
    print("(press Enter to stop)")

    while not keystop():
        list_of_streams_of_partial_bits = []
        while True:
            try:
                blocksize = 30

                y, timestamp = d.RFrecv(blocksize=blocksize)
                yhex = binascii.hexlify(y).decode()
                stream_of_partial_bits = bin(int(yhex, 16))[2:]

                if could_be_part_of_preamble(stream_of_partial_bits, samples_per_bit):
                    _MY_DEBUG and print("(%5.3f) received:  %s | %s" % (timestamp, yhex, stream_of_partial_bits))
                    list_of_streams_of_partial_bits.append(stream_of_partial_bits)

                    blocksize = 252

                    for times in range(3):
                        y, timestamp = d.RFrecv(blocksize=blocksize)
                        yhex = binascii.hexlify(y).decode()
                        stream_of_partial_bits = bin(int(yhex, 16))[2:]
                        _MY_DEBUG and print("(%5.3f) received:  %s | %s" % (timestamp, yhex, stream_of_partial_bits))
                        list_of_streams_of_partial_bits.append(stream_of_partial_bits)

                    break
                else:
                    # if len(list_of_streams_of_partial_bits) >= 2:
                    #     list_of_streams_of_partial_bits.append(stream_of_partial_bits)
                    #     break
                    # else:
                    _MY_DEBUG or print('.', end="")
                    list_of_streams_of_partial_bits = [stream_of_partial_bits]
            except ChipconUsbTimeoutException:
                _MY_DEBUG or print('!', end="")
                list_of_streams_of_partial_bits = []

        # stream_of_partial_bits = ''.join(list_of_streams_of_partial_bits)
        print('\n----------------------------')
        # return stream_of_partial_bits, timestamp
        return list_of_streams_of_partial_bits, timestamp


def could_be_part_of_preamble(stream_of_partial_bits, samples_per_bit):
    # stream_of_partial_bits_filtered = remove_micro_glitches(stream_of_partial_bits)
    count_1s = len([bit for bit in stream_of_partial_bits if bit == "1"])
    fraction_of_ones = count_1s / len(stream_of_partial_bits)
    # print(f'{int(round(fraction_of_ones * 10, 0))}', end='')

    if 0.4 <= fraction_of_ones <= 0.6:
        list_of_received_partial_bit_counts = convert_stream_of_partial_bits_to_list_of_partial_bit_counts(stream_of_partial_bits, samples_per_bit)[1:-1]
        magic_sum = sum([value if pos % 2 == 0 else -value for pos, value in enumerate(list_of_received_partial_bit_counts)])
        magic_fraction = abs(magic_sum) / len(list_of_received_partial_bit_counts)

        print(f'[{round(magic_fraction, 1)}] ', end='')

        if 1.9 <= magic_fraction <= 2.1:
            return True
        else:
            a = 1
    return False
    if False:
        # return False
        stream_of_partial_bits_filtered_split_list = [stream_of_partial_bits_filtered[i:i + blocksize] for i in range(0, len(stream_of_partial_bits_filtered), blocksize)]
        for partial_stream in stream_of_partial_bits_filtered_split_list:
            count_1s = len([bit for bit in partial_stream if bit == "1"])
            fraction_of_ones = count_1s / len(partial_stream)
            # print(f'{round(fraction_of_ones*10,0)}', end='')
            if 0.4 <= fraction_of_ones <= 0.6:
                return True

        return False


def get_next_preamble_position(list_of_received_partial_bit_counts, first_position_to_check):
    for pos in range(first_position_to_check, len(list_of_received_partial_bit_counts) - 6):
        if 2.5 <= list_of_received_partial_bit_counts[pos] <= 3.5:
            if -3.5 <= list_of_received_partial_bit_counts[pos + 1] <= -2.5:
                if 2.5 <= list_of_received_partial_bit_counts[pos + 2] <= 3.5:
                    if -3.5 <= list_of_received_partial_bit_counts[pos + 3] <= -2.5:
                        if 2.5 <= list_of_received_partial_bit_counts[pos + 4] <= 3.5:
                            if -3.5 <= list_of_received_partial_bit_counts[pos + 5] <= -2.5:
                                return pos
    return -1


def get_simple_sequence(list_of_received_partial_bit_counts, first_position_to_check, last_position_to_check=None, expected_sample_sequence_lentgh=80):
    if last_position_to_check is None:
        last_position_to_check = len(list_of_received_partial_bit_counts) - 1

    simple_sequence = []

    pos = first_position_to_check
    left_value = list_of_received_partial_bit_counts[pos]

    while True:
        pos += 1
        if pos > last_position_to_check:
            break

        right_value = list_of_received_partial_bit_counts[pos]

        if 1.0 <= left_value <= 3.0:
            if right_value <= -1.0:
                simple_sequence.append(MANCHESTER_ZERO)
                if right_value < -2.0:
                    left_value = right_value + 2.0
                else:
                    left_value = 0
            else:
                if len(simple_sequence) >= expected_sample_sequence_lentgh:
                    break
                a = 1
        elif -3.0 <= left_value <= -1.0:
            if 1.0 <= right_value:
                simple_sequence.append(MANCHESTER_ONE)
                if right_value > 2.0:
                    left_value = right_value - 2.0
                else:
                    left_value = 0
            else:
                if len(simple_sequence) >= expected_sample_sequence_lentgh:
                    break
                a = 1
        if abs(left_value) < 1.0:
            pos += 1
            if pos > last_position_to_check:
                break
            left_value = list_of_received_partial_bit_counts[pos]
        elif abs(left_value) > 3:
            if len(simple_sequence) >= expected_sample_sequence_lentgh:
                break
            simple_sequence.append('<' if left_value < 0 else '>')

    return simple_sequence


def get_list_of_valid_messages(list_of_streams_of_partial_bits, samples_per_bit):
    burst_list = []

    for sample_number, stream_of_partial_bits in enumerate(list_of_streams_of_partial_bits):
        # if sample_number <= 2:
        #     continue

        # _MY_DEBUG and print(f'{stream_of_partial_bits=}')
        stream_of_partial_bits = remove_micro_glitches(stream_of_partial_bits)
        # _MY_DEBUG and print(f'{stream_of_partial_bits=}')

        list_of_received_partial_bit_counts = convert_stream_of_partial_bits_to_list_of_partial_bit_counts(stream_of_partial_bits, samples_per_bit)
        preamble_3_position = get_next_preamble_position(list_of_received_partial_bit_counts, 0)

        if preamble_3_position >= 0:
            extracted_simple_sequence = get_simple_sequence(list_of_received_partial_bit_counts, first_position_to_check=preamble_3_position + 6)
            _MY_DEBUG and print(f'[{sample_number}] {extracted_simple_sequence=}')

            if len(extracted_simple_sequence) < 80:
                print(f'Extracted sequence is not long enough, {len(extracted_simple_sequence)} < 80, ignoring sequence')
            else:
                is_valid = True
                for symbol in extracted_simple_sequence[:80]:
                    if symbol not in [MANCHESTER_ONE, MANCHESTER_ZERO]:
                        print('Error! Extracted sequence containing unexpected symbols, ignoring')
                        is_valid = False
                        break
                if is_valid:
                    burst_list.append(extracted_simple_sequence[:80])
        else:
            _MY_DEBUG and print(f'[{sample_number}] ! Preamble not found, sample will be ignored')
            _MY_DEBUG and print(f'[{sample_number}] {list_of_received_partial_bit_counts=}')

    message_matches = {}

    for message_on_test_as_list in burst_list:
        message_on_test_as_str = ''.join(message_on_test_as_list)
        if message_on_test_as_str in message_matches.keys():
            message_matches[message_on_test_as_str] = message_matches[message_on_test_as_str] + 1
        else:
            message_matches[message_on_test_as_str] = 1

    winner_message_count = max(message_matches.values())
    winner_messages_list = [(message, count) for message, count in message_matches.items() if count == winner_message_count]

    return winner_messages_list


def convert_stream_of_partial_bits_to_list_of_partial_bit_counts(stream_of_partial_bits, samples_per_bit):
    sampled_lengths = convert_stream_of_partial_bits_to_sampled_lengths_list(stream_of_partial_bits)
    # print(f'{sampled_lengths=}')

    if False:
        list_of_received_partial_bit_counts_1d = [round(sampled_length / samples_per_bit, 1) for sampled_length in sampled_lengths]
        print(f'{list_of_received_partial_bit_counts_1d=}')

    list_of_received_partial_bit_counts = [sampled_length / samples_per_bit for sampled_length in sampled_lengths]
    # print(f'{list_of_received_partial_bit_counts=}')
    return list_of_received_partial_bit_counts


def convert_stream_of_partial_bits_to_sampled_lengths_list(stream_of_partial_bits):
    sampled_lengths = []
    current_value = stream_of_partial_bits[0]
    current_length = 0
    for bit_value in stream_of_partial_bits:
        if bit_value == current_value:
            current_length += 1
        else:
            sampled_lengths.append(current_length if current_value == _ONE else -current_length)
            current_value = bit_value
            current_length = 1
    # last sample
    sampled_lengths.append(current_length if current_value == _ONE else -current_length)
    return sampled_lengths


def remove_micro_glitches(stream_of_partial_bits):
    stream_of_partial_bits = ''.join([stream_of_partial_bits[0]] + [_ONE if stream_of_partial_bits[pos - 1] == _ONE and stream_of_partial_bits[pos + 1] == _ONE else stream_of_partial_bits[pos] for pos in range(1, len(stream_of_partial_bits) - 2)] + [stream_of_partial_bits[-1]])
    return stream_of_partial_bits


# --

def write_to_file(list_of_streams, samples_per_bit, timestamp, type, state, number_of_reads):
    output_path = "/home/ochopelocho/PycharmProjects/TFG/Samples/JSON/"
    file_name = f'{output_path}/passat.{time.strftime("%Y-%m-%d")}.json'

    message_info = {  # stream, garage, timestamp, samples_per_bit, state in JSON
        "list_of_streams": list_of_streams,
        "samples_per_bit": samples_per_bit,
        "timestamp": timestamp,
        "type": type,
        "state": state,
        "number_of_reads": number_of_reads
    }

    if exists(file_name):
        with open(file_name, "r") as log_file:
            messages_info_list = json.load(log_file)
    else:
        messages_info_list = []

    messages_info_list.append(message_info)

    with open(file_name, "w") as log_file:
        json.dump(messages_info_list, log_file, indent=4)

    return None


# --

def execute_read_messages():
    sample_rate = PASSAT_PARTIAL_BIT_RATE_READ * PASSAT_SAMPLES_PER_PARTIAL_BIT_READ

    d = RfCat()
    d.setFreq(PASSAT_MODULATION_FREQUENCY)
    d.setMdmModulation(MOD_ASK_OOK)
    d.setMdmDRate(sample_rate)
    d.setMaxPower()
    d.lowball()
    # d.discover()

    try:
        while True:
            samples_per_bit = PASSAT_SAMPLES_PER_PARTIAL_BIT_READ
            list_of_streams_of_partial_bits, timestamp = get_stream_of_partial_bits_from_RF(d, samples_per_bit)
            list_of_valid_messages = get_list_of_valid_messages(list_of_streams_of_partial_bits, samples_per_bit)
            for valid_message, number_of_reads in list_of_valid_messages:
                print(f'{valid_message}, {number_of_reads}')
            if list_of_valid_messages:
                write_to_file(list_of_valid_messages, samples_per_bit, timestamp, "PASSAT", "not used", number_of_reads)

    except KeyboardInterrupt:
        d.setModeIDLE()
        print("Please press <enter> to stop")
        sys.stdin.read(1)
    except Exception as e:
        d.setModeIDLE()

    a = 1

def convert_message_to_partial_bit_string_to_send(message: str):
    partial_bit_string = ''

    for bit in message:
        if bit == MANCHESTER_ZERO:
            partial_bit_string += PASSAT_PARTIAL_BITS_FOR_ZERO_SEND
        elif bit == MANCHESTER_ONE:
            partial_bit_string += PASSAT_PARTIAL_BITS_FOR_ONE_SEND

    return partial_bit_string

def add_x(partial_bit_string):
    partial_bit_string_hex = bitstring.BitArray(bin=partial_bit_string).tobytes()

    # TODO: controlar el caso cuando al longitud de la cadena no sea multiplo de 8 bits

    return partial_bit_string_hex

def execute_send_messages():
    message = '00101111110011110101101101111000111100010011110010110011010010000000001111010100'
    rfcat_samples_per_partial_bit = 4
    tx_rate = PASSAT_BIT_RATE_SEND * rfcat_samples_per_partial_bit

    d = RfCat()
    d.setFreq(PASSAT_MODULATION_FREQUENCY)
    d.setMdmModulation(MOD_ASK_OOK)
    d.setMdmDRate(tx_rate)
    d.setMaxPower()
    d.lowball()

    partial_bit_string_preamble = convert_message_to_partial_bit_string_to_send(MANCHESTER_ZERO * 46) + '111100' + ('111000' * 3)
    partial_bit_string_message = convert_message_to_partial_bit_string_to_send(message)
    partial_bit_string_hex = add_x(partial_bit_string_preamble + partial_bit_string_message)

    print(f'{partial_bit_string_preamble=}')
    print(f'{partial_bit_string_message=}')
    print(f'{partial_bit_string_hex=}')

    d.makePktFLEN(len(partial_bit_string_hex))

    d.RFxmit(partial_bit_string_hex, repeat=1)
    d.setModeIDLE()

    # 369 para cualquier cadena, preambulo de 200 - preambulo normal, preambulo 29, mas cadena, mas 8 mini bits 0


# --

def main():
    if False:
        list_of_received_partial_bit_counts_1 = [32.25, -0.5, 7.25, -0.5, 2.5, -0.5, 28.0, -0.5, 0.5, -0.75, 0.25, -2.0, 1.5, -0.5, 1.25, -0.5, 1.75, -0.5, 0.5, -0.5, 0.25, -0.5, 0.75, -0.5, 1.0, -0.5, 6.0, -0.5, 4.25, -0.5, 6.5, -0.5, 14.0, -0.75, 5.0, -0.5, 9.0, -0.5, 1.0, -1.25, 1.75, -0.75, 0.25, -0.5, 5.0, -0.75, 41.75, -0.5, 3.25, -0.5, 0.25, -0.75, 22.5, -0.5, 3.25, -0.5, 6.0, -1.0, 1.25, -0.5, 0.25, -0.5, 1.5, -0.5, 17.25, -1.0, 1.0, -0.75, 2.5, -0.5, 10.0, -0.5, 4.5, -0.75, 2.25, -0.75, 9.25, -0.5, 1.0, -0.75, 14.0, -0.5, 2.75, -0.75, 7.25, -2.0, 0.75, -1.0, 1.75, -1.0, 2.75, -1.0, 16.5, -0.5, 7.0, -0.5, 8.25, -0.5, 28.75, -0.75, 0.75, -0.5, 0.25, -0.5, 14.25, -0.5, 6.25, -0.5, 2.75, -0.5, 4.0, -0.5, 6.5, -0.5, 10.75, -0.5, 3.5, -1.0, 1.0, -0.75, 7.5, -0.5, 1.0, -0.5, 5.0, -0.5, 6.75, -1.0, 0.25, -0.5, 4.25, -0.5, 2.25, -0.75, 1.25, -0.75, 20.0, -1.75, 1.0, -0.75, 0.5, -0.5, 0.5, -0.5, 4.75, -0.75, 0.25, -0.5, 4.0, -1.0, 5.0, -0.75, 18.5, -0.75, 0.5, -0.5, 1.25, -0.75, 2.25,
                                                 -0.5,
                                                 0.25, -0.5, 0.5, -0.75, 1.25, -0.5, 12.75, -0.5, 3.0, -0.5, 0.75, -0.75, 1.0, -2.5, 10.75, -0.5, 3.5, -2.0, 0.25, -1.0, 4.5, -0.75, 3.0, -0.5, 6.5, -0.5, 4.0, -0.5, 14.0, -0.5, 5.75, -0.5, 0.75, -1.25, 0.75, -0.75, 3.5, -0.5, 0.75, -0.5, 13.0, -0.5, 1.5, -0.5, 9.5, -0.75, 0.5, -0.75, 0.25, -0.75, 2.75, -0.5, 1.5, -0.5, 1.25, -0.5, 6.25, -0.5, 2.25, -0.75, 5.25, -1.0, 6.0, -0.75, 3.5, -0.5, 0.25, -1.0, 3.25, -0.5, 2.75, -0.5, 13.25, -0.5, 2.0, -1.25, 1.0, -1.0, 8.0, -0.5, 17.25, -2.0, 2.0, -2.25, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0,
                                                 2.0,
                                                 -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 3.0, -3.0, 3.0, -3.0, 3.0, -3.0, 2.0, -2.0, 2.0, -1.25, 5.75, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0,
                                                 -2.0,
                                                 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.75, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 3.0, -3.0, 3.0, -3.0, 3.0, -3.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0,
                                                 -4.0,
                                                 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 4.0, -2.0, 2.0, -121.5, 9.25, -0.75, 3.25, -0.75, 2.5, -0.5, 1.0, -0.5, 0.75, -0.5, 2.5, -0.75, 5.75, -1.5, 9.0, -0.5, 9.5, -0.5, 1.0, -0.5, 0.25, -1.0, 1.0, -0.5, 0.75, -1.25, 10.5, -0.5, 5.5, -1.0, 4.75, -0.5, 2.0, -0.5, 1.75, -0.5, 0.5, -0.5, 3.25, -0.75, 8.5, -0.5, 2.5, -1.0, 0.5, -0.75, 1.75, -0.5, 5.5, -1.0, 19.25, -0.75, 0.75, -0.75, 17.0, -0.75, 0.25, -0.5, 32.75, -0.5, 3.5, -0.5, 5.25, -0.5, 11.5, -0.5, 5.5, -0.5, 34.0, -0.5, 8.75, -0.5, 2.75, -0.5, 1.5, -0.75, 6.25, -0.75, 2.5, -0.5, 0.25, -0.5, 49.5, -0.5, 18.5, -1.0, 0.5, -0.5, 9.5, -0.75, 0.25, -0.75, 2.0, -0.5, 1.0, -0.5, 0.5, -0.5, 0.75, -0.5, 14.5, -0.5, 5.0, -0.5, 1.75, -0.5, 21.75, -0.5, 0.75, -0.75, 1.25, -0.5, 2.75, -0.5, 1.25, -0.5, 2.75, -0.5, 2.5, -0.5, 0.75, -0.5, 2.0, -0.5, 1.75, -0.5, 0.25, -0.75, 1.5, -0.5, 12.75, -0.5, 6.0, -0.5, 31.5]
        list_of_received_partial_bit_counts_2 = [8.5, -0.5, 5.0, -0.5, 3.0, -0.5, 0.5, -0.5, 9.25, -0.5, 5.25, -0.5, 13.75, -0.5, 33.0, -0.5, 17.75, -0.5, 16.0, -0.5, 0.75, -0.5, 1.0, -0.5, 3.0, -0.5, 24.25, -0.5, 11.0, -0.5, 0.25, -0.5, 9.25, -0.5, 53.5, -0.5, 16.0, -0.5, 8.75, -0.5, 37.0, -1.0, 14.0, -0.5, 23.75, -0.5, 21.25, -0.5, 0.25, -0.5, 6.5, -0.5, 0.25, -0.5, 13.5, -0.5, 27.5, -0.75, 2.25, -0.5, 1.0, -0.5, 2.75, -0.75, 4.5, -0.5, 10.75, -1.25, 0.25, -0.5, 12.5, -0.75, 21.0, -0.5, 1.0, -0.5, 18.25, -1.0, 3.5, -0.75, 0.75, -0.5, 19.5, -1.0, 6.75, -0.5, 16.75, -0.75, 1.25, -0.5, 4.25, -0.5, 1.0, -0.75, 1.0, -0.5, 0.5, -0.5, 8.75, -2.5, 31.5, -0.5, 96.25, -0.5, 19.75, -0.5, 11.25, -0.5, 19.0, -0.5, 9.75, -0.75, 1.5, -0.5, 3.0, -0.75, 16.0, -0.5, 10.5, -0.5, 7.5, -0.5, 5.0, -0.5, 0.25, -0.75, 6.75, -0.75, 26.0, -0.5, 7.5, -0.5, 12.0, -0.5, 19.0, -0.5, 0.25, -0.5, 0.75, -0.5, 0.25, -1.0, 2.0, -0.5, 2.5, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0,
                                                 -2.0,
                                                 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 1.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 3.0, -3.0, 3.0, -3.0, 3.0, -3.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 4.0,
                                                 -2.0,
                                                 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 4.0, -2.0, 2.0, -4.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -1.5, 1.0, -2.25, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 3.0, -3.0, 3.0, -3.0, 3.0, -3.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0,
                                                 -2.0,
                                                 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 4.0, -2.0, 2.0, -4.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 3.25, -1.75, 1.0, -142.5, 0.25, -11.0, 0.75, -1.5, 0.25, -2.25, 0.5, -3.75, 0.25, -0.5, 1.0, -1.25, 0.25, -1.0, 1.0, -0.75, 1.75, -0.75, 0.25, -0.5, 1.0, -0.75, 11.0, -0.5, 7.0, -0.5, 20.5, -0.5, 11.0, -0.5, 1.25, -0.5, 8.0, -1.0, 6.0, -0.5, 0.5, -0.5, 7.5, -0.5, 3.5, -0.5, 20.5, -0.5, 30.0, -0.5, 13.5, -0.5, 1.75, -0.5, 17.0, -0.5, 1.5, -0.5, 0.25, -0.5, 8.0, -0.5, 2.0, -0.5, 10.25, -1.25, 0.75, -0.75, 4.5, -0.5, 2.75, -0.5, 1.75, -0.5, 1.75, -0.5, 0.25, -0.5, 0.25, -0.5, 0.5, -0.5,
                                                 3.25,
                                                 -0.5, 4.75, -0.5, 1.75, -1.0, 4.5, -0.5, 1.5, -0.5, 4.25, -0.5, 1.5, -0.5, 14.75, -0.5, 12.5, -0.5, 1.0, -1.0, 0.5, -0.75, 7.5, -1.0, 5.5, -0.75, 17.0, -0.5, 9.75, -0.75, 0.75, -0.5, 3.75, -0.75, 0.75, -0.5, 5.0, -0.5, 5.75, -0.75, 0.5, -0.5, 2.75, -0.5, 25.0, -2.25, 3.25, -0.5, 2.5, -0.5, 2.25, -0.5, 4.25, -0.5, 0.25, -0.75, 0.25, -1.0, 0.5, -0.5, 1.25, -0.5, 6.5, -0.75, 4.25, -0.75, 3.25, -1.0, 2.25, -0.5, 8.25, -0.5, 0.5, -0.75, 0.75, -0.5, 5.75, -0.75, 3.25, -2.25, 5.25, -0.5, 2.0, -0.5, 1.25, -0.5, 15.5, -0.5, 1.5, -0.5, 2.75, -1.25, 0.25, -1.0, 0.25, -0.5, 5.25, -1.0, 6.5, -0.5, 1.5, -0.5, 23.75, -1.0, 5.25, -0.75, 4.0, -1.0, 12.0, -0.5, 8.5, -0.5, 2.25, -0.5, 1.0, -1.0, 4.0, -0.75, 16.0, -0.75, 2.75, -0.75, 1.25, -1.0, 0.25, -1.25, 1.0, -0.5, 3.75, -0.5, 1.25, -0.5, 4.75, -0.75, 11.75, -0.5, 0.25, -0.5, 10.5, -0.5, 7.25, -0.5, 55.75, -0.75, 3.0, -0.75, 5.25, -0.5, 3.0, -0.75, 10.25, -0.5, 4.0, -0.5, 4.0, -0.5, 2.25, -0.5, 6.0,
                                                 -0.75,
                                                 12.25, -0.5, 1.25, -0.5, 1.25, -0.5, 2.5, -0.5, 5.0, -0.5, 1.5, -0.75, 5.75, -0.75, 0.25, -1.25, 10.0, -0.75, 2.25, -0.5, 4.75, -0.5, 0.5, -2.0, 1.5, -0.5, 4.75, -0.5, 0.25, -0.75, 2.5, -0.75, 1.0, -0.75, 3.5, -1.0, 1.25, -0.5, 0.25, -0.5, 1.5]
        list_of_received_partial_bit_counts_3 = [10.25, -0.5, 18.0, -1.0, 31.75, -0.5, 2.0, -0.75, 26.5, -0.5, 9.25, -0.5, 0.75, -0.5, 7.75, -0.5, 65.5, -0.5, 17.0, -0.5, 3.0, -0.75, 16.0, -0.75, 0.25, -0.75, 0.25, -2.0, 1.5, -0.5, 16.0, -0.5, 11.75, -0.5, 14.25, -0.5, 19.5, -0.5, 30.0, -0.5, 14.25, -0.5, 1.5, -0.5, 0.25, -0.5, 7.75, -0.5, 0.25, -0.75, 28.0, -0.5, 2.25, -0.75, 1.5, -0.5, 22.5, -0.5, 7.0, -0.5, 71.5, -1.0, 9.5, -0.5, 2.5, -0.5, 17.5, -0.5, 3.25, -0.5, 8.5, -0.5, 2.5, -0.5, 0.25, -0.5, 24.25, -0.5, 0.75, -0.75, 43.5, -0.5, 29.5, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0,
                                                 -2.0,
                                                 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 3.0, -3.0, 3.0, -3.0, 3.0, -3.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 4.0, -3.25, 1.5, -2.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0,
                                                 -2.0,
                                                 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 3.0, -3.0, 3.0, -3.0, 3.0, -3.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.5, 2.5, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 4.0, -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0,
                                                 -2.0,
                                                 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 4.0, -2.0, 2.0, -128.75, 0.25, -12.5, 0.25, -0.75, 0.25, -2.5, 0.25, -1.75, 0.5, -0.5, 0.75, -0.5, 0.75, -5.5, 0.25, -0.75, 1.5, -0.5, 6.75, -0.5, 0.25, -0.5, 1.5, -0.5, 1.0, -0.5, 19.25, -0.5, 3.0, -0.5, 0.25, -0.75, 2.75, -0.5, 0.25, -0.5, 27.75, -0.5, 1.75, -0.75, 2.5, -0.75, 0.25, -0.5, 1.25, -0.5, 1.0, -0.5, 3.25, -0.5, 6.25, -0.5, 1.25, -0.5, 2.25, -0.5, 3.0, -0.75, 1.0, -0.5, 8.75, -0.5, 0.75, -0.75, 26.25, -0.5, 0.5, -0.75, 14.5, -0.5, 2.25, -1.0, 0.5, -0.5, 7.75, -0.75, 8.75, -0.75, 16.0, -0.5, 2.0, -0.5, 0.75, -1.25, 3.5, -1.25, 11.0, -0.5, 0.5, -0.5, 1.75, -0.5, 1.0, -0.75, 0.25, -0.5, 5.0, -0.5, 0.25, -0.5, 4.0, -0.75, 0.75, -0.5, 2.25, -0.5, 1.5, -0.5, 1.75, -0.75, 0.25, -0.5, 0.25, -0.75, 5.0, -0.75, 4.25, -0.5, 1.5, -0.5, 2.5, -0.5, 1.5, -2.25, 3.75, -0.5, 7.5, -0.5, 2.75, -0.5, 0.25, -0.5, 1.0, -1.0, 3.5, -0.5,
                                                 22.75,
                                                 -0.75, 31.0, -0.5, 13.25, -0.5, 11.0, -0.5, 32.75, -0.75, 2.5, -0.5, 2.25, -0.5, 1.0, -0.5, 4.75, -0.5, 14.25, -0.5, 9.75, -0.75, 14.75, -0.5, 0.75, -1.0, 21.0, -0.5, 2.5, -0.75, 0.25, -0.5, 0.75, -0.5, 4.5, -1.0, 2.0, -0.5, 21.25, -0.5, 0.25, -0.75, 0.25, -0.5, 4.5, -0.5, 1.0, -0.5, 0.75, -0.75, 0.25, -1.75, 2.0, -0.5, 8.75, -0.5, 3.75, -0.5, 2.0, -0.5, 7.25, -0.75, 0.25, -0.5, 0.25, -0.5, 2.0, -0.75, 0.25, -1.0, 0.75, -0.75, 3.0, -0.75, 4.25, -0.75, 0.75, -0.5, 0.75, -2.0, 1.5, -0.25]
        list_of_received_partial_bit_counts_4 = [8.5, -0.5, 25.5, -0.5, 3.5, -2.0, 1.0, -0.75, 2.25, -0.5, 0.75, -2.0, 1.25, -1.0, 0.25, -1.0, 3.0, -0.5, 0.75, -0.5, 0.25, -0.75, 0.5, -0.5, 0.5, -0.5, 5.0, -0.5, 1.5, -0.5, 4.0, -0.5, 2.0, -0.5, 2.5, -0.5, 3.5, -0.5, 2.0, -0.5, 3.0, -0.75, 11.0, -0.75, 3.75, -0.5, 1.75, -0.5, 6.75, -0.5, 2.5, -0.5, 1.25, -0.75, 1.0, -0.5, 0.75, -0.5, 18.25, -0.75, 92.75, -0.5, 5.25, -0.5, 1.5, -0.5, 3.5, -0.5, 3.75, -0.75, 4.0, -0.5, 4.25, -0.5, 17.75, -0.5, 0.25, -0.5, 3.0, -0.5, 0.25, -0.75, 7.0, -1.0, 4.0, -0.75, 3.0, -0.5, 0.75, -0.75, 2.75, -0.5, 3.25, -0.75, 6.5, -0.5, 4.25, -0.5, 4.0, -0.5, 12.0, -0.5, 1.25, -0.5, 0.25, -0.5, 4.0, -0.5, 2.0, -0.75, 2.25, -1.0, 0.5, -0.5, 1.25, -0.5, 0.25, -1.25, 5.25, -1.0, 1.25, -0.5, 15.5, -0.5, 1.5, -0.75, 1.25, -0.5, 3.5, -0.75, 1.25, -0.75, 0.5, -0.5, 2.25, -0.5, 6.75, -0.5, 2.75, -0.5, 1.25, -0.5, 5.5, -0.5, 1.75, -0.5, 6.25, -1.25, 0.25, -0.5, 0.25, -0.5, 2.75, -0.5, 0.75, -0.5, 12.0, -0.5, 5.5, -0.5,
                                                 7.75,
                                                 -0.5, 4.5, -0.5, 0.5, -0.5, 11.25, -0.5, 0.5, -0.75, 0.5, -0.5, 7.75, -0.5, 5.0, -0.5, 1.75, -0.5, 11.25, -0.5, 0.5, -0.5, 3.25, -1.0, 3.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 3.0, -3.0, 3.0, -3.0, 3.0, -3.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0,
                                                 4.0,
                                                 -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -1.0, 1.75, -2.0, 2.0, -4.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 3.0, -3.0, 3.0, -3.0, 3.0, -3.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0,
                                                 -2.0, 2.0,
                                                 -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 3.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 4.0, -2.0, 2.0, -139.75, 0.75, -7.5, 0.5, -0.5, 0.25, -2.5, 0.5, -2.75, 0.5, -0.75, 0.5, -0.5, 1.5, -0.5, 67.0, -1.0, 11.0, -0.5, 22.5, -0.5, 10.75, -0.75, 15.5, -0.5, 1.25, -0.5, 16.5, -0.5, 4.5, -0.5, 24.25, -0.5, 7.0, -0.5, 9.75, -0.5, 3.0, -0.75, 0.5, -1.0, 3.75, -1.0, 0.25, -0.5, 3.0, -0.5, 0.75, -1.0, 0.5, -0.75, 0.5, -0.75, 0.25, -0.75, 3.25, -0.5, 3.75, -0.5, 6.25, -0.5, 32.75, -0.75, 0.25, -1.25, 2.5, -0.5, 0.25, -0.5, 16.5, -0.5, 2.25, -0.5, 6.5,
                                                 -0.75,
                                                 12.75, -1.25, 6.75, -0.75, 0.25, -0.5, 8.75, -0.5, 0.5, -0.5, 5.25, -0.5, 3.25, -0.75, 6.5, -0.5, 0.5, -1.75, 0.25, -2.25, 5.75, -0.75, 1.0, -0.5, 1.25, -0.5, 5.0, -0.5, 2.0, -0.5, 16.5, -0.75, 2.0, -1.25, 2.25, -0.5, 16.75, -0.5, 0.75, -0.75, 0.75, -1.0, 18.25, -2.75, 0.25, -0.5, 1.25, -0.75, 0.75, -1.0, 0.75, -1.25, 0.75, -0.75, 0.25, -1.5, 6.25, -0.5, 6.0, -1.75, 0.25, -1.0, 0.75, -2.0, 1.25, -2.25, 0.25, -1.5, 0.25, -0.5, 0.25, -1.25, 1.0, -1.5, 0.5, -1.25, 0.25, -0.75, 0.5, -0.5, 2.75, -1.25, 0.75, -0.75, 43.75, -0.5, 19.75, -0.75, 12.5, -0.75, 22.0, -0.5, 13.25, -0.5, 18.25, -0.5, 9.5, -0.5, 2.25, -0.75, 5.75, -0.5, 2.25, -0.75, 29.0, -0.5, 0.75, -0.5, 6.5, -0.5, 8.5]
        list_of_received_partial_bit_counts_5 = [9.25, -0.5, 0.25, -0.5, 0.25, -0.5, 0.5, -0.5, 1.25, -1.0, 1.5, -0.5, 18.5, -0.5, 0.25, -1.0, 9.75, -0.5, 1.5, -0.5, 0.25, -2.25, 5.25, -0.5, 0.25, -0.5, 0.75, -0.5, 1.25, -0.5, 5.75, -0.75, 0.75, -0.5, 3.0, -0.75, 0.75, -1.25, 0.25, -1.0, 2.25, -0.5, 6.5, -0.5, 8.25, -0.5, 0.25, -0.5, 1.0, -0.5, 13.5, -0.75, 2.0, -0.5, 2.25, -2.0, 3.0, -0.75, 4.0, -0.5, 8.0, -0.75, 0.75, -1.5, 0.25, -1.5, 2.5, -0.75, 0.25, -0.75, 0.5, -0.5, 9.25, -0.75, 1.5, -0.75, 7.5, -0.5, 0.25, -0.5, 9.25, -0.75, 9.25, -0.5, 13.25, -0.5, 0.25, -0.5, 2.0, -0.5, 1.5, -0.5, 9.25, -0.75, 0.25, -0.5, 1.0, -0.75, 17.75, -1.75, 0.25, -3.25, 1.0, -0.5, 0.25, -2.75, 3.0, -0.5, 2.5, -1.0, 6.0, -0.5, 1.5, -0.5, 2.5, -0.75, 1.25, -0.75, 15.75, -0.5, 3.5, -0.5, 0.75, -0.5, 0.75, -0.5, 0.5, -0.5, 3.75, -0.5, 4.5, -1.25, 2.0, -0.5, 0.25, -0.5, 5.0, -0.5, 5.25, -0.5, 7.75, -0.5, 1.0, -0.75, 0.25, -0.5, 8.0, -1.0, 21.0, -0.75, 37.0, -0.75, 4.5, -0.5, 4.75, -0.5, 25.5, -1.5, 2.0,
                                                 -0.5,
                                                 9.75, -0.5, 4.0, -0.5, 0.25, -0.5, 21.75, -0.5, 22.75, -0.5, 0.75, -0.5, 0.5, -0.75, 7.0, -0.5, 1.5, -0.5, 6.75, -0.5, 3.25, -1.75, 4.25, -0.5, 3.25, -0.5, 1.0, -0.75, 1.0, -0.5, 1.25, -0.75, 4.25, -0.5, 0.75, -0.75, 8.75, -0.5, 1.25, -0.75, 0.25, -1.0, 27.25, -0.5, 1.5, -0.75, 6.0, -0.75, 8.25, -2.5, 0.5, -1.5, 1.5, -0.5, 1.5, -0.5, 6.0, -0.5, 3.0, -0.5, 2.0, -0.5, 1.0, -0.5, 0.25, -0.5, 1.0, -0.75, 2.75, -0.5, 3.5, -0.5, 8.5, -0.75, 3.25, -0.5, 3.5, -0.5, 0.5, -0.5, 1.25, -0.5, 4.0, -0.5, 0.25, -0.5, 3.75, -0.5, 0.25, -0.5, 0.25, -2.25, 1.0, -0.75, 1.0, -0.75, 4.25, -0.5, 3.5, -0.5, 14.25, -1.0, 0.5, -0.75, 4.25, -0.5, 2.75, -0.5, 1.5, -0.5, 0.25, -0.75, 3.5, -0.5, 6.0, -0.5, 1.5, -1.0, 0.25, -0.5, 0.5, -0.5, 15.5, -0.75, 0.25, -0.5, 6.25, -2.25, 0.25, -0.5, 1.25, -1.0, 0.25, -0.5, 4.75, -0.5, 2.75, -0.5, 6.25, -0.5, 2.5, -0.75, 0.75, -0.5, 2.75, -0.5, 3.75, -1.25, 5.5, -0.5, 4.75, -0.5, 7.0, -1.25, 0.25, -0.75, 1.0, -0.5, 5.5, -1.5,
                                                 0.25,
                                                 -1.5, 0.25, -0.75, 0.5, -0.5, 1.5, -0.5, 13.5, -0.5, 6.5, -0.75, 0.25, -0.75, 4.25, -0.75, 0.5, -0.5, 0.5, -0.5, 12.0, -1.25, 0.25, -2.5, 0.75, -1.5, 0.75, -0.5, 0.75, -2.0, 0.25, -1.0, 0.25, -1.0, 0.25, -0.5, 0.25, -1.25, 2.5, -0.75, 0.25, -0.75, 11.5, -0.5, 8.25, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -1.75, 1.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 3.0, -3.0, 3.0, -3.0, 3.0, -3.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 2.0,
                                                 -2.0,
                                                 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -1.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0,
                                                 -2.0,
                                                 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 3.0, -3.0, 3.0, -3.0, 3.0, -3.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 2.0, -2.0, 2.0, -2.0, 4.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -2.0, 2.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 4.0, -2.0, 2.0, -2.0, 2.0, -4.0, 2.0, -2.0, 4.0, -4.0, 4.0, -4.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 4.0, -2.0, 2.0, -4.0, 2.0, -2.0, 2.0, -2.0, 2.0, -2.0, 3.0, -2.0, 2.0, -2.0, 2.0, -4.0, 4.0, -147.0, 0.25, -1.0, 0.25, -1.0, 0.25, -1.25, 0.5, -3.75, 0.25, -1.75, 0.75, -1.0, 0.75, -0.5, 0.75, -0.75, 0.25, -1.0, 0.25, -0.5, 0.25, -0.75, 0.25, -0.5, 1.0, -0.75, 0.75, -0.5, 0.75, -0.5, 2.5, -0.5, 3.5,
                                                 -0.5,
                                                 0.5, -1.0, 1.0, -1.0, 11.25, -0.5, 2.75, -0.75, 6.75, -0.5, 9.5, -0.75, 0.75, -0.75, 1.5, -0.5, 3.25, -0.5, 0.5, -1.0, 1.25, -0.5, 0.75, -0.5, 0.25, -0.5, 2.25, -0.75, 4.5, -1.25, 2.25, -1.75, 2.25, -0.5, 0.5, -0.5, 1.0, -0.5, 0.75, -0.5, 13.25, -0.5, 4.5, -0.75, 0.5, -0.5, 1.5, -0.5, 0.75, -0.75, 14.25, -0.5, 0.25, -0.5, 0.5, -0.5, 8.0, -0.75, 0.25, -0.75, 2.75, -0.5, 1.5, -1.0, 1.5, -0.5, 2.25, -0.5, 0.25, -0.75, 1.25, -0.5, 0.75, -0.75, 10.25, -0.5, 0.75, -0.75, 8.5, -0.5, 9.5, -0.5, 2.5, -0.5, 1.5, -0.5, 4.25, -0.5, 2.0, -0.5, 3.25, -0.5, 4.25, -1.0, 7.75, -0.75, 2.75, -0.75, 0.25, -0.75, 0.25, -0.5, 0.5, -0.75, 5.0, -0.75, 1.75, -0.5, 6.0, -0.5, 17.0, -0.5, 16.75, -0.5, 2.25, -0.75, 0.25, -0.5, 9.5, -0.5, 3.25, -0.5, 0.75, -0.5, 0.25, -0.5, 0.5, -1.25, 2.25, -0.5, 17.0, -0.5, 2.5, -0.5, 0.5, -0.5, 0.25, -1.75, 0.25, -0.75, 0.75, -0.5, 1.75, -1.5, 3.25, -0.5, 2.75, -0.5, 2.25, -0.5, 0.5, -1.0, 2.5, -0.5, 19.0, -0.5, 17.5, -0.5,
                                                 65.25,
                                                 -0.5, 15.5, -0.5, 23.25, -1.0, 10.5, -0.5, 19.75, -0.5, 8.5, -0.75, 0.25, -0.5, 10.25, -0.5, 1.0, -0.5, 16.5, -0.5, 2.5, -0.75, 1.5, -0.5, 4.25, -0.5, 11.5, -0.75, 0.25, -0.5, 0.25, -0.75, 0.75, -0.5, 4.0, -0.75, 14.25, -0.5, 3.75, -0.5, 9.75, -1.75, 3.0, -1.0, 0.25, -0.5, 1.75, -0.5, 0.25, -1.0, 2.75, -0.75, 0.25, -0.75, 4.0, -0.5, 2.25, -2.25, 0.25, -1.0, 0.25, -0.5, 2.25, -0.5, 11.5, -0.5, 9.25, -0.75, 7.0, -0.75, 4.5, -1.0, 2.75, -0.5, 3.25, -0.5, 22.5, -0.5, 0.5, -0.5, 0.25, -2.0, 3.0, -0.5, 2.25, -0.5, 3.5, -0.5, 2.5, -0.5, 0.5, -0.5, 0.5, -0.5, 28.25, -0.5, 36.0]

        list_of_received_partial_bit_counts = list_of_received_partial_bit_counts_3

        first_preamble3_posisition = get_next_preamble_position(list_of_received_partial_bit_counts, 0)
        if first_preamble3_posisition < 0:
            print(f'! First preamble not found, sample will be ignored')
        second_preamble3_posisition = get_next_preamble_position(list_of_received_partial_bit_counts, first_preamble3_posisition + 6)
        if second_preamble3_posisition < 0:
            print(f'! Second preamble not found, sample will be ignored')
        third_preamble3_posisition = get_next_preamble_position(list_of_received_partial_bit_counts, second_preamble3_posisition + 6)
        if third_preamble3_posisition >= 0:
            print(f'! Unpexpected third preamble at position {third_preamble3_posisition}')

        first_simple_sequence = get_simple_sequence(list_of_received_partial_bit_counts, first_position_to_check=first_preamble3_posisition + 6, last_position_to_check=second_preamble3_posisition - 1)
        second_simple_sequence = get_simple_sequence(list_of_received_partial_bit_counts, first_position_to_check=second_preamble3_posisition + 6)
        print(f'{first_simple_sequence=}')
        print(f'{second_simple_sequence=}')

    if False:
        list_of_received_partial_bit_counts = list_of_received_partial_bit_counts_2
        # list_of_valid_messages_1 = get_list_of_valid_messages(list_of_received_partial_bit_counts, 1)
        first_preamble3_posisition = get_next_preamble_position(list_of_received_partial_bit_counts, 0)

        get_simple_sequence(list_of_received_partial_bit_counts, first_preamble3_posisition + 6)

        second_preamble3_posisition = get_next_preamble_position(list_of_received_partial_bit_counts, first_preamble3_posisition + 6)
        third_preamble3_posisition = get_next_preamble_position(list_of_received_partial_bit_counts, second_preamble3_posisition + 6)
        a = 1

    execute_read_messages()
     #execute_send_messages()


# --

if __name__ == '__main__':
    main()
