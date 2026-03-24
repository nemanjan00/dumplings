# Dumplings

My ChipWhisperer Husky likes to eat dumplings — so here are some.

Voltage glitching attack scripts for bypassing debug protection on microcontrollers, using a [ChipWhisperer Husky](https://www.newae.com/chipwhisperer) as the glitch platform.

## Targets

| Target | Protection | Status |
|--------|-----------|--------|
| [NRF52840](nrf52840/) | APPROTECT (SWD/JTAG lock) | Working |

## Quick Start

### Prerequisites

- ChipWhisperer Husky (connected via USB)
- Python 3

### Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Then pick a target and follow its README for hardware setup and usage.

## Credits

- [findus](https://fault-injection-library.readthedocs.io/en/latest/overview/) — fault injection library used for glitcher control and experiment management
