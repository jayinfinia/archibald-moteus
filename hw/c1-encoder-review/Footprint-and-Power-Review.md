# Footprint and power review — 18 October 2026

**Result:** U7 now has a project-local footprint derived from its manufacturer drawing. J2 geometry and cable orientation remain unverified. The power calculation is a conditional planning budget, not a worst-case approval. No PCB or hardware has been validated.

## U7: THVD2442DRCR

Assigned `Encoder:TI_DRC0010J` on aux2/page 11. Source: [TI datasheet](https://www.ti.com/lit/ds/symlink/thvd2442.pdf), package drawing 4218878/B, DRC0010J, PDF pages 29–31. Dimensions in mm:

| Feature | Implemented |
|---|---|
| Body | 3 × 3 nominal |
| Pins 1–10 | 0.50 pitch; 0.60 × 0.24 lands; row centers x = ±1.40 |
| Numbering, top view | 1 at upper left; 5 lower left; 6 lower right; 10 upper right |
| Exposed pad 11 | 1.65 × 2.40; four 0.25 × 0.50 extensions at x = ±0.25, y = ±1.45 |
| Paste apertures | Two 1.50 × 1.06 at y = ±0.63; four 0.25 × 0.34 at x = ±0.25, y = ±1.53 |
| Mask | +0.07 per side |
| Thermal vias | Optional; omitted in this footprint |

Pad 11 maps to the schematic's grounded EP. Drawing dimensions and symbol pin functions were checked. The installed generic KiCad 1.65 × 2.4 footprint has larger peripheral lands and different paste geometry; the 1.2 × 2.0 variant has the wrong exposed-pad size. Neither was silently substituted. Courtyard (3.9 × 3.9), reference text and pin-one marking are our additions. Assembly vendor must approve stencil thickness, paste and thermal implementation; board-level clearance/placement remains pending.

## J2: Molex 0512810898 / 512810898

The [Molex series catalog](https://www.molex.com/en-us/products/series-chart/51281) confirms eight circuits, 0.50 mm pitch, right-angle SMT, dual contact, non-ZIF, 1.20 mm mated height. Dual contact does not establish end-to-end cable numbering.

**Footprint remains blank deliberately.** No exact 51281 footprint was found in the installed KiCad library. The [manufacturer sales drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/512/51281/512810898_sd.pdf) failed to download through both web access and direct requests; older drawing endpoints also failed. This does not prove the drawing is unavailable to Stephen or through a browser/distributor.

Do not approve a generic eight-pin 0.5 mm footprint. Needed: terminal length/width and origin, retention-pad geometry, body outline, insertion direction, cable thickness/exposed-contact length, and numbered top view. Then check cable continuity end-to-end against this schematic:

| J2 pin | Connection |
|---|---|
| 1 | +5 V encoder supply |
| 2 | Ground |
| 3 / 4 | Encoder RX+ / RX− (controller U7 Y / Z) |
| 5 / 6 | Encoder TX+ / TX− (controller U7 A / B) |
| 7 | Separate backup battery positive |
| 8 | Ground / backup battery return |

The [Mosrac family datasheet](https://www.mosrac.com/uploads/pic/product/s_series/mosrac-s-series-magnetic-encoder-data-sheet.pdf) lists an FH34SRJ-8S-0.5SH connector option. Confirm the actual encoder variant and supplied cable: matching pitch alone is insufficient. J3 battery connection/footprint is a separate unresolved decision.

## Power calculation

[Moteus documentation](https://mjbots.github.io/moteus/reference/encoders/) specifies C1 auxiliary allowances of 50 mA at 3.3 V and 100 mA at 5 V. These are not the regulators' full capacities or proof of simultaneous headroom with every other accessory.

The schematic has a [MAX15062](https://www.analog.com/en/products/MAX15062.html) 5 V buck and [TLV70233](https://www.ti.com/product/TLV702) 3.3 V LDO, each rated up to 300 mA subject to operating/thermal conditions. Netlist checks confirm the LDO is fed by +5 V. Therefore the transceiver current also loads the 5 V buck approximately one-for-one; it must not be converted using a lossless 3.3/5 ratio.

Mosrac states approximately 60 mA main current and 15 ms startup time, but provides no guaranteed maximum or startup-current waveform here. Backup current is approximately 35 µA under its stated 3.6 V/6000 rpm low-power condition; it is on the separate battery path. It is not added to the main supply or used as a guaranteed battery-life figure.

TI's 4.1 mA maximum applies to **no-load** operation at 3–3.6 V with both sections enabled. The encoder contains receive termination, so U7 drives a load even when the logic remains idle. Its value is not established by the available family data. R36 is on the opposite direction and remains DNP; fitting it would load the encoder transmitter and may increase encoder current.

For screening only, use `I_U7 ≈ 4.1 mA + VCC/Rload`. This intentionally uses the supply voltage rather than the smaller differential output voltage. It bounds the simple resistive contribution, **not total guaranteed device current**: switching, cable capacitance, receiver output load, temperature and abnormal bus conditions need separate evidence.

| Assumed encoder termination | U7 estimate at 3.3 V | Margin to 50 mA | U7 at 3.6 V and R −1% | 5 V increment: 60 mA encoder + nominal U7 |
|---|---:|---:|---:|---:|
| 120 Ω | 31.60 mA | 18.40 mA | 34.40 mA | 91.60 mA |
| 100 Ω | 37.10 mA | 12.90 mA | 40.46 mA | 97.10 mA |
| 54 Ω stress case | 65.21 mA | −15.21 mA | 71.44 mA | 125.21 mA |

These are scenarios, not measured encoder termination values. TI's typical loaded curve at 54 Ω is about 43 mA at 3.3 V; it illustrates why no-load current is insufficient, but does not guarantee passing the 50 mA allowance. The simple estimator is deliberately higher than that typical curve.

For a provisional allocation, reserve the full 50 mA 3.3 V allowance for the interface. With the approximate 60 mA encoder load, this adds **110 mA / 0.55 W at the 5 V buck output**, including about **85 mW additional LDO heat** at 5 V → 3.3 V. It leaves at most 190 mA of the buck's nominal 300 mA rating for all original board loads and other accessories, before startup/thermal margin. The 3.3 V regulator would have at most 250 mA left independently. Neither remainder is measured spare capacity. At the encoder's full 100 mA auxiliary allocation, the combined allocation is 150 mA, leaving at most 150 mA on the buck. Do not compare the combined 110 mA against the 100 mA external 5 V allowance: the latter applies to external 5 V loading, while this combined figure checks the upstream regulator.

Power gate stays blocked until:

1. Confirm the exact encoder's termination, maximum running and peak startup current, including the intended receive termination configuration.
2. Measure or bound stock C1 consumption on both rails with firmware, CAN, gate driver and other accessories active; include regulator tolerance and thermal conditions.
3. Measure loaded UART/BiSS interface current and rail droop during startup and traffic with the intended cable. Check the encoder sees 4.5–5.5 V throughout operation and evaluate startup sequencing.
4. Verify the populated PCB's regulator temperatures and signaling timing. No circuit simulation, hardware test or manufacturing approval is implied by this calculation.

The reproducible arithmetic is in `tests/power_budget.py`. G02 remains blocked for J2/J3/cable mechanics; G03 remains blocked for maximum/startup/load/thermal/timing evidence.
