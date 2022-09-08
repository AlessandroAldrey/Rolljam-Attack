import json
import binascii
from os.path import exists
import bitstring as bitstring
from rflib import *
import time

_ZERO = '0'  # \ = high_low
_ONE = '1'  # / = low_high

ACLASS_BIT_RATE_READ = 1000
ACLASS_BIT_RATE_SEND = 997

ACLASS_PARTIAL_BITS_PER_BIT_READ = 4
ACLASS_PARTIAL_BITS_PER_BIT_SEND = 4
ACLASS_SAMPLES_PER_PARTIAL_BIT_READ = 2
ACLASS_SAMPLES_PER_PARTIAL_BIT_SEND = 1

ACLASS_PARTIAL_BITS_FOR_ZERO_SEND = _ONE * 2 + _ZERO * 2
ACLASS_PARTIAL_BITS_FOR_ONE_SEND = _ZERO * 2 + _ONE * 2

ACLASS_PARTIAL_BIT_RATE_READ = ACLASS_BIT_RATE_READ * ACLASS_PARTIAL_BITS_PER_BIT_READ
ACLASS_PARTIAL_BIT_RATE_SEND = ACLASS_BIT_RATE_SEND * ACLASS_PARTIAL_BITS_PER_BIT_SEND

#ACLASS_PREAMBLE_BITS_SEND = 172
ACLASS_PREAMBLE_BITS_SEND = 176
ACLASS_MESSAGE_BITS = 82
ACLASS_FINAL_PARTIAL_BITS_SEND = 162

ACLASS_MODULATION_FREQUENCY = 433945600
#ACLASS_MODULATION_FREQUENCY = 433919300

_MY_DEBUG = True


def get_stream_of_partial_bits_from_RF(d: RfCat, samples_per_bit, jam: bool):
    print("get_stream_of_partial_bits_from_RF(): Entering RFlisten mode...  packets arriving will be displayed on the screen")
    print("(press Enter to stop)")

    #while not keystop():
    if True:
        list_of_streams_of_partial_bits = []
        while True:
        #if True:
            try:
                y, timestamp = d.RFrecv(blocksize=16 * ACLASS_SAMPLES_PER_PARTIAL_BIT_READ)
                yhex = binascii.hexlify(y).decode()
                stream_of_partial_bits = bin(int(yhex, 16))[2:]

                if could_be_part_of_preamble(stream_of_partial_bits, samples_per_bit):
                    _MY_DEBUG and print("(%5.3f) received %d bytes: %s | %s" % (timestamp, int(len(yhex)/2), yhex, stream_of_partial_bits))
                    if jam:
                        print('Preamble detected')
                        return None, timestamp

                    list_of_streams_of_partial_bits.append(stream_of_partial_bits)
                    #blocksize = 252
                    #for times in range(3):
                    #for blocksize in [252, 252, 236, 252, 236, 252, 252]:
                    #for blocksize in [64, 252, 252]:
                    for blocksize in [256+128, 256+128, 256+128]: #256+256-32
                        y, timestamp = d.RFrecv(blocksize=blocksize)
                        yhex = binascii.hexlify(y).decode()
                        stream_of_partial_bits = bin(int(yhex, 16))[2:]
                        _MY_DEBUG and print("(%5.3f) received %d bytes: %s | %s" % (timestamp, int(len(yhex)/2), yhex, stream_of_partial_bits))
                        list_of_streams_of_partial_bits.append(stream_of_partial_bits)
                    print("get_stream_of_partial_bits_from_RF(): BREAK")
                    break
                else:
                    print('.', end="")
                    list_of_streams_of_partial_bits = [stream_of_partial_bits]
            except ChipconUsbTimeoutException as e:
                print(f'\n! {e=}')
                if len(list_of_streams_of_partial_bits) >2:
                    break
                else:
                    list_of_streams_of_partial_bits = []
            except BaseException as e2:
                print(f'\n!! {e2=}')
                list_of_streams_of_partial_bits = []

        print("get_stream_of_partial_bits_from_RF(): End")
        print('\n----------------------------')
        return list_of_streams_of_partial_bits, timestamp

