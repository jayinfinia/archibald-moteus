#!/usr/bin/env python3
"""Conditional resistive-load screening, NOT guaranteed total supply current."""
import json
rows=[]
for r in (120,100,54):
    nominal=4.1+3300/r
    rows.append(dict(assumed_ohms=r,u7_nominal_ma=round(nominal,2),
        margin_to_50ma=round(50-nominal,2),
        u7_3v6_resistor_minus_1pct_ma=round(4.1+3600/(r*.99),2),
        buck_increment_with_approx_60ma_encoder=round(60+nominal,2)))
print(json.dumps(rows,indent=2))
print('Provisional 50 mA interface allocation + approximate 60 mA encoder:')
print('5 V increment = 110 mA; 5 V output power = 0.55 W; extra LDO heat = 0.085 W.')
print('Missing: encoder maximum/startup current, actual termination, switching current, base loads and thermal evidence.')
