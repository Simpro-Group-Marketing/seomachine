# California OEWS May 2025 trade wage table: best-trade-jobs-california

- Run ID: 0f23f31d-46c1-4b8c-936e-2b2edb8dbbf5
- Retrieved: 2026-09-24T16:02:16Z
- Release: May 2025 | Area: California (0600000)
- Ranking measure: California annual median wage (OEWS datatype 13); 'top 10% earn' uses the annual 90th percentile (datatype 15).
- Machine artifact: `research/ca-oews-trade-wages-best-trade-jobs-california-2026-09-24.json`
- Raw snapshots: `research/source-snapshots/ca-oews-best-trade-jobs-california-2026-09-24/`

## Method

Full California cross-industry OEWS table from POST https://data.bls.gov/OESServices/prefilter/table (areaCode 0600000, industryCode 000000, year 2025); datatype codes verified against /OESServices/prefilter/datatype; release label from /OESServices/prefilter/year. Scope rule applied to every SOC in groups 47, 49, and 51-80; detailed = SOC code not ending in 0; suppressed = non-numeric value (footnote 8 'Estimate not released'). Occupations absent from the published California table are treated as not published. Ranked by annual median descending; ranked top-25 plus core trades cross-checked series-by-series against the BLS Public Data API v2 (employment, employment RSE, annual mean, hourly median, annual p10, annual median, annual p90).

## Scope rule

Include hands-on detailed occupations in SOC major group 47 (construction and extraction) and 49 (installation, maintenance, and repair). EXCLUDE: first-line supervisors (47-1011, 49-1011); helpers (47-3xxx and 49-9098); extraction workers (47-5xxx); 'all other' residual codes (xx-xxx9 ending 'All Other', e.g. 47-4099, 49-9099); any occupation with California employment under 1,000 or with suppressed CA wage/employment data. Use only detailed occupations (not broad/minor groups). Detailed 51-80xx plant and system operators are listed as exclusions for transparency because they are utility and plant operation roles rather than construction or repair trades.

## Ranked table (top 25 of 67 in-scope occupations)

