import json
import binascii
from os.path import exists
import bitstring as bitstring
from rflib import *

_ZERO = '0'  # \ = high_low
_ONE = '1'  # / = low_high

Q2_BIT_RATE_READ = 1700
Q2_BIT_RATE_SEND = 1696

Q2_PARTIAL_BITS_PER_BIT_READ = 4
Q2_PARTIAL_BITS_PER_BIT_SEND = 4
Q2_SAMPLES_PER_PARTIAL_BIT_READ = 3
Q2_SAMPLES_PER_PARTIAL_BIT_SEND = 1

Q2_PARTIAL_BITS_FOR_ZERO_SEND = _ONE * 2 + _ZERO * 2
Q2_PARTIAL_BITS_FOR_ONE_SEND = _ZERO * 2 + _ONE * 2

Q2_PARTIAL_BIT_RATE_READ = Q2_BIT_RATE_READ * Q2_PARTIAL_BITS_PER_BIT_READ
Q2_PARTIAL_BIT_RATE_SEND = Q2_BIT_RATE_SEND * Q2_PARTIAL_BITS_PER_BIT_SEND

Q2_PREAMBLE_BITS_SEND = 214
Q2_MESSAGE_BITS = 96
Q2_FINAL_PARTIAL_BITS_SEND = 12

Q2_MODULATION_FREQUENCY = 434421100

_MY_DEBUG = False


def get_stream_of_partial_bits_from_RF(d: RfCat, samples_per_bit):
    print("Entering RFlisten mode...  packets arriving will be displayed on the screen")
    print("(press Enter to stop)")

    while not keystop():
        list_of_streams_of_partial_bits = []
        while True:
            try:
                y, timestamp = d.RFrecv(blocksize=8 * Q2_SAMPLES_PER_PARTIAL_BIT_READ)
                yhex = binascii.hexlify(y).decode()
                stream_of_partial_bits = bin(int(yhex, 16))[2:]

                if could_be_part_of_preamble(stream_of_partial_bits, samples_per_bit):
                    _MY_DEBUG and print("(%5.3f) received:  %s | %s" % (timestamp, yhex, stream_of_partial_bits))
                    list_of_streams_of_partial_bits.append(stream_of_partial_bits)

                    # for blocksize in [148,252,252,148,252,252,148,252,252,148]:
                    for blocksize in [252, 252, 236, 252, 236, 252, 252]:
                        y, timestamp = d.RFrecv(blocksize=blocksize)
                        yhex = binascii.hexlify(y).decode()
                        stream_of_partial_bits = bin(int(yhex, 16))[2:]
                        _MY_DEBUG and print("(%5.3f) received:  %s | %s" % (timestamp, yhex, stream_of_partial_bits))
                        list_of_streams_of_partial_bits.append(stream_of_partial_bits)

                    break
                else:
                    print('.', end="")
                    list_of_streams_of_partial_bits = [stream_of_partial_bits]
            except ChipconUsbTimeoutException:
                print('!', end="")
                list_of_streams_of_partial_bits = []

        # stream_of_partial_bits = ''.join(list_of_streams_of_partial_bits)
        print('\n----------------------------')
        # return stream_of_partial_bits, timestamp
        return list_of_streams_of_partial_bits, timestamp


def could_be_part_of_preamble(stream_of_partial_bits, samples_per_bit):
    count_1s = len([bit for bit in stream_of_partial_bits if bit == "1"])
    fraction_of_ones = count_1s / len(stream_of_partial_bits)

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


def get_next_message_start_position(list_of_received_partial_bit_counts, first_position_to_check):
    for pos in range(first_position_to_check, len(list_of_received_partial_bit_counts) - 6):
        if -2.5 <= list_of_received_partial_bit_counts[pos] <= -1.5:
            if 3.5 <= list_of_received_partial_bit_counts[pos + 1] <= 4.5:
                if -4.5 <= list_of_received_partial_bit_counts[pos + 2] <= -3.5:
                    if 1.5 <= list_of_received_partial_bit_counts[pos + 3] <= 2.5:
                        if -2.5 <= list_of_received_partial_bit_counts[pos + 4] <= -1.5:
                            if 1.5 <= list_of_received_partial_bit_counts[pos + 5] <= 2.5:
                                return pos
    return -1


