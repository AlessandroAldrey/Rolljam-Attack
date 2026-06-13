# Rolljam & Replay Attack Exploration Framework
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Hardware: YARD Stick One](https://img.shields.io/badge/Hardware-YARD%20Stick%20One-orange.svg)](https://greatscottgadgets.com/yardstickone/)

---
This repository contains the implementation, research data, and proof-of-concept scripts developed for my Senior Thesis. The project focuses on researching, documenting, and executing RF security audits, specifically Replay Attacks and Rolljam Attacks, against Sub-GHz Remote Keyless Entry (RKE) systems.
## Overview & Research Context
Modern vehicles and garage systems use Rolling Codes to prevent simple replay attacks. Every time a button is pressed, the key fob generates a unique cryptographic token. If a token is used once, the receiver burns it, rendering it useless for future replays.

The Rolljam Attack overcomes this defense by deploying a reactive jamming technique:
1. First Press: The attacker jams the frequency while simultaneously sniffing the RF signal. The receiver never gets the code, so the vehicle stays locked, but the attacker intercepts `Code A`.
2. Second Press: The user presses the button again. The attacker jams again and sniffs `Code B`. Instantly after capturing `Code B`, the attacker transmits the pristine `Code A`. The vehicle unlocks, the user thinks it was a glitch, but the attacker now holds an unused, valid token (`Code B`) to unlock the vehicle at any time.
---
## Hardware Architecture
To replicate this environment safely inside a controlled lab sandbox, the architecture uses a distributed dual-RF interface setup:
* 2x YARD Stick One: Transceivers operating in the Sub-1 GHz frequency bands.
  * Interface 1 (Jammer): Responsible for reactive jamming upon preamble detection.
  * Interface 2 (Sniffer/Player): Responsible for IQ signal capturing, demodulation, and transmission.
* 1x Raspberry Pi 4B: Acts as the localized field deployment unit, hosting the reactive jamming logic close to the target device.
* Analyzed Target Key Fobs:
  * Aprimatic TX2M (Garage Door System)
  * Volkswagen Passat (Year 2002)
  * Mercedes A-Class (Year 2006)
  * Audi Q2 (Year 2021) — *Note: Investigated exclusively for reactive jamming capabilities due to advanced modern rolling code constraints.*
---
## Repository Structure
The project assets are organized systematically to support both implementation and academic audit trails:
```text
├── Python/          # Core proof-of-concept attack scripts mapped per device
├── Samples/JSON/    # Demodulated RF signal payloads captured in JSON format
├── WAV_Files/       # Raw baseband audio/IQ recordings of transmission bursts
├── Videos/          # Live action demonstrations of successful attack vectors
└── notes/           # Research annotations, frequency analysis, and registers
```
## Software Prerequisites & Setup
### Dependencies
Ensure the following libraries are present in your environment:
* `rflib` (RfCat runtime engine)
* `bitstring`
* `binascii`
### Module Modes of Operation
Each device-specific script (excluding the baseline garage utility) implements an argument-driven state machine to execute different phases of the RF audit:

| Mode | Function | Operational Description |
| :--- | :--- | :--- |
| `rx` | Capture & Decode | Sets the YARD Stick One to continuous listening mode. Upon valid preamble detection, it demodulates the payload and saves it into a structured JSON file. |
| `tx` | Targeted Playback | Transmits a hardcoded, unused rolling code payload directly from the local JSON database to trigger state changes in the receiver. |
| `echo` | Live Replay | Instantly sniffs a signal burst and replays it back into the medium without modification. |
| `echo_with_delay` | Delayed Replay | Captures the payload and queues transmission for a 5-second interval delay to test receiver timeout windows. |
| `jam` | Reactive Jamming | Monitors the RSSI/preamble thresholds. The moment a transmission starts, it activates high-power white-noise jamming to block the receiver while letting the sniffer log the payload. |
| `jam_with_delay`| Scheduled Jamming | Executes the reactive jamming loop with an automated 10-second operational cooldown window. |

## Academic Publication & Citation
This scripts represents the practical implementation of my Senior Thesis at the University of A Coruña (UDC).

The complete theoretical background, security analysis, and full dissertation are officially published and peer-reviewed in the UDC Academic Repository:
- Read [Full Senior Thesis](https://ruc.udc.es/entities/publication/439035f5-e5e3-4e8f-8388-337df8bbb0de)