| Rank | SOC | Occupation | CA median | CA p90 (top 10%) | CA mean | CA p10 | Hourly median | Employment | Emp. RSE | API check | Server-visible evidence |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| 1 | 47-4021 | Elevator and Escalator Installers and Repairers | $141,180 | $173,920 | $137,670 | $74,670 | $67.88 | 1,910 | 24.1% | match | yes (O*NET) |
| 2 | 49-9051 | Electrical Power-Line Installers and Repairers | $129,040 | $167,090 | $125,270 | $77,350 | $62.04 | 8,930 | 5.4% | match | yes (O*NET) |
| 3 | 49-2095 | Electrical and Electronics Repairers, Powerhouse, Substation, and Relay | $121,520 | $165,540 | $122,410 | $76,440 | $58.42 | 1,680 | 8.2% | match | yes (O*NET) |
| 4 | 47-2132 | Insulation Workers, Mechanical | $119,690 | $165,540 | $108,970 | $57,700 | $57.55 | 1,310 | 29.9% | match | yes (O*NET) |
| 5 | 47-4011 | Construction and Building Inspectors | $101,290 | $161,550 | $103,850 | $56,220 | $48.70 | 13,420 | 6.3% | match | yes (O*NET) |
| 6 | 49-9012 | Control and Valve Installers and Repairers, Except Mechanical Door | $100,260 | $137,030 | $100,960 | $60,360 | $48.20 | 4,310 | 11.1% | match | yes (O*NET) |
| 7 | 49-9052 | Telecommunications Line Installers and Repairers | $97,980 | $106,230 | $91,490 | $60,260 | $47.11 | 8,810 | 7.9% | match | yes (O*NET) |
| 8 | 49-2091 | Avionics Technicians | $92,480 | $126,600 | $90,750 | $58,670 | $44.46 | 1,220 | 10.6% | match | yes (O*NET) |
| 9 | 47-2073 | Operating Engineers and Other Construction Equipment Operators | $87,160 | $132,210 | $94,000 | $52,760 | $41.90 | 36,020 | 3.0% | match | yes (O*NET) |
| 10 | 49-2094 | Electrical and Electronics Repairers, Commercial and Industrial Equipment | $87,080 | $129,910 | $91,820 | $52,790 | $41.86 | 5,830 | 5.9% | match | yes (O*NET) |
| 11 | 49-3011 | Aircraft Mechanics and Service Technicians | $86,100 | $116,690 | $86,110 | $53,860 | $41.40 | 12,590 | 4.4% | match | yes (O*NET) |
| 12 | 49-9096 | Riggers | $85,730 | $127,810 | $87,230 | $53,190 | $41.22 | 2,260 | 14.6% | match | yes (O*NET) |
| 13 | 49-2093 | Electrical and Electronics Installers and Repairers, Transportation Equipment | $84,820 | $122,590 | $85,980 | $47,880 | $40.78 | 1,480 | 17.3% | match | yes (O*NET) |
| 14 | 47-2071 | Paving, Surfacing, and Tamping Equipment Operators | $83,130 | $130,120 | $94,440 | $56,980 | $39.97 | 1,400 | 10.7% | match | yes (O*NET) |
| 15 | 49-3042 | Mobile Heavy Equipment Mechanics, Except Engines | $78,550 | $129,310 | $82,320 | $47,880 | $37.76 | 20,080 | 7.1% | match | yes (O*NET) |
| 16 | 49-9044 | Millwrights | $77,950 | $127,890 | $84,220 | $49,340 | $37.48 | 2,230 | 16.1% | match | yes (O*NET) |
| 17 | 49-2022 | Telecommunications Equipment Installers and Repairers, Except Line Installers | $76,630 | $113,240 | $81,340 | $56,410 | $36.84 | 14,040 | 8.9% | match | yes (O*NET) |
| 18 | 47-2211 | Sheet Metal Workers | $76,590 | $132,190 | $85,580 | $47,410 | $36.82 | 8,390 | 8.9% | match | yes (O*NET) |
| 19 | 47-2221 | Structural Iron and Steel Workers | $76,370 | $118,030 | $80,920 | $47,480 | $36.72 | 7,110 | 11.4% | match | yes (O*NET) |
| 20 | 47-2151 | Pipelayers | $76,180 | $108,790 | $77,930 | $50,650 | $36.63 | 1,420 | 20.9% | match | yes (O*NET) |
| 21 | 47-2111 | Electricians | $76,160 | $140,340 | $85,860 | $46,800 | $36.62 | 73,310 | 2.7% | match | yes (O*NET) |
| 22 | 47-2031 | Carpenters | $75,920 | $119,950 | $78,810 | $47,490 | $36.50 | 100,750 | 3.4% | match | yes (O*NET) |
| 23 | 49-9041 | Industrial Machinery Mechanics | $74,400 | $107,700 | $76,060 | $47,880 | $35.77 | 26,830 | 3.2% | match | yes (O*NET) |
| 24 | 49-3031 | Bus and Truck Mechanics and Diesel Engine Specialists | $73,950 | $96,730 | $72,690 | $47,180 | $35.55 | 20,940 | 4.0% | match | yes (O*NET) |
| 25 | 47-2082 | Tapers | $73,460 | $115,370 | $76,260 | $45,800 | $35.32 | 4,540 | 10.5% | match | yes (O*NET) |

## Top-18 cut

The top 18 run from $141,180 (Elevator and Escalator Installers and Repairers) to $76,590 (Sheet Metal Workers). Rank 19 is Structural Iron and Steel Workers at $76,370, $220 below the cut.

## Core service trades just outside the top 18

| SOC | Occupation | Rank | CA median | CA p90 | Employment | Emp. RSE |
|---|---|---:|---:|---:|---:|---:|
| 47-2152 | Plumbers, Pipefitters, and Steamfitters | 26 | $72,830 | $131,100 | 47,660 | 5.1% |
| 49-9021 | Heating, Air Conditioning, and Refrigeration Mechanics and Installers | 27 | $72,560 | $109,060 | 35,130 | 6.9% |
| 49-2098 | Security and Fire Alarm Systems Installers | 29 | $71,570 | $98,710 | 8,180 | 7.8% |
| 47-2231 | Solar Photovoltaic Installers | 46 | $60,600 | $83,770 | 6,830 | 13.6% |
| 47-2111 | Electricians | 21 | $76,160 | $140,340 | 73,310 | 2.7% |

## Close-band note

Ranks 12-24 are separated by $11,780 in total; consecutive gaps range from $20 to $4,580. Small differences in this band are within ordinary survey variation, so public copy should not over-interpret rank order there.

| From rank | To rank | Median gap |
|---:|---:|---:|
| 12 | 13 | $910 |
| 13 | 14 | $1,690 |
| 14 | 15 | $4,580 |
| 15 | 16 | $600 |
| 16 | 17 | $1,320 |
| 17 | 18 | $40 |
| 18 | 19 | $220 |
| 19 | 20 | $190 |
| 20 | 21 | $20 |
| 21 | 22 | $240 |
| 22 | 23 | $1,520 |
| 23 | 24 | $450 |

