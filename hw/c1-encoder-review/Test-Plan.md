# Does the integrated C1 encoder interface work?

## Current answer

The schematic passes the structural checks listed in `Test-Results.md`. **Hardware operation has not been demonstrated.** There is no integrated PCB layout or assembled prototype yet. The automated checks verify wiring intent and preservation of the C1; they are not an electrical simulation, firmware test, or manufacturing approval.

The complete KiCad project has **14 pages**, including the original motor-control circuitry. Open `moteus_c1.kicad_pro`, launch its schematic, and use the left-hand Schematic Hierarchy. Opening `aux2.kicad_sch` alone does not load the whole hierarchy.

| Page | C1 sheet | Purpose |
|---|---|---|
| 1 | Root | Connects the system's schematic sheets |
| 2 | Power Input | Input supply and regulated rails |
| 3 | stm32g4 | Processor, programming and processor supplies |
| 4 | Gate Driver | Controls the power-switching transistors |
| 5-7 | H Bridge A, B, C | Three motor phase power stages |
| 8 | Current Sense | Measures motor phase current |
| 9 | CAN | Communications with the host |
| 10 | VT Sense | Supply-voltage and temperature sensing |
| 11 | aux2 | New integrated encoder interface |
| 12 | aux1 | Original onboard encoder/auxiliary circuitry |
| 13 | LED Sense | Indicators and associated circuitry |
| 14 | Bulk Capacitance | Motor-bus capacitors |

H Bridge A/B/C are three separate sheet instances sharing one source file; this is intentional. The full PDF has all 14 pages. This package covers the schematic; it does not yet contain a modified PCB layout tab.

## Run the software checks

With Python 3 and KiCad installed, from this project directory run:

```sh
python3 tests/run_checks.py
```

The script exports a fresh netlist and runs ERC on the full project before testing. It saves `Test-Results.md`, structured results, the netlist, ERC and a command log under `tests/results/`. It requires no additional Python packages. Use `--kicad-cli /path/to/kicad-cli` if KiCad is not found automatically.

```sh
python3 tests/run_checks.py --strict-release
```

Default exit code 0 means the regression checks pass. Strict-release mode also refuses release while evidence gates are blocked (exit 2). An actual failed automated check returns exit 1. Release gates are deliberately recorded as unresolved engineering reviews; they do not automatically become approved merely because a field or file exists.

### What the automated checks cover

- Every C1 page, local file link and hierarchical port, including each distinct H-bridge instance.
- Correct UART/clock and return paths through the processor series resistors.
- Each differential pair's polarity and every ribbon electrical pin.
- Ground, 3.3 V, 5 V, separate battery positive and absence of direct rail/signal shorts.
- Correct transceiver, bypass capacitor, retained rail capacitors, resistor values and DNP termination state.
- Unchanged connections and component values outside the modified sheet.
- Fresh ERC, with an exact comparison to the original design.
- Eight deliberately corrupted in-memory circuits, proving the relevant checks reject common mistakes. The real design files are never corrupted by these tests.

### One reviewed ERC delta

KiCad now reports a warning between **U3 pin 49**, whose original C1 symbol calls its exposed pad an *unspecified* pin, and **U7 pin 2**, an input tied low to enable reception. Both share the original regulator ground net. The suite recognizes only that exact pair after checking its ground connection. It does not suppress the warning in KiCad or ignore other pin-to-pin warnings. Resolve the symbol typing during full-project ERC review. Other pre-existing errors still prevent an overall clean ERC result.

## Before ordering a PCB: design acceptance tests

All entries below are **NOT RUN / BLOCKED** unless evidence is later recorded. A design owner should approve the proposed project-specific acceptance criteria before hardware testing. Do not replace missing maximum specifications with typical values.

