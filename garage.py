import wave
from os.path import dirname, join as pjoin
from scipy.io import wavfile
import scipy.io
import matplotlib.pyplot as plt
import numpy as np
import re
from textwrap import wrap

#sample_rate, original_samples = wavfile.read("ON_reduced.wav")
sample_rate, original_samples = wavfile.read("ON_reduced.wav")
#print(f"number of channels = {original_samples.shape[1]}")
length = original_samples.shape[0] / sample_rate
#print(f"length = {length}s")

time = np.linspace(0., length, original_samples.shape[0])
plt.plot(time, original_samples[:, 0], label="Left channel")
#plt.plot(time, original_samples[:, 1], label="Right channel")
plt.legend()
plt.xlabel("Time [s]")
plt.ylabel("Amplitude")

_ONE = 8000
_ZERO = -12000
_BIAS = 2000
#TX_RATE = 9600 / 6
TX_RATE = 3600
#TX_RATE = 48000
samples_per_bit = sample_rate / TX_RATE

#print(f'{sample_rate=}; {TX_RATE=} => {samples_per_bit=}')
#print(original_samples.shape[0])
#print(type(original_samples.shape[0]))
#print(original_samples[:, 0])
#print(original_samples[:, 1])
#plt.show()
# --

binary_samples = [_ONE if sample >= _BIAS else _ZERO for sample in original_samples[:, 0]]
plt.plot(time, binary_samples, label="Binary samples")
#plt.show()

# --

sampled_lengths = []
current_value = binary_samples[0]
current_length = 0

for position in range (len(binary_samples)):
	if binary_samples[position] == current_value:
		current_length += 1
	else:
		sampled_lengths.append(current_length if current_value == _ONE else -current_length)
		current_value = binary_samples[position]
		current_length = 0

#last sample
sampled_lengths.append(current_length if current_value == _ONE else -current_length)
print(sampled_lengths)

# --

received_bit_counts_1d = [round(sampled_length/samples_per_bit,1) for sampled_length in sampled_lengths]
#received_bit_counts = [int(round(sampled_length/samples_per_bit,1)) for sampled_length in sampled_lengths]
#received_bit_counts = [int(round(sampled_length/samples_per_bit,0)) for sampled_length in sampled_lengths]
print(received_bit_counts_1d)

# --

received_bit_counts = [int(round(sampled_length/samples_per_bit,0)) for sampled_length in sampled_lengths]
#received_bit_counts = [int(round(sampled_length/samples_per_bit,1)) for sampled_length in sampled_lengths]
#received_bit_counts = [int(round(sampled_length/samples_per_bit,0)) for sampled_length in sampled_lengths]
print(received_bit_counts)

# --

received_bit_counts_on =  [29, -4, 2, -4, 2, -4, 2, -1, 5, -1, 5, -4, 2, -4, 2, -4, 2, -1, 5, -1, 5, -4, 2, -1, 5, -4, 2, -1, 5, -1, 5, -1, 5, -1, 5, -4, 2, -1, 5, -4, 2, -1, 5, -1, 5, -1, 5, -4, 2, -4, 2, -1, 5, -1, 5, -4, 2, -4, 2, -1, 5, -4, 2, -1, 5, -4, 2, -4, 2, -1, 5, -4, 2, -4, 2, -1, 5, -1, 5, -4, 2, -1, 5, -1, 5, -1, 5, -4, 2, -4, 2, -4, 2, -1, 5, -4, 2, -1, 5, -4, 2, -1, 5, -4, 2, -4, 2, -4, 2, -4, 2, -1, 5, -4, 2, -1, 5, -1, 5, -1, 5, -1, 5, -1, 5, -1, 5, -4, 2, -1, 4, -4, 2, -1, 5, -4, 2, -1, 5, -1, 5, -1, 5, -1, 5, -4, 2, -4, 2, -1, 5, -4, 2, -4, 2, -4, 2, -4, 2, -4, 2, -8]
received_bit_counts_off = [29, -4, 2, -1, 5, -1, 5, -1, 5, -1, 5, -1, 5, -4, 2, -4, 2, -4, 2, -4, 2, -4, 2, -4, 2, -1, 5, -4, 2, -1, 5, -1, 5, -1, 5, -1, 5, -1, 5, -4, 2, -4, 2, -1, 5, -4, 2, -1, 5, -4, 2, -1, 5, -4, 2, -1, 5, -1, 5, -1, 5, -4, 2, -4, 2, -4, 2, -4, 2, -1, 5, -1, 5, -4, 2, -4, 2, -4, 2, -1, 5, -1, 5, -1, 5, -1, 5, -4, 2, -1, 5, -1, 5, -1, 5, -1, 5, -4, 2, -1, 5, -4, 2, -1, 5, -1, 5, -4, 2, -1, 5, -4, 2, -4, 2, -4, 2, -1, 5, -4, 2, -1, 5, -4, 2, -4, 2, -4, 2, -1, 5, -4, 2, -4, 2, -4, 2, -4, 2, -1, 5, -4, 2, -1, 5, -1, 5, -1, 5, -4, 2, -1, 5, -1, 5, -4, 2, -1, 5, -1, 5, -8]


received_bit_array = ['1'* bit_count if bit_count > 0 else '0' * -bit_count for bit_count in received_bit_counts_on]
received_bit_string = ''.join(received_bit_array)
num_ones = 8 - (len(received_bit_string)%8)
bit_string = '1'* (num_ones if num_ones < 8 else 0)+ received_bit_string
received_hex = hex(int(bit_string, 2))
#received_bits_string = ''.join(received_bits)+'00000000'
#received_bits_string = received_bits_string[0:int(len(received_bits_string)/8)*8]
#print(''.join(received_bits))
print(received_hex)

# --

#rev_x = re.findall('.{1,8}',x[::-1])
#adjusted_x = rev_x[::-1]
#if len(adjusted_x[0]) < 8:
#	adjusted_x[0] = adjusted_x[0].rjust(8, "O")

#print(adjusted_x)
test = ''
n = 0
new = ''
for s in test:
	if n%2==0:
		new += '\\x'
	n += 1
	new += s
#print(new)