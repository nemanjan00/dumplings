# NRF52840 APPROTECT Voltage Glitching Attack

Voltage glitching attack to bypass the APPROTECT (AP lock) on the Nordic NRF52840 SoC using a ChipWhisperer Husky.

The NRF52840's APPROTECT mechanism disables SWD debug access to protect firmware from being read out. By injecting a precisely timed voltage glitch during boot, the APPROTECT check can be corrupted, temporarily granting full debug access and allowing firmware extraction.

## Target

- **SoC**: Nordic NRF52840 (ARM Cortex-M4F, 64MHz, 1MB flash, 256KB RAM)
- **Protection**: APPROTECT — controlled by UICR register at `0x10001208`. When enabled, all SWD/JTAG debug access is blocked.
- **Attack surface**: The APPROTECT check occurs ~1.66ms after power-up during the boot sequence
- **Rail under attack**: DEC1 (1.0V internal core regulator decoupling pin). The crowbar MOSFET briefly shorts DEC1 to GND, causing a voltage dip on the core supply that corrupts the APPROTECT check in the CPU.

## Hardware Required

- **ChipWhisperer Husky** — glitch generation (crowbar MOSFET) and trigger
- **Segger J-Link V9** — SWD debug probe for reading flash via OpenOCD
- **NRF52840 target board** — device under test with APPROTECT enabled

## Wiring

```
                    ChipWhisperer Husky
                   ┌────────────────────┐
                   │                    │
  NRF52840 VCC ◄───┤ Pin 20 (+3.3V)    │
       │           │                    │
       ├───────────┤ Pin 16 (TIO4)      │   Trigger: rising edge on power-up
       │           │                    │
       ├───────────┤ Glitch SMA         │   Crowbar: shorts DEC1 to GND
       │           │                    │
  NRF52840 DEC1 ───┤                    │   (remove decoupling cap on DEC1)
       │           │                    │
  NRF52840 GND ◄───┤ GND               │
                   └────────────────────┘

                   ┌────────────────────┐
                   │    J-Link V9       │
                   │                    │
  NRF52840 SWDIO ◄─┤ SWDIO             │
  NRF52840 SWDCLK◄─┤ SWDCLK            │
  NRF52840 GND ◄───┤ GND               │
                   └────────────────────┘
```

### Husky 20-pin connector

| Husky Pin | Function | Connect to |
|-----------|----------|------------|
| Pin 20 (+3.3V) | Target power supply (200mA) | NRF52840 VCC |
| Pin 16 (TIO4) | Trigger input | NRF52840 VCC (same net as pin 20) |
| GND | Ground | NRF52840 GND |

### Husky SMA

| Connector | Connect to |
|-----------|------------|
| Glitch SMA output | NRF52840 DEC1 pin (1.0V core regulator decoupling) |

The Husky's built-in 3.3V supply (pin 20) powers the target and serves as the trigger source. TIO4 detects the rising edge when power is turned on, which triggers the glitch after the configured delay.

## Board Preparation

The decoupling capacitor on the DEC1 pin must be removed. This cap filters voltage transients — with it in place, the glitch pulse is absorbed and has no effect on the core supply.

## How It Works

1. **Power off** the target via `scope.io.target_pwr`
2. **Arm** the glitcher with random delay/length parameters
3. **Power on** the target — rising edge on TIO4 triggers the glitch
4. After the configured delay, the Husky's high-power crowbar MOSFET briefly shorts DEC1 to GND via the SMA output, causing a voltage dip on the core supply
5. If the glitch hits during the APPROTECT check (~1.66ms after boot), the check may be corrupted and debug access remains open
6. **OpenOCD** attempts to dump the full 1MB flash over SWD via J-Link
7. Response is classified and stored in a SQLite database
8. Repeat until APPROTECT is bypassed (color `R`)

## Dependencies

- [findus](https://github.com/faultyHardware/fault-injection-library) — fault injection framework
- [chipwhisperer](https://github.com/newaetech/chipwhisperer) — Husky interface
- [OpenOCD](https://openocd.org/) — SWD debug access
- Segger J-Link drivers

## Usage

```bash
python attack.py --delay 2200 2300 --length 500 800
```

### Arguments

| Argument | Description |
|----------|-------------|
| `--delay START END` | Glitch delay range in nanoseconds after trigger |
| `--length START END` | Glitch pulse length range in nanoseconds |
| `--resume` | Resume from previous database |
| `--no-store` | Do not store results in database |

### Recommended Parameters

The APPROTECT check occurs ~1.66ms after power-up. Confirmed successful parameters:

- **Delay**: 1,659,931 ns (~1.66ms)
- **Length**: 634 ns

Recommended search range:

```bash
python attack.py --delay 1600000 1700000 --length 500 800
```

### Output Colors

| Color | Meaning |
|-------|---------|
| Green (G) | AP lock active — expected, keep searching |
| Blue (B) | Hardware error (J-Link not found, connection error) |
| Magenta (M) | Unusual response — worth investigating |
| Yellow (Y) | Timeout — trigger did not fire |
| Red (R) | **Success** — APPROTECT bypassed, flash dumped |

## When the Glitch Succeeds

On a successful glitch (color `R`):

1. The attack loop breaks automatically
2. The full 1MB flash is dumped to `nrf52_dumped.bin` in the working directory
3. The APPROTECT bypass is **temporary** — it only lasts until the next power cycle. If you need to read again, re-run the attack.

## Locking the Device (for testing)

To enable APPROTECT on an unlocked NRF52840:

```bash
nrfjprog --rbp ALL
```

Or via OpenOCD:

```bash
openocd -f interface/jlink.cfg -c "transport select swd" -f target/nrf52.cfg \
  -c "init; halt; flash fillw 0x10001208 0xFFFFFF00 1; reset; exit"
```

Power cycle the target after locking. Verify with:

```bash
openocd -f interface/jlink.cfg -c "transport select swd" -f target/nrf52.cfg \
  -c "init; exit"
```

You should see `AP lock engaged` and `Debug access is denied` in the output.

## Files

| File | Description |
|------|-------------|
| `attack.py` | Main attack script |
| `databases/` | SQLite databases with experiment results |
| `execution.log` | Execution log |
| `nrf52_dumped.bin` | Dumped flash (1MB, created on success) |