## Small-sample caveats (employment RSE >= 20%)

- Rank 1 47-4021 Elevator and Escalator Installers and Repairers: employment 1,910, RSE 24.1%.
- Rank 4 47-2132 Insulation Workers, Mechanical: employment 1,310, RSE 29.9%.
- Rank 20 47-2151 Pipelayers: employment 1,420, RSE 20.9%.

## Exclusions

| SOC | Occupation | Reason | Employment | CA median |
|---|---|---|---:|---:|
| 47-0000 | Construction and Extraction Occupations | not a detailed occupation (major, minor, or broad group) | 672,770 | $71,670 |
| 47-1011 | First-Line Supervisors of Construction Trades and Extraction Workers | first-line supervisor | 71,750 | $97,680 |
| 47-2011 | Boilermakers | California employment 720 is under 1,000 | 720 | $118,150 |
| 47-2053 | Terrazzo Workers and Finishers | suppressed CA estimate (Employment: Estimate not released.; Employment percent relative standard error: Estimate not released.; 16: Estimate not released.; 17: Estimate not released.) | suppressed | $41,430 |
| 47-2072 | Pile Driver Operators | California employment 480 is under 1,000 | 480 | $110,340 |
| 47-2142 | Paperhangers | California employment 130 is under 1,000 | 130 | $62,790 |
| 47-3011 | Helpers--Brickmasons, Blockmasons, Stonemasons, and Tile and Marble Setters | helper occupation | 3,600 | $49,590 |
| 47-3012 | Helpers--Carpenters | helper occupation | 2,670 | $49,890 |
| 47-3013 | Helpers--Electricians | helper occupation | 3,120 | $52,080 |
| 47-3014 | Helpers--Painters, Paperhangers, Plasterers, and Stucco Masons | helper occupation | 1,990 | $46,220 |
| 47-3015 | Helpers--Pipelayers, Plumbers, Pipefitters, and Steamfitters | helper occupation | 2,500 | $47,130 |
| 47-3016 | Helpers--Roofers | helper occupation | 1,200 | $55,470 |
| 47-3019 | Helpers, Construction Trades, All Other | helper occupation | 2,990 | $48,430 |
| 47-4061 | Rail-Track Laying and Maintenance Equipment Operators | California employment 770 is under 1,000 | 770 | $71,170 |
| 47-4090 | Miscellaneous Construction and Related Workers | not a detailed occupation (major, minor, or broad group) | 2,560 | $60,890 |
| 47-5011 | Derrick Operators, Oil and Gas | extraction worker (47-5xxx) | suppressed | $55,480 |
| 47-5012 | Rotary Drill Operators, Oil and Gas | extraction worker (47-5xxx) | 460 | $65,520 |
| 47-5013 | Service Unit Operators, Oil and Gas | extraction worker (47-5xxx) | 2,820 | $62,580 |
| 47-5022 | Excavating and Loading Machine and Dragline Operators, Surface Mining | extraction worker (47-5xxx) | 790 | $74,500 |
| 47-5023 | Earth Drillers, Except Oil and Gas | extraction worker (47-5xxx) | 1,630 | $66,910 |
| 47-5032 | Explosives Workers, Ordnance Handling Experts, and Blasters | extraction worker (47-5xxx) | 220 | $80,370 |
| 47-5041 | Continuous Mining Machine Operators | extraction worker (47-5xxx) | 940 | $62,790 |
| 47-5051 | Rock Splitters, Quarry | extraction worker (47-5xxx) | 290 | $61,620 |
| 47-5071 | Roustabouts, Oil and Gas | extraction worker (47-5xxx) | 660 | $48,880 |
| 47-5081 | Helpers--Extraction Workers | extraction worker (47-5xxx) | 1,170 | $51,720 |
| 47-5099 | Extraction Workers, All Other | extraction worker (47-5xxx) | suppressed | $50,590 |
| 49-0000 | Installation, Maintenance, and Repair Occupations | not a detailed occupation (major, minor, or broad group) | 546,040 | $64,660 |
| 49-1011 | First-Line Supervisors of Mechanics, Installers, and Repairers | first-line supervisor | 51,670 | $93,660 |
| 49-2092 | Electric Motor, Power Tool, and Related Repairers | California employment 810 is under 1,000 | 810 | $66,040 |
| 49-2096 | Electronic Equipment Installers and Repairers, Motor Vehicles | California employment 960 is under 1,000 | 960 | $48,500 |
| 49-3043 | Rail Car Repairers | California employment 700 is under 1,000 | 700 | $68,370 |
| 49-9045 | Refractory Materials Repairers, Except Brickmasons | suppressed CA estimate (Employment: Estimate not released.; Employment percent relative standard error: Estimate not released.; 16: Estimate not released.; 17: Estimate not released.) | suppressed | $77,220 |
| 49-9061 | Camera and Photographic Equipment Repairers | suppressed CA estimate (Employment: Estimate not released.; Employment percent relative standard error: Estimate not released.; 16: Estimate not released.; 17: Estimate not released.) | suppressed | $59,770 |
| 49-9063 | Musical Instrument Repairers and Tuners | California employment 520 is under 1,000 | 520 | $47,580 |
| 49-9064 | Watch and Clock Repairers | suppressed CA estimate (Employment: Estimate not released.; Employment percent relative standard error: Estimate not released.; 16: Estimate not released.; 17: Estimate not released.) | suppressed | $110,050 |
| 49-9069 | Precision Instrument and Equipment Repairers, All Other | 'All Other' residual code | 1,460 | $80,060 |
| 49-9081 | Wind Turbine Service Technicians | California employment 400 is under 1,000 | 400 | $77,910 |
| 49-9092 | Commercial Divers | California employment 310 is under 1,000 | 310 | $101,540 |
| 49-9095 | Manufactured Building and Mobile Home Installers | suppressed CA estimate (Employment: Estimate not released.; Employment percent relative standard error: Estimate not released.; 16: Estimate not released.; 17: Estimate not released.) | suppressed | $59,450 |
| 49-9097 | Signal and Track Switch Repairers | California employment 390 is under 1,000 | 390 | $84,670 |
| 49-9098 | Helpers--Installation, Maintenance, and Repair Workers | helper occupation | 9,050 | $44,670 |
| 49-9099 | Installation, Maintenance, and Repair Workers, All Other | 'All Other' residual code | 23,630 | $51,230 |
| 51-8012 | Power Distributors and Dispatchers | dispatcher / non-hands-on role (power distributors and dispatchers) | 670 | $137,570 |
| 51-8013 | Power Plant Operators | plant and system operator (SOC 51-80xx), outside the construction and repair trade scope | 2,610 | $105,210 |
| 51-8021 | Stationary Engineers and Boiler Operators | plant and system operator (SOC 51-80xx), outside the construction and repair trade scope | 5,840 | $90,650 |
| 51-8031 | Water and Wastewater Treatment Plant and System Operators | plant and system operator (SOC 51-80xx), outside the construction and repair trade scope | 11,630 | $81,770 |
| 51-8091 | Chemical Plant and System Operators | plant and system operator (SOC 51-80xx), outside the construction and repair trade scope | 780 | $87,550 |
| 51-8092 | Gas Plant Operators | plant and system operator (SOC 51-80xx), outside the construction and repair trade scope | 800 | $130,220 |
| 51-8093 | Petroleum Pump System Operators, Refinery Operators, and Gaugers | plant and system operator (SOC 51-80xx), outside the construction and repair trade scope | 3,360 | $103,250 |
| 51-8099 | Plant and System Operators, All Other | plant and system operator (SOC 51-80xx), outside the construction and repair trade scope | 1,560 | $78,020 |

## Benchmarks

| SOC | Group | CA median | Employment |
|---|---|---:|---:|
| 00-0000 | All Occupations | $58,240 | 18,213,700 |
| 47-0000 | Construction and Extraction Occupations | $71,670 | 672,770 |
| 49-0000 | Installation, Maintenance, and Repair Occupations | $64,660 | 546,040 |

## Evidence routes

data.bls.gov/oes/ and data.bls.gov/timeseries/OEUS... return HTTP 200 to the repo fetcher but the OEWS figures are not in the server-rendered HTML (SPA / empty series table), so they fail source_evidence_not_found if cited as the proof URL. api.bls.gov JSON is rejected by the fetcher's MIME policy (text/html, text/plain, application/xhtml+xml only), which routes source support to the local-artifact fallback and requires a tool-emitted capture receipt. O*NET OnLine Local Wages (DOL-sponsored, 'Source: Bureau of Labor Statistics 2025 wage data') renders the California p10/p25/median/p75/p90 row server-side and is the working public-copy proof URL. Employment counts and RSEs are not on the O*NET page; they are evidenced only by the saved BLS API/OESServices snapshots.

