# Impact

Who would use this, for which decision, and what it changes. Written by Tommy's side to be lifted into `PAGE.md` and one slide; Reagan owns those files. Every `[v: key]` is a number from `pipeline/out/validation.json`, to be filled when that entry is `final`. Every outside fact has its source at the bottom. No user, partner or quotation here is invented: nobody has tested this tool yet, and the page must not suggest otherwise.

## The problem, in three facts

1. **Peat fires are a regional health and economic event, not a local one.** The World Bank put the cost of Indonesia's 2015 fires at USD 16.1 billion, about 1.9% of the country's GDP [1]. A modelling study estimated 100,300 excess deaths across Indonesia, Malaysia and Singapore from that season's smoke [2]. On 25 September 2015 Singapore closed its primary and secondary schools because of haze [3].
2. **Drained peat is where the worst of it starts.** Canals lower the water table, the peat dries, and dry peat burns underground for weeks. Indonesian regulation requires the water table in peat to stay within 0.4 m of the surface [4], and the national peat and mangrove restoration agency was tasked with restoring 1.2 million hectares of peatland by 2024 [5].
3. **Nobody can watch the drying happen.** In the dry season the ground is hidden from optical satellites by cloud and then by smoke, and water-level gauges exist at only a few sites. The people who must decide where to block canals or send patrols work from last year's fire map.

Not every fire in Indonesia is a peat fire. In our own study area fire touched [v: fire_share_on_peat_west] of the mapped peat and [v: fire_share_off_peat_west] of the land outside it. The map shows both.

## Who decides what, and what this gives them

| Who | The decision | What they have today | What this adds |
|---|---|---|---|
| Peat restoration planners | Which canals to block first, with a limited budget | Peat maps, canal maps, last year's burn scars | A ranked list of 1 km blocks of peat that dried on both radar orbits, did not burn, and stayed low after the rain: [v: blocks_rewet_first_west] in the west box, [v: blocks_rewet_first_high_west] of them at high confidence. With coordinates, as CSV and GeoJSON |
| Fire brigades and village fire patrols | Where to patrol during the dry season | Hotspot alerts, which arrive after ignition | Every 12 days, which drained peat has dried and not yet burned. Inside drained peat, blocks already dry by late July went on to burn in [v: hindcast_near_canal_burned_later_if_early_dry_west] of cases, against [v: hindcast_near_canal_burned_later_if_not_west] of the rest |
| Post-fire recovery teams | Which burnt areas need replanting, not only rewetting | Burn scar maps | Where the canopy signal (HV) stayed down after the rain while the ground signal (HH) came back: [v: blocks_assess_burn_west] blocks to assess |
| Researchers, journalists, the public in the haze's path | Whether a claim about this season is true | Press reports, hotspot counts | An open map with its evidence and its limits one tap away, and code that rebuilds every number |

## What changes because it exists

- **From once a year to every 12 days.** NISAR passes every 12 days on each orbit and sees through cloud and smoke. The picture arrives during the season, while a decision can still be made.
- **From "where it burned" to "where it dried".** Hotspots tell you a fire has started. This shows the condition that makes fire possible, and what the rain did and did not undo.
- **From a map to a list.** A restoration team cannot act on a colour ramp. It can act on [v: blocks_rewet_first_west] squares with coordinates, a reason for each, and a confidence grade.
- **At no cost per use.** Every input is free and open, the processing is one command on a laptop, and the app is a static site with no server.

## Ground truth: the main gap, and how to close it

Nothing in this project was checked against the ground. Every test we ran is internal: two orbits agree, intact forest is not flagged, the rain brings the signal back. Those show the signal is real. They do not show what it means in centimetres of water, and that is the weakest point of the work.

**What exists in public, and why it does not settle it.** Two water-level records from this landscape are openly licensed: daily groundwater levels in drained and undrained peat swamp forest near Palangka Raya for 2013 to 2018 [6], and water levels at forested, dammed and drained sites in Sebangau from August 2019 to January 2020 [7]. Neither overlaps NISAR, which began observing here in 2026. Indonesia's peat water-level monitoring network would be the obvious source for 2026, and we could not reach its data.

**What could be done without going to the field.** The 2013 to 2018 record can calibrate a simple rainfall-driven water-table model. Run on NASA's 2026 rainfall, it would give a modelled water table for the same weeks the radar saw, to set beside the radar curve. That is a bridge, not a measurement, and it must be labelled as modelled.

**What real ground truthing would look like.** A small, cheap protocol that a field partner could run in one dry season:

1. Pick about 30 of the 1 km blocks, spread evenly over "rewet first", "watch" and "no action flagged", in places that can be reached.
2. At each, twice (late dry season, and two weeks after the first rain): depth to the water table in a dipwell, whether a canal is present and how full it is, signs of fire, a photograph of the vegetation, and a GPS fix.
3. Compare. Do the flagged blocks have deeper water tables than the unflagged ones? How many decibels of fall go with how many centimetres? Do the "did not come back" blocks differ on the ground from the ones that did?

About sixty visits would turn a screening map into a calibrated one, or show where it is wrong.

## What it would take to use it for real

We are a student team at a hackathon, and this is a prototype. Honest next steps:

1. **Ground truth,** as above. Until then the list is a screening result.
2. **A second and third season.** One El Nino year cannot show how the method behaves in a wet year.
3. **Someone to hand it to.** The outputs are in formats a GIS or a GPS reads. It needs an agency or a field group to pull on it.

## What we do not promise

- It does not measure the water table. Colour means the radar echo fell.
- It does not predict fire. It marks ground that is ready to burn; people light the fires.
- It does not replace a field visit. It says where to make one first, and it has not yet been checked by one.
- It covers two boxes in Central Kalimantan for one season.

## The one-sentence version

Drained peat dries for weeks before it burns and sends haze across the region, and until now nobody could watch that happen: we used NISAR's first dry season to map where Borneo's peat dried, where it burned, and what the rain did not bring back, and turned it into a ranked list of where to rewet first.

## Sources

1. World Bank (2016), The Cost of Fire: An Economic Analysis of Indonesia's 2015 Fire Crisis. https://openknowledge.worldbank.org/entities/publication/391e19f4-18f7-56c2-8c28-bb89cc9e7d6f
2. Koplitz et al. (2016), Public health impacts of the severe haze in Equatorial Asia in September to October 2015, Environmental Research Letters 11, 094023. doi 10.1088/1748-9326/11/9/094023. A modelled estimate, not a count of recorded deaths.
3. Statement of Singapore's Minister for the Environment and Water Resources, 25 September 2015, National Archives of Singapore. https://www.nas.gov.sg/archivesonline/data/pdfdoc/MSE_20150925001.pdf
4. Government of Indonesia, Regulation 57 of 2016 amending Regulation 71 of 2014 on the protection and management of peat ecosystems. To be checked against the text before submission.
5. Mongabay (2022), Indonesia on track with peatland restoration but bogged down with mangroves. https://news.mongabay.com/2022/02/indonesia-on-track-with-peatland-restoration-but-bogged-down-with-mangroves/ Press coverage; the agency's own report would be a better source.
6. Hirano and colleagues, daily groundwater level in drained and undrained peat swamp forest near Palangka Raya, 2013 to 2018. figshare, doi 10.6084/m9.figshare.22321129, CC BY 4.0.
7. Putra, Holden and Baird, water level, rainfall and evapotranspiration at forested, dammed and drained sites in Sebangau, from August 2019. University of Leeds, doi 10.5518/960, CC BY 4.0.
