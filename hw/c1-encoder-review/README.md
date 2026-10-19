# Integrated C1 encoder schematic - review draft 0.2

Prepared October 8, 2026. This is an AI-assisted engineering draft for review, not a fabrication release or tested circuit.

Open `moteus_c1.kicad_pro` in KiCad and open its main schematic. **All 14 C1 pages** are available in the left-hand Schematic Hierarchy; the new interface is **aux2 (page 11)**. Do not open the child sheet alone if you want the complete hierarchy. `Complete-C1-Schematic.pdf` contains all 14 pages; `Encoder-Interface-Review.pdf` shows just the modified sheet. There is deliberately no PCB file in this review package: the original physical board has not been modified.

## October 18 footprint and power review

See `Footprint-and-Power-Review.md` for manufacturer checks and the conditional loaded-current calculation. U7 now uses the local `Encoder:TI_DRC0010J` footprint. J2/J3 and cable orientation remain unapproved. Power approval still needs maximum/startup current and board-load measurements.

## Test suite and bench plan

Read `Test-Results.md` for the latest executed checks and `Test-Plan.md` for the page index, test instructions, design reviews and staged bench tests. Run `python3 tests/run_checks.py` from this directory to regenerate the netlist/ERC and rerun all checks. `--strict-release` also returns nonzero while release gates remain blocked. The suite includes eight deliberately injected faults to verify detection. Use `Bench-Test-Record.csv` to record future measurements; every entry starts NOT RUN.

## Implemented

- Replaced the original AUX2 and AUX2H1 connector circuit with an integrated THVD2442 interface, retaining the C1 processor connections through 100-ohm R26/R27.
- U7 D receives AUX2_C through R26. AUX2_C connects to MCU PC4 pin 16 and PA11 pin 33. Firmware must select the intended UART/BiSS function without competing outputs.
- U7 R drives AUX2_D through R27 to MCU PB7 pin 45.
- U7 VCC and DE use the C1 +3V rail (3.3 V). Active-low RE, GND and exposed pad connect to GND. The symbol uses pad 11 for EP; the local DRC0010J footprint matches this convention.
- J2 maps encoder pins 1-8 to 5 V, GND, RX+, RX-, TX+, TX-, battery positive, GND respectively, following Stephen's documented mapping.
- J3 represents the external 2.7-3.6 V battery connection. Battery positive only connects to J2 pin 7; it is not tied to the board's supply. No charger is present.
- R36 is an optional 120-ohm receive termination, explicitly DNP (do not populate). No transmit termination or bias resistors were added.
- Added C50 100 nF local bypass. Retained the original C31/C32 1 uF supply capacitors and 0402 footprint sizes.
- Retired AUX2 A/B/I2C-pullup functions on this dedicated encoder sheet. Removed their old series/filter/pullup components: R22-R25, D11-D12, C33-C36. This removes the switched I2C pullup from AUX2_C. The other child schematic files are unchanged.

Reference mapping: Flux U1 -> U7; Flux J1 -> J2; Flux C3 -> C50; Flux R1 -> R36. References were changed to avoid collisions with existing C1 parts. The original riser-to-C1 header is not needed in this integrated design.

## Decisions still requiring review

1. **Termination:** Notion prose says receive termination DNP and mentions R2-R4; the visible image shows two 120-ohm resistors. This draft follows the prose's DNP receive termination and omits an additional transmitter load. Confirm the encoder's internal termination and inspect the actual cable waveform before selecting population. Short cable length alone does not prove termination is unnecessary.
2. **Battery attachment:** The image shows J3, while prose says solder pads; the parent C1 requirement requests a connector. The electrical two-pin symbol is complete, but its footprint/part is intentionally unset until connector versus pads is resolved.
3. **Footprints:** U7 uses the drawing-derived local DRC0010J footprint; J2 remains unset pending its exact manufacturer land-pattern verification. J2's symbol currently represents its eight electrical contacts only; map any mechanical mounting pads during footprint selection. Verify cable contact side, numbering at both ends and orientation before layout. J3 also needs a footprint decision.
4. **Power:** 4.1 mA is the cited no-load transceiver current, not its loaded maximum. Verify differential-load and switching current, the actual encoder's maximum/startup current, and other consumers of the C1 rails. Do not treat the Notion table's approximate 60 mA encoder value as a guaranteed worst-case limit. No loaded power-budget approval is implied.
5. **Logic/firmware:** R26/R27's original 100-ohm values are retained as a review choice. Check edge timing and the selected UART/BiSS configuration. Always-enabled DE/RE requires compatible firmware configuration. This package changes no firmware.

## Remaining C1 board work

The updated Motor Driver page also calls for AUX1/AUX2 through-hole removal, removal of stock connectors, CAN solder pads, and placement in the freed area. This package completes the encoder schematic integration only. AUX1, CAN, programming, power and other connector definitions outside AUX2 are still stock. Review their replacement connections and access requirements before deleting them or updating the PCB. Preserve programming/debug access and required power/motor connections.

Next physical step: validate footprints, copy the original PCB into a separate layout work area, then synchronize the reviewed schematic and place the new parts. Do not interpret the old riser's 9 x 12 mm outline or its reported clean DRC as validation of the integrated C1 board.

## Verification

`Verification.txt` records the netlist checks and baseline comparison. All intended signal/power/battery connection groups pass, and electrical connectivity among components outside the modified sheet is unchanged. Other child schematic files are byte-identical to the source.

The new aux2 sheet has zero reported ERC violations. The complete project has **24 errors and 65 warnings** elsewhere. Most originate in the source design/checking environment; the new receiver-enable connection changes one warning involving the original MCU's unspecified ground-pad pin. `Test-Plan.md` documents that exact reviewed delta. The project is **not ERC-clean overall**. The frozen baseline ERC is in tests/baseline; running the suite produces the current report in tests/results. No KiCad exclusions or dummy power flags were added to conceal violations. A schematic ERC pass cannot verify footprint correctness or physical signal integrity.

The original source under `Documents/Archibald 434/moteus-main/hw/c1` has not been edited. The project copy preserves the original supporting custom library and license context. The KiCad file dates/format may be updated by KiCad when opened and saved.

## Sources

- [Updated Motor Driver requirements](https://app.notion.com/p/3779c86ceacf80ac8c18fb09ad21ecc8), reviewed October 8, 2026.
- [Flux Riser Board Design](https://app.notion.com/p/d4e67be331dc4436acdb363d34727610), Stephen Bell October 3 update; schematic image and accompanying prose reviewed.
- [TI THVD2442 datasheet](https://www.ti.com/lit/ds/symlink/thvd2442.pdf), pin functions and supply/enable conventions.
- [MOSRAC S-series data](https://www.mosrac.com/uploads/pic/product/s_series/mosrac-s-series-magnetic-encoder-data-sheet.pdf); confirm the exact installed encoder variant.
- [Official C1 hardware source](https://github.com/mjbots/moteus/tree/main/hw/c1), local downloaded revision 1.2.
