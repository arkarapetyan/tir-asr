# Audio setup on Ubuntu (C4)

**Project:** tir-asr · **Date:** 2026-10-26 · **Decisions:** D-020, D-041, D-054
C8 copies this guide into the README.

The program captures two sources at the same time (F1):

| Label | Source | Flag | Default (no flag) |
|---|---|---|---|
| `Me` | your microphone | `--mic ID` | the default microphone of the system |
| `System` | the sound that your computer plays (the other side of the call) | `--system ID` | the monitor of the default output |

On Ubuntu (PulseAudio or PipeWire), each output device has a **monitor** source. The monitor gives the sound that plays on the output. You still hear the sound; the monitor only copies it. This is the Ubuntu equivalent of BlackHole on macOS. You need no extra software.

## Before the call

1. Connect **wired headphones** before you start the program.
   - Echo handling is out of scope (`PLAN.md` §1.4). With speakers, the microphone also captures the other side of the call.
   - The program does not follow a change of the output device during a run (D-054). If you change the output, stop the program and start it again.
2. In the call application, select the **laptop microphone** as the input.
   - Bluetooth headphones can change to a headset mode when an application uses their microphone, and the call audio can then lose quality (Q-12, not checked).
3. In the call application, select the **default output** (the wired headphones).

## Select the devices

1. Show the sources and their exact ids:
   ```
   ./run.sh --list-devices
   ```
   Example:
   ```
   Microphones (--mic):
   * alsa_input.pci-0000_80_1f.3.analog-stereo  800 Series ACE (Audio Context Engine) Analog Stereo
   System audio (--system):
   * alsa_output.pci-0000_80_1f.3.analog-stereo.monitor  Monitor of 800 Series ACE (Audio Context Engine) Analog Stereo
   * = the default, used when the flag is not given
   ```
2. If the defaults (`*`) are correct, start the program with no flags:
   ```
   ./run.sh
   ```
3. If a default is not correct, give the exact id from the list:
   ```
   ./run.sh --mic <microphone id> --system <monitor id>
   ```
   - The id must be exact. A part of a name gives the error `audio: no source with the exact id <id>` (D-041).
   - `--mic` and `--system` must not be the same source.

## Check the startup lines

Before "Listening", the program prints one line for each source:
```
startup: source Me: <device name> (<id>)
startup: source System: <device name> (<id>)
```
Make sure that these are the devices that you selected in the call application.

## Errors

| Message | Cause | What to do |
|---|---|---|
| `audio: cannot connect to the PulseAudio server` | No audio server for this user. | Start the program in your desktop session, not over SSH. |
| `audio: no source with the exact id <id>` | The id is not in the list. | Copy the id from `./run.sh --list-devices`. |
| `audio: no monitor source for the default output <id>` | The default output has no monitor with the name `<id>.monitor`. | Give `--system` with an id from the list. |
| `audio: no default microphone`, `audio: no default output` | The system has no default device. | Select a default device in the sound settings, or give the flags. |