def could_be_part_of_preamble(stream_of_partial_bits, samples_per_bit):
    count_1s = len([bit for bit in stream_of_partial_bits if bit == "1"])
    fraction_of_ones = count_1s / len(stream_of_partial_bits)

    if 0.4 <= fraction_of_ones <= 0.6:
        list_of_received_partial_bit_counts = convert_stream_of_partial_bits_to_list_of_partial_bit_counts(stream_of_partial_bits, samples_per_bit)[-17:-1]
        magic_sum = sum([value if pos % 2 == 0 else -value for pos, value in enumerate(list_of_received_partial_bit_counts)])
        magic_fraction = abs(magic_sum) / len(list_of_received_partial_bit_counts)

        print(f'[{round(magic_fraction, 1)}] ', end='')
        print(f'list_of_received_partial_bit_counts = {[round(value,1) for value in list_of_received_partial_bit_counts]}')
        if 1.9 <= magic_fraction <= 2.1:
            return True
        else:
            a = 1
    return False

def get_next_message_start_position(list_of_received_partial_bit_counts, first_position_to_check):
    for pos in range(first_position_to_check, len(list_of_received_partial_bit_counts) - 6):
        if 1.5 <= list_of_received_partial_bit_counts[pos] <= 3:
            if -3 <= list_of_received_partial_bit_counts[pos + 1] <= -1.5:
                if 1.5 <= list_of_received_partial_bit_counts[pos + 2] <= 3:
                    if -9 <= list_of_received_partial_bit_counts[pos + 3] <= -7:
                        if 1.5 <= list_of_received_partial_bit_counts[pos + 4] <= 3:
                            if -3 <= list_of_received_partial_bit_counts[pos + 5] <= -1.5:
                                return pos+4
    return -1

def get_simple_sequence(list_of_received_partial_bit_counts, first_position_to_check, last_position_to_check=None, expected_sample_sequence_lentgh=ACLASS_MESSAGE_BITS):
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

        first_position_to_check = 0
        while True:
            message_start_position = get_next_message_start_position(list_of_received_partial_bit_counts, first_position_to_check)

            if message_start_position >= 0:
                extracted_simple_sequence = get_simple_sequence(list_of_received_partial_bit_counts, first_position_to_check=message_start_position)
                #_MY_DEBUG and print(f'[{sample_number}] {extracted_simple_sequence=}')

                if len(extracted_simple_sequence) < ACLASS_MESSAGE_BITS:
                    print(f'Extracted sequence is not long enough, {len(extracted_simple_sequence)} < {ACLASS_MESSAGE_BITS}, ignoring sequence')
                else:
                    is_valid = True
                    for symbol in extracted_simple_sequence[:ACLASS_MESSAGE_BITS]:
                        if symbol not in [_ONE, _ZERO]:
                            print('Error! Extracted sequence containing unexpected symbols, ignoring')
                            is_valid = False
                            break
                    if is_valid:
                        burst_list.append(extracted_simple_sequence[:ACLASS_MESSAGE_BITS])
                first_position_to_check = message_start_position + 10
            else:
                _MY_DEBUG and print(f'[{sample_number}] ! Preamble not found, sample will be ignored')
                break
        print(f'[{sample_number}] list_of_received_partial_bit_counts = {[round(value,1) for value in list_of_received_partial_bit_counts]}')
        a = 1
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
    file_name = f'{output_path}/ACLASS.{time.strftime("%Y-%m-%d")}.json'

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

def execute_read_messages(d: RfCat, jam: bool):
    print('execute_read_messages(): Init')
    sample_rate = ACLASS_PARTIAL_BIT_RATE_READ * ACLASS_SAMPLES_PER_PARTIAL_BIT_READ

    #d.setModeRX()
    d.setFreq(ACLASS_MODULATION_FREQUENCY)
    d.setMdmModulation(MOD_ASK_OOK)
    d.setMdmDRate(sample_rate)
    d.setMaxPower()
    d.lowball()

    try:
        while True:
            print('execute_read_messages(): Calling get_stream_of_partial_bits_from_RF()')
            samples_per_bit = ACLASS_SAMPLES_PER_PARTIAL_BIT_READ
            list_of_streams_of_partial_bits, timestamp = get_stream_of_partial_bits_from_RF(d, samples_per_bit, jam)
            print(f'execute_read_messages(): End of call get_stream_of_partial_bits_from_RF(). {len(list_of_streams_of_partial_bits)} streams were returned')

            if jam:
                d.setModeIDLE()
                print('execute_read_messages(): End')
                return None

            list_of_valid_messages = get_list_of_valid_messages(list_of_streams_of_partial_bits, samples_per_bit)

            for valid_message, number_of_reads in list_of_valid_messages:
                print(f'{valid_message}, {number_of_reads}')
            if list_of_valid_messages and len(list_of_valid_messages) == 2:
                if list_of_valid_messages[0][0][0:4] == '0010' and list_of_valid_messages[1][0][0:4] == '0001' and list_of_valid_messages[0][0][4:] == list_of_valid_messages[1][0][4:]:
                    write_to_file(list_of_valid_messages, samples_per_bit, timestamp, "ACLASS", "not used", number_of_reads)
                    print('execute_read_messages(): End')
                    return list_of_valid_messages
                else:
                    print('execute_read_messages(): Ignoring messages')
    except KeyboardInterrupt:
        d.setModeIDLE()
        print("Please press <enter> to stop")
        sys.stdin.read(1)
    except Exception as e:
        d.setModeIDLE()
    print('execute_read_messages(): End with errors')
    return None

