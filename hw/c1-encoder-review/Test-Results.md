# C1 encoder test results

Run: 2026-10-18T21:27:06.819816-04:00

**42 passed; 0 failed; 5 release gates blocked.**

These are structural schematic checks, not circuit simulation or evidence of working hardware. Fresh netlist and ERC generated from the packaged full C1 project.

| Test | Result | Evidence / limitation |
|---|---|---|
| H01 All 14 original C1 page instances are present | PASS |  |
| H02 Every linked schematic exists inside this package | PASS |  |
| H03 Parent sheet ports match child hierarchical labels | PASS |  |
| H04 Component references are unique across repeated sheets | PASS |  |
| H05 All three motor phases retain their own power components | PASS |  |
| S01 MCU TX/clock connects to R26, with both original MCU pins | PASS |  |
| S02 R26 connects only to U7 data input on the transceiver side | PASS |  |
| S03 MCU RX connects to R27; U7 output is on its other side | PASS |  |
| S04 Encoder RX+ is driven by Y, not Z | PASS |  |
| S05 Encoder RX- is driven by Z, not Y | PASS |  |
| S06 Encoder TX+ reaches A and the optional termination | PASS |  |
| S07 Encoder TX- reaches B and the optional termination | PASS |  |
| S08 TX, RX and differential lines are not shorted together | PASS |  |
| P01 VCC and DE use the C1 3.3 V regulator output | PASS |  |
| P02 Active-low RE, ground and exposed pad are grounded | PASS |  |
| P03 Ribbon pin 1 receives 5 V and pins 2/8 are ground | PASS |  |
| P04 Battery positive connects only to encoder battery input | PASS |  |
| P05 5 V, 3.3 V, battery positive and ground are separate nets | PASS |  |
| P06 No communication signal is shorted directly to a power rail | PASS |  |
| C01 Transceiver has the correct part and exactly pins 1-11 | PASS |  |
| C02 Ribbon has all eight distinct numbered electrical pins | PASS |  |
| C03 Local 100 nF bypass is connected across U7 supply | PASS |  |
| C04 Original 1 uF rail capacitors are retained | PASS |  |
| C05 Both processor series resistors retain 100-ohm values | PASS |  |
| C06 Receive termination is 120 ohms and explicitly unpopulated | PASS |  |
| C07 Old AUX2 connectors and switched I2C pullup are removed | PASS |  |
| R01 Connectivity outside the encoder sheet matches stock C1 | PASS |  |
| R02 Original non-encoder component values and footprints retained | PASS |  |
| R03 All other original child schematic files are byte-identical | PASS |  |
| F01 U7 footprint assignment and manufacturer peripheral land geometry | PASS |  |
| F02 U7 exposed-pad geometry, grounding and segmented paste | PASS |  |
| P01 Power-budget topology: encoder and 3.3 V LDO share 5 V buck | PASS |  |
| E01 Integrated encoder sheet has no ERC violations | PASS |  |
| E02 No unexplained new electrical ERC violations versus original C1 | PASS |  |
| M reverse encoder input pair | PASS | Injected defect detected |
| M reverse encoder output pair | PASS | Injected defect detected |
| M swap chip UART input/output | PASS | Injected defect detected |
| M short battery to 3.3 V | PASS | Injected defect detected |
| M disconnect local capacitor | PASS | Injected defect detected |
| M omit an H-bridge page | PASS | Injected defect detected |
| M populate DNP termination | PASS | Injected defect detected |
| M drop ribbon pin 8 | PASS | Injected defect detected |
| G01 Full-project ERC clearance | BLOCKED | 89 remaining findings; see erc.json |
| G02 Exact footprint and FPC contact-orientation review | BLOCKED | U7 drawing-derived footprint assigned; J2/J3 geometry and cable orientation pending |
| G03 Loaded/startup power and timing margins | BLOCKED | Conditional loaded budget documented; maximum/startup, base-load, thermal and timing evidence pending |
| G04 Complete modified C1 PCB and manufacturing checks | BLOCKED | No integrated PCB layout; connector/CAN-pad changes pending |
| G05 UART, BiSS, battery and motor bench tests | BLOCKED | No assembled board or recorded bench results |

Default exit code tests regressions; use `--strict-release` to return nonzero while any release gate remains blocked.

The baseline is a frozen original C1 comparison, not proof of correctness. Review gates must be rerun/reassessed as the design evolves.
