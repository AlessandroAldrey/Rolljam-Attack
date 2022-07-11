import scipy.io.wavfile as wav

rate,sample = wav.read("fragment_garage.wav")

sample[sample>=0] = max(sample)
sample[sample<0] = min(sample)

wav.write("converted_garage.wav", rate, sample)