def convert_message_to_partial_bit_string_to_send(message: str):
    partial_bit_string = ''

    for bit in message:
        if bit == _ZERO:
            partial_bit_string += ACLASS_PARTIAL_BITS_FOR_ZERO_SEND
        elif bit == _ONE:
            partial_bit_string += ACLASS_PARTIAL_BITS_FOR_ONE_SEND

    return partial_bit_string


def add_x(partial_bit_string):
    partial_bit_string_hex = bitstring.BitArray(bin=partial_bit_string).tobytes()

    # TODO: controlar el caso cuando al longitud de la cadena no sea multiplo de 8 bits

    return partial_bit_string_hex


def execute_send_messages(d: RfCat, message_list:[]=None, jam:bool=None):
    if not message_list:
        message_list = ['0010101001000011111110000011001001111101011110000011101010101011011101111000000000',
                        '0001101001000011111110000011001001111101011110000011101010101011011101111000000000']
    else:
        message_list = [tup[0:2][0] for tup in message_list]

    tx_rate = ACLASS_PARTIAL_BIT_RATE_SEND * ACLASS_SAMPLES_PER_PARTIAL_BIT_SEND

    d.setFreq(ACLASS_MODULATION_FREQUENCY) #setMdmChanBW
    d.setMdmModulation(MOD_ASK_OOK)
    d.setMdmDRate(tx_rate)
    d.lowball()

    if jam:
        d.setPower(0x50)
        partial_bit_string_jam_message = '111000' * int(252 * 8 / 6)
        partial_bit_string_hex = add_x(partial_bit_string_jam_message)

        d.makePktFLEN(len(partial_bit_string_hex))
        d.RFxmit(partial_bit_string_hex, repeat=1)
    else:
        d.setMaxPower()
        partial_bit_string_preamble = convert_message_to_partial_bit_string_to_send(_ZERO * ACLASS_PREAMBLE_BITS_SEND)
        #partial_bit_string_mid_preamble = _ZERO * (ACLASS_PARTIAL_BITS_PER_BIT_SEND * 6) #og=98 mio=311 --> 24
        partial_bit_string_mid_preamble = _ZERO * int(ACLASS_PARTIAL_BITS_PER_BIT_SEND * 1.5) # TODO check that the calculation has not fractional part
        partial_bit_string_suffix = _ZERO * (ACLASS_PARTIAL_BITS_PER_BIT_SEND * ACLASS_FINAL_PARTIAL_BITS_SEND)

        #for pos, message in enumerate(message_list):
        partial_bit_string_message_0 = convert_message_to_partial_bit_string_to_send(message_list[0])
        partial_bit_string_message_1 = convert_message_to_partial_bit_string_to_send(message_list[1])
        partial_bit_string_hex = add_x(partial_bit_string_preamble + partial_bit_string_mid_preamble + partial_bit_string_message_0 + partial_bit_string_mid_preamble + partial_bit_string_message_1 + partial_bit_string_suffix)

        #print(f'{partial_bit_string_preamble=}')
        #print(f'{partial_bit_string_message=}')
        print(f'{partial_bit_string_hex=}')

        #   if pos == 0:
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
        elif mode == "jam_with_delay":
            for attempt in range(5):
                execute_read_messages(d, jam=True)
                execute_send_messages(d, jam=True)
                time.sleep(10)
        elif mode == "echo":
            for attempt in range(5):
                message_list = execute_read_messages(d, jam=False)
                time.sleep(0.1)
                execute_send_messages(d, message_list=message_list, jam=False)
        elif mode == "echo_with_delay":
            for attempt in range(5):
                message_list = execute_read_messages(d, jam=False)
                time.sleep(5)
                execute_send_messages(d, message_list=message_list, jam=False)

        d.setModeIDLE()

# --


if __name__ == '__main__':
    main(argv=sys.argv)
