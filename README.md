🎯 Purpose
Assess Battery Energy Storage sizing for firm power delivery from hybrid renewable system:

Hydro: 250 MW baseload (24/7)
PV: Variable (500–1,000 MW sensitivity)
Wind: Variable (~1,104 MW)
BESS: Sensitivity sweep (500–3,500 MWh)

📐 Three-Tier Dispatch
Tier	Condition	Output
FIRM	Hydro+RE+BESS ≥ Target	Full firm power
SUPPLEMENTAL	Hydro ≥ 250 MW	Hydro only
SHUTDOWN	Hydro < 250 MW	Zero

📊 Outputs
Capacity Factor % vs BESS size
Days with 24h full operation vs BESS
Curtailment % vs BESS size
Typical & low-renewable dispatch profiles
Baseline performance (no BESS)
Full hourly dispatch download

📁 Required Inputs
File	Format
PV Profile	CSV/XLSX, 8760 hrs
Wind Profile	CSV/XLSX, 8760 hrs