def get_simple_sequence(list_of_received_partial_bit_counts, first_position_to_check, last_position_to_check=None, expected_sample_sequence_lentgh=Q2_MESSAGE_BITS):
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
                simple_sequence.append(_ZERO)
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
                simple_sequence.append(_ONE)
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
        stream_of_partial_bits = remove_micro_glitches(stream_of_partial_bits)
        # _MY_DEBUG and print(f'{stream_of_partial_bits=}')

        list_of_received_partial_bit_counts = convert_stream_of_partial_bits_to_list_of_partial_bit_counts(stream_of_partial_bits, samples_per_bit)
        message_start_position = get_next_message_start_position(list_of_received_partial_bit_counts, 0)

        if message_start_position >= 0:
            extracted_simple_sequence = get_simple_sequence(list_of_received_partial_bit_counts, first_position_to_check=message_start_position)
            _MY_DEBUG and print(f'[{sample_number}] {extracted_simple_sequence=}')

            if len(extracted_simple_sequence) < Q2_MESSAGE_BITS:
                print(f'Extracted sequence is not long enough, {len(extracted_simple_sequence)} < Q2_MESSAGE_BITS, ignoring sequence')
            else:
                is_valid = True
                for symbol in extracted_simple_sequence[:Q2_MESSAGE_BITS]:
                    if symbol not in [_ONE, _ZERO]:
                        print('Error! Extracted sequence containing unexpected symbols, ignoring')
                        is_valid = False
                        break
                if is_valid:
                    burst_list.append(extracted_simple_sequence[:Q2_MESSAGE_BITS])
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
    list_of_received_partial_bit_counts = [sampled_length / samples_per_bit for sampled_length in sampled_lengths]

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
    file_name = f'{output_path}/Q2.{time.strftime("%Y-%m-%d")}.json'

    message_info = {
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

def execute_read_messages(d: RfCat, jam: bool):
    sample_rate = Q2_PARTIAL_BIT_RATE_READ * Q2_SAMPLES_PER_PARTIAL_BIT_READ

    d.setFreq(Q2_MODULATION_FREQUENCY)
    d.setMdmModulation(MOD_ASK_OOK)
    d.setMdmDRate(sample_rate)
    d.setMaxPower()
    d.lowball()
    # d.discover()

    try:
        while True:
            samples_per_bit = Q2_SAMPLES_PER_PARTIAL_BIT_READ
            list_of_streams_of_partial_bits, timestamp = get_stream_of_partial_bits_from_RF(d, samples_per_bit)

            if jam:
                d.setModeIDLE()
                return None

            list_of_valid_messages = get_list_of_valid_messages(list_of_streams_of_partial_bits, samples_per_bit)

            for valid_message, number_of_reads in list_of_valid_messages:
                print(f'{valid_message}, {number_of_reads}')
            #if number_of_reads == 3:
            if len(list_of_valid_messages) == 3:
                write_to_file(list_of_valid_messages, samples_per_bit, timestamp, "Q2", "not used", number_of_reads)
                return list_of_valid_messages

    except ChipconUsbTimeoutException:
        d.setModeIDLE()
        print("Please press <enter> to stop")
        sys.stdin.read(1)
        return None
    except Exception as e:
        d.setModeIDLE()
        return None


def convert_message_to_partial_bit_string_to_send(message: str):
    partial_bit_string = ''

    for bit in message:
        if bit == _ZERO:
            partial_bit_string += Q2_PARTIAL_BITS_FOR_ZERO_SEND
        elif bit == _ONE:
            partial_bit_string += Q2_PARTIAL_BITS_FOR_ONE_SEND

    return partial_bit_string


def add_x(partial_bit_string):
    partial_bit_string_hex = bitstring.BitArray(bin=partial_bit_string).tobytes()

    # TODO: controlar el caso cuando al longitud de la cadena no sea multiplo de 8 bits

    return partial_bit_string_hex


def execute_send_messages(d: RfCat, message_list:[]=None, jam:bool=None):
    if not message_list:
        message_list = ["101110000001001001100000101110101101111101110001000000011111101010110101001111010001000101111100",
                    "101110000001001001100000100000111111001111010010010001111001011111100011111001100100100010110101",
                    "101110000001001001100000100000001010011101100010101001100001111000100011001010001011101100000111"]
    else:
        message_list = [tup[0:3][0] for tup in message_list]

    tx_rate = Q2_PARTIAL_BIT_RATE_SEND * Q2_SAMPLES_PER_PARTIAL_BIT_SEND

    d.setFreq(Q2_MODULATION_FREQUENCY)
    d.setMdmModulation(MOD_ASK_OOK)
    d.setMdmDRate(tx_rate)
    d.setMaxPower()
    d.lowball()

    if jam:
        d.setPower(0x50)
        partial_bit_string_jam_message = '111000' * int(252 * 8 / 6)
        partial_bit_string_hex = add_x(partial_bit_string_jam_message)

        d.makePktFLEN(len(partial_bit_string_hex))
        d.RFxmit(partial_bit_string_hex, repeat=1)
    else:
        d.setMaxPower()
        partial_bit_string_preamble = convert_message_to_partial_bit_string_to_send(_ONE * Q2_PREAMBLE_BITS_SEND)
        partial_bit_string_suffix = _ZERO * (Q2_PARTIAL_BITS_PER_BIT_SEND * Q2_FINAL_PARTIAL_BITS_SEND)

        for pos, message in enumerate(message_list):
            partial_bit_string_message = convert_message_to_partial_bit_string_to_send(message)
            partial_bit_string_hex = add_x(partial_bit_string_preamble + partial_bit_string_message + partial_bit_string_suffix)

            # print(f'{partial_bit_string_preamble=}')
            print(f'{partial_bit_string_message=}')
            print(f'{partial_bit_string_hex=}')

            if pos == 0:
                d.makePktFLEN(len(partial_bit_string_hex))

            d.RFxmit(partial_bit_string_hex, repeat=0)

    d.setModeIDLE()

# --

def main(argv):
    if len(argv) > 1:
        d = RfCat(idx=0)
        mode = argv[1]
        if mode == "rx":
            execute_read_messages(d, jam=False)
        elif mode == "tx":
            execute_send_messages(d, jam=False)
        elif mode == "jam":
            for attempt in range(5):
                execute_read_messages(d, jam=True)
                execute_send_messages(d, jam=True)
        elif mode == "echo":
            for attempt in range(5):
                message_list = execute_read_messages(d, jam=False)
                time.sleep(0.1)
                execute_send_messages(d, message_list=message_list, jam=False)

# --

if __name__ == '__main__':
    main(argv=sys.argv)
