# MaizeCare soil-water estimate

This feature reports a weather-based model estimate, never a physical sensor reading. Historical precipitation and FAO reference evapotranspiration (ET₀) are retrieved from the Open-Meteo Historical Weather API. Those values are gridded historical reanalysis and are not measurements from a farmer's rain gauge or weather station. The future window uses the existing Open-Meteo seven-day forecast.

## Method

The calculation follows the daily root-zone depletion structure in FAO Irrigation and Drainage Paper 56:

`ETc = Kc × ET₀`

`net balance = rainfall + entered irrigation − ETc`

`TAW = AWC × effective root depth`

The available-water figure is `TAW - min(TAW, max(0, -cumulative net balance))`, with depletion bounded from zero to TAW. It is returned in millimetres only when planting date, farmer-confirmed growth stage, a farmer-provided available-water capacity, and usable historical daily precipitation/ET₀ are all available. No percentage is inferred.

Maize stage Kc values are representative FAO-56 values: initial 0.40, development 0.80, mid-season 1.15, and late-season 0.70. Representative root depths used for the simplified storage estimate are 0.30 m, 0.60 m, 1.00 m, and 1.00 m respectively. Root depths are model assumptions, not local measurements. The farmer-selected current stage is applied across the historical window because complete stage transition dates are not collected.

## Limitations and inputs

- At planting, the model initializes storage at field capacity. This is an assumption, not a measured initial condition.
- Reanalysis rainfall is provisionally treated as effective rainfall. Runoff, interception, deep percolation, capillary rise, and within-field variation are not modeled.
- Only a farmer-entered most recent irrigation date and depth are included. Unreported irrigation lowers reliability; daily irrigation logs are not required.
- Soil texture is saved as context but does not imply a water-holding value. The estimate requires an available-water capacity (mm/m) provided by the farmer from a soil analysis or another trusted local source; the application does not infer it from texture.
- If essential inputs or complete historical weather are missing, root-zone availability is withheld. The page may show a historical net weather water-balance signal, clearly separated from the future forecast balance.
- Estimates use at most the latest 365 days of historical archive values. Stale or incomplete values lower reliability.

This is a screening aid for field observations, not irrigation scheduling or agronomic diagnosis. FAO-56 formulation references: [daily root-zone water balance](https://www.fao.org/4/X0490E/x0490e0e.htm), [crop coefficient method](https://www.fao.org/land-water/land/land-governance-and-planning/land-resources-planning-toolbox/detail/crop-evapotranspiration-%28crop-et0%29/en), [maize stage coefficients](https://www.fao.org/4/s2022e/s2022e07.htm). Open-Meteo describes historical API values as reanalysis: [Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api).