| ID | Test and method | Acceptance / evidence |
|---|---|---|
| D01 | Independently compare U7 symbol against TI pin table, then compare every footprint pad, including EP, against the package drawing. | Pins 1-10 match; EP-to-GND mapping is explicit and matches pad 11 convention. Save annotated symbol/footprint review. |
| D02 | Compare the Molex drawing, encoder drawing and actual ribbon orientation end to end. Include mechanical hold-down pads. | Each physical contact maps to the intended electrical pin; no mirror/reversal ambiguity. Save marked drawings and cable photos. |
| D03 | Resolve battery connector versus solder pads and trace each polarity. | Signed-off attachment type, battery range and cable polarity. Battery positive has no board-rail tie or charging path in the design. |
| D04 | Determine actual encoder input termination; calculate loaded transceiver current and startup/continuous encoder load. Include other loads on each supply. | Within regulator, trace and connector ratings over the intended operating range, with an explicitly agreed margin. No-load transceiver current alone is insufficient. Save calculations and supporting specifications. |
| D05 | Check logic thresholds and timing for both protocols, including R26/R27, receiver propagation, cable delay and MCU pin configuration. | Positive worst-case voltage/timing margins, with no simultaneous drive by PC4 and PA11. Exact encoder variant and firmware commit recorded. |
| D06 | Complete the physical C1 layout and connector changes; review routing, decoupling, ground return, current loops and mechanical fit. | No unreviewed DRC violations/unrouted nets; connector access and board clearances verified. Check new components do not disturb motor-current paths. |
| D07 | Resolve or explicitly justify every full-project ERC finding without masking missing connections. | Electrical reviewer approval, final netlist and ERC archived. Current automated pass does not satisfy this gate. |

## Bench sequence after the prototype exists

Equipment: current-limited supply suitable for the C1 input, multimeter, oscilloscope with suitable differential probing, logic capture equipment, host/CAN interface, the exact encoder and cables, and a controlled battery source. Record instrument identity, board revision, firmware commit, configuration, cable length and ambient conditions. Never clip a grounded oscilloscope lead onto a differential signal or motor switching node.

Use the main C1 input to power the board. Do not back-feed its regulated rails without an independently reviewed setup. Leave the motor phases disconnected for B01-B08. Power down before cable changes; intentional high-voltage bus faults and destructive short-circuit testing are outside this plan.

