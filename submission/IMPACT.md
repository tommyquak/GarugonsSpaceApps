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

## What it would take to use it for real

We are a student team at a hackathon, and this is a prototype. Honest next steps:

1. **Ground checks.** Take the top-ranked blocks to people who know the land and compare. Until then the list is a screening result.
2. **A water-level record.** A single season of gauge data in the study area would let us say what a decibel of fall means in centimetres. We found no public 2026 record.
3. **A second and third season.** One El Nino year cannot show how the method behaves in a wet year.
4. **Someone to hand it to.** The outputs are in formats a GIS or a GPS reads. It needs an agency or a field group to pull on it.

## What we do not promise

- It does not measure the water table. Colour means the radar echo fell.
- It does not predict fire. It marks ground that is ready to burn; people light the fires.
- It does not replace a field visit. It says where to make one first.
- It covers two boxes in Central Kalimantan for one season.

## The one-sentence version

Drained peat dries for weeks before it burns and sends haze across the region, and until now nobody could watch that happen: we used NISAR's first dry season to map where Borneo's peat dried, where it burned, and what the rain did not bring back, and turned it into a ranked list of where to rewet first.

## Sources

1. World Bank (2016), The Cost of Fire: An Economic Analysis of Indonesia's 2015 Fire Crisis. https://openknowledge.worldbank.org/entities/publication/391e19f4-18f7-56c2-8c28-bb89cc9e7d6f
2. Koplitz et al. (2016), Public health impacts of the severe haze in Equatorial Asia in September to October 2015, Environmental Research Letters 11, 094023. doi 10.1088/1748-9326/11/9/094023. A modelled estimate, not a count of recorded deaths.
3. Statement of Singapore's Minister for the Environment and Water Resources, 25 September 2015, National Archives of Singapore. https://www.nas.gov.sg/archivesonline/data/pdfdoc/MSE_20150925001.pdf
4. Government of Indonesia, Regulation 57 of 2016 amending Regulation 71 of 2014 on the protection and management of peat ecosystems. To be checked against the text before submission.
5. Mongabay (2022), Indonesia on track with peatland restoration but bogged down with mangroves. https://news.mongabay.com/2022/02/indonesia-on-track-with-peatland-restoration-but-bogged-down-with-mangroves/ Press coverage; the agency's own report would be a better source.
