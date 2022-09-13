# Senior thesis
In this repository you will find the necessary information to be able to carry out both, the replay attack and the rolljam attack against different devices.

Requirements:
• ** Two YARD Stick One **. One of them will be used for jamming and the other one for capturing and sending the replica of the signal.
• ** A Raspberry Pi 4B**. The Raspberry will use one of the YARD Stick One, it will be in charge of being close to the vehicle that we want to test, and do the jamming when the desired signal is detected.
• **Different key fobs**. The implemented scripts are useful against an Aprimatic TX2M, a Volkswagen Passat (year 2002), a Mercedes A Class (year 2006) and an Audi Q2 (year 2021, you can only do the jamming against it).
  ** Python 3.9.13 **. The following libraries are needed: JSON, Binascii, Exists, Bitstring, Time, Rflib.
 
Each script, except the garage's one, has different modes:
• ** rx **. This mode sets the YARD Stick One in capture mode, when it detects a signal from a remote control, if it has captured it correctly, it saves it in a JSON file.
• ** tx **. This mode transmits a hard-coded message. This message must be replaced with one that has not been used in one of the JSON files.
• ** echo **. In this mode the signal is captured and subsequently sent.
• ** echo_with_delay **. This modality is similar to the previous one but with a delay of 5 seconds between the reception and the sending of the signal.
• ** jam **. In this mode the YARD Stick One listens for a preamble of a signal, when it detects it, it starts to jam (jamming power must be configured as needed).
• ** jam_with_delay **. This modality is similar to the previous one but with a 10-second delay once the jamming has been done.

The content of it is structured as follows:
• **Python folder**. It contains the scripts for each analyzed device.
• **Samples/JSON folder**. This folder contains the captured signal messages in JSON format for each remote access key.
• **Videos folder**. It contains different demonstrations for the different attacks.
• **WAV_Files folder**. Audio recordings of each analyzed device are located in this folder.