| ID | Procedure | Pass condition | Evidence to save |
|---|---|---|---|
| B01 | Unpowered inspection and continuity: trace all eight ribbon contacts to U7, supply, ground and battery points; inspect EP soldering. | Correct end-to-end mapping; no solder bridges or sustained unexplained low resistance between power rails. Account for capacitor charging and semiconductor paths; a continuity beep alone is not a short diagnosis. | Photos and measured pin map. |
| B02 | Power the C1 with encoder and battery disconnected, using a current limit selected from the reviewed baseline budget. | Stable expected rails, no unexpected heating, no sustained current limiting; U7 VCC near 3.3 V and within TI's recommended range; DE high and RE low. | Startup traces, rail voltages, input current and temperatures. |
| B03 | Connect the encoder with the motor still disconnected; capture startup and continuous operation on both rails. | Encoder supply stays in its specified range at the encoder connector; C1 regulator and encoder/transceiver current budgets are met with approved margin. No MCU reset or loss of CAN. | Scope captures and current measurements including peak startup. |
| B04 | Enable the intended C1 transmit function. Capture MCU-side TX, U7 D, Y/Z, A/B and R as appropriate. | Correct polarity, levels and decoded traffic; no competing MCU outputs. Rise/fall time, overshoot and settling meet the approved receiver/timing limits. | Annotated request/response captures. |
| B05 | Run UART with the exact supported MOSRAC variant and approved Archibald firmware/configuration. Proposed endurance: at least 1 million frames AND 10 minutes at the intended update rate. | Proposed project criterion: zero new checksum/framing/timeout errors, no resets, fresh position timestamps throughout. Record counters before/after, including any rollover. | Raw frames or timestamped telemetry, configuration and error counters. |
| B06 | Rotate the shaft manually through known forward/reverse turns and across single-turn wrap. | Correct direction after configured sign mapping; no unexplained discontinuities; angle/turn counts agree with the known motion within the chosen reference measurement's accuracy. | Position log and independent turn record. |
| B07 | Repeat signal capture and endurance using a BiSS-capable encoder/approved mode and firmware. Start at a validated clock rate, then the target rate. | Correct word length, CRC, status polarity, fresh data and timing; zero unexpected error/timeout increments under the same proposed endurance criterion. A UART-only encoder is not a valid BiSS test device. | Clock/data captures and raw decoded words. |
| B08 | Compare minimum and maximum intended cable length (reference design limit: 100 mm). Start with R36 DNP; power down before changing termination if waveform review justifies it. | Approved signal/timing margins and error criteria at each tested configuration; supply budget still passes if a resistor is fitted. Do not install an extra transmitter termination without checking encoder termination. | Cable/termination matrix, scope captures and frame counts. |
| B09 | For the BM variant, with motor phases disconnected, provide backup power, record position, remove main power, rotate a known number of turns, restore main power. Repeat forward/reverse and at reviewed backup supply endpoints. | Exact signed multi-turn change recovered; backup voltage/current within the actual variant specification. Main rails are not unintentionally energized through backup or signal paths. | Battery voltage/current and before/after turn counts. |
| B10 | Exercise encoder absence/reconnection and controlled power sequencing. Disconnect only with the system powered down unless a hot-plug procedure has been approved. | Missing/stale data is recognized, not accepted indefinitely as fresh. Recovery and any required reinitialization match the approved firmware behavior. | Fault/status timeline and recovery log. |
| B11 | Check CAN, programming/debug access, onboard encoder, voltage/current/temperature sensing and all three motor-phase connections against the stock baseline. | No unexplained functional regression; required access retained after connector removal. | Regression checklist and sensor/communications logs. |
| B12 | After B01-B11 pass, use a secured motor and approved low-current, low-speed bring-up settings; progress to agreed load/speed while logging encoder errors and temperatures. | Stable controlled motion, no unintended motion, no new encoder errors/CAN resets, and electrical/thermal limits respected. Stop on stale feedback, unexpected motion, current limiting or overheating. | Speed/load/current matrix, feedback logs and temperatures. |

The endurance counts above are proposed development criteria, not manufacturer reliability guarantees. Further temperature, EMC, vibration and production qualification may be required by the eventual product requirements.

## What to log

Use `Bench-Test-Record.csv` as the run index. For each run, attach raw telemetry and scope captures rather than only writing PASS. Useful telemetry fields are timestamp, valid-frame count, checksum/CRC errors, framing errors, timeouts, reset count, encoder status, single/multi-turn position, and selected protocol/configuration. If firmware cannot expose a required counter, record that limitation and obtain equivalent capture evidence; do not enter zero for unavailable data.

## Source limits and references

- [Stephen's Flux reference](https://app.notion.com/p/d4e67be331dc4436acdb363d34727610) and [modified C1 requirements](https://app.notion.com/p/3779c86ceacf80ac8c18fb09ad21ecc8) define the intended interface. The text/image inconsistencies remain review items.
- [TI THVD2442 data](https://www.ti.com/lit/ds/symlink/thvd2442.pdf): pin functions, recommended supply/logic limits, driver loading and timing. Test against the applicable operating conditions, not absolute-maximum limits.
- [MOSRAC S-series data](https://www.mosrac.com/uploads/pic/product/s_series/mosrac-s-series-magnetic-encoder-data-sheet.pdf): the family specifies 4.5-5.5 V main power and 2.7-3.6 V backup for BM variants. Its approximately 60 mA operating current is not a guaranteed startup maximum. Confirm the selected model before applying these limits.
- [moteus encoder reference](https://mjbots.github.io/moteus/reference/encoders/): C1 auxiliary allowances are 50 mA at 3.3 V and 100 mA at 5 V. Those are accessory budgets, not limits for total C1 input current. Port/source/output configuration and firmware compatibility must be tested separately.
