# ZeroISS

A tiny automatic ISS receiver for Raspberry Pi Zero🚀

Turn your Raspberry Pi Zero + RTL-SDR into an automatic ISS receiver.

ZeroISS automatically tracks the International Space Station (ISS) using Doppler correction and streams the audio to your phone or PC.

No SDR GUI required.

Designed for people who bought an RTL-SDR dongle,

played with FM radio and ADS-B,

and want to try satellite reception without complicated SDR software.

## Features

- Automatic ISS Doppler tracking
- Headless operation (SSH not required)
- Lightweight (works on Raspberry Pi Zero)
- HTTP audio streaming
- Smartphone friendly
- Fine tuning of gain/PPM should be done with a full SDR application.
- This tool is designed for simple automated tracking and logging.

## Architecture

RTL-SDR  
↓  
Raspberry Pi Zero  
↓  
ZeroISS  
↓  
HTTP stream  
↓  
Phone / PC

## Components

- `ISS_doppler.py`  
  Automatic Doppler tuning during ISS passes

- `stream.sh`  
  Audio pipeline
  rtl_fm → netcat → VLC → HTTP
 
- `config.ini`  
  Basic configuration

## Example stream

http://localhost:8080.zero.mp3

## Requirements

- Raspberry Pi Zero / Zero2W
- RTL-SDR dongle
- rtl_fm
- VLC
- netcat

## Example pipeline

```bash
rtl_fm -f 145800000 -M fm -s 48k -r 48k -E deemp -g 20 - | nc localhost 7355
```

## Status

Early prototype.

Currently supports:

- ISS voice reception (145.800 MHz)
- Automatic Doppler correction
- HTTP audio streaming

## Future ideas

- ISS pass auto calculation
- NOAA satellite support
- IBP beacon monitoring
- Recording support
  
