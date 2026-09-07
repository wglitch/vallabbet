const coverageInput = document.querySelector("#coverage");
const coverageLabel = document.querySelector("#coverage-label");
const coverageTitle = document.querySelector('label[for="coverage"] span');
const timeScale = document.querySelector("#time-scale");
const countedDistricts = document.querySelector("#counted-districts");
const countedVotes = document.querySelector("#counted-votes");
const liveUpdated = document.querySelector("#live-updated");
const partyTable = document.querySelector("#party-table");
const partyTabs = document.querySelector("#party-tabs");
const focusPanel = document.querySelector("#focus-panel");
const radioLine = document.querySelector("#radio-line");
const countySignals = document.querySelector("#county-signals");
const districtSignals = document.querySelector("#district-signals");
const countySelect = document.querySelector("#county-select");
const countyTable = document.querySelector("#county-table");
const countyStory = document.querySelector("#county-story");
const viewTabs = document.querySelectorAll(".view-tabs button");
const viewPanels = document.querySelectorAll("[data-view-panel]");
const opinionToggle = document.querySelector("#opinion-toggle");
const opinionNote = document.querySelector("#opinion-note");
const coalitionPresets = document.querySelector("#coalition-presets");
const coalitionParties = document.querySelector("#coalition-parties");
const coalitionResult = document.querySelector("#coalition-result");
const mandateIndicator = document.querySelector("#mandate-indicator");
const modeNoteText = document.querySelector("#mode-note-text");
const percent = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
const integer = new Intl.NumberFormat("sv-SE");
const clock = new Intl.DateTimeFormat("sv-SE", { hour: "2-digit", minute: "2-digit" });
const dayClock = new Intl.DateTimeFormat("sv-SE", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

let payload;
let timeline;
let focusParty = "S";
let selectedCounty = "Jämtland";
let showOpinion = false;
let selectedCoalition = new Set(["M", "KD", "L", "SD"]);
let opinionReference = null;

const coalitionOptions = [
  { name: "Tidöpartierna", parties: ["M", "KD", "L", "SD"] },
  { name: "S + V + C + MP", parties: ["S", "V", "C", "MP"] },
];

const parliamentSeats = 349;
const parliamentThreshold = 4;

const neighborMinAreas = 8;
const neighborMinVotes = 6500;

const strata = [
  {
    key: (district) => `type-profile:${district.municipalityType}|${district.historicProfile}`,
    source: "kommuntyp + profil",
    minDistricts: 8,
    minVotes: 6500,
  },
  {
    key: (district) => `type:${district.municipalityType}`,
    source: "kommuntyp",
    minDistricts: 16,
    minVotes: 12000,
  },
  {
    key: (district) => `band-profile:${district.municipalityBand}|${district.historicProfile}`,
    source: "huvudgrupp + profil",
    minDistricts: 10,
    minVotes: 8500,
  },
  {
    key: (district) => `band:${district.municipalityBand}`,
    source: "huvudgrupp",
    minDistricts: 22,
    minVotes: 18000,
  },
  {
    key: (district) => `profile:${district.historicProfile}`,
    source: "historisk profil",
    minDistricts: 20,
    minVotes: 16000,
  },
  {
    key: (district) => `county:${district.county}`,
    source: "län",
    minDistricts: 18,
    minVotes: 12000,
  },
  {
    key: () => "national",
    source: "riket",
    minDistricts: 1,
    minVotes: 1,
  },
];

function areaCountyCode(area) {
  return area.countyCode || String(area.municipalityCode || "").slice(0, 2) || area.county;
}

function neighborKeys(area) {
  const county = areaCountyCode(area);
  return [
    `municipality:${area.municipalityCode}`,
    `county-type-profile:${county}|${area.municipalityType}|${area.historicProfile}`,
    `county-type:${county}|${area.municipalityType}`,
    `county-profile:${county}|${area.historicProfile}`,
    `county:${county}`,
    `type-profile:${area.municipalityType}|${area.historicProfile}`,
    "national",
  ];
}

function sumDistricts(districts, validKey, voteKey) {
  const total = { valid: 0 };
  Object.keys(payload.parties).forEach((party) => total[party] = 0);
  districts.forEach((district) => {
    total.valid += district[validKey];
    Object.keys(payload.parties).forEach((party) => {
      total[party] += district[voteKey][party] || 0;
    });
  });
  return total;
}

function splitAreasByTime(areas, cutoffMs) {
  const take = areas.findIndex((area) => !Number.isFinite(area.reportMs) || area.reportMs > cutoffMs);
  const end = take === -1 ? areas.length : Math.max(1, take);
  return {
    counted: areas.slice(0, end),
    uncounted: areas.slice(end),
  };
}

function share(total, party) {
  return total.valid ? total[party] / total.valid * 100 : 0;
}

function swing(current, baseline, party) {
  return share(current, party) - share(baseline, party);
}

function signed(value) {
  return `${value > 0 ? "+" : ""}${percent.format(value)}`;
}

function uncertaintyLabel(value) {
  return `±${percent.format(value)}`;
}

function reportMs(district) {
  return Date.parse(district.reportingTimeRD || district.reportingTime);
}

function minutesBetween(startMs, endMs) {
  return Math.max(0, Math.round((endMs - startMs) / 60000));
}

function formatReplayTime(ms) {
  const date = new Date(ms);
  const firstDate = new Date(timeline.minMs);
  if (date.toDateString() === firstDate.toDateString()) {
    return `kl. ${clock.format(date)}`;
  }
  return dayClock.format(date);
}

function setupTimeline() {
  coverageTitle.textContent = payload.mode === "valmyndigheten-live" ? "Rapporteringstid" : "Tid i replayen";
  payload.districts.forEach((district) => {
    district.reportMs = reportMs(district);
  });
  if (payload.currentDistricts) {
    payload.currentDistricts.forEach((district) => {
      district.reportMs = reportMs(district);
    });
    payload.currentDistricts.sort((a, b) => (Number.isFinite(a.reportMs) ? a.reportMs : Infinity) - (Number.isFinite(b.reportMs) ? b.reportMs : Infinity));
  }
  payload.districts.sort((a, b) => (Number.isFinite(a.reportMs) ? a.reportMs : Infinity) - (Number.isFinite(b.reportMs) ? b.reportMs : Infinity));

  const validTimes = payload.districts
    .map((district) => district.reportMs)
    .filter(Number.isFinite);
  const minMs = Math.min(...validTimes);
  const maxMs = Math.max(...validTimes);
  const firstDate = new Date(minMs);
  const preferredNightEnd = new Date(firstDate);
  preferredNightEnd.setDate(preferredNightEnd.getDate() + 1);
  preferredNightEnd.setHours(1, 0, 0, 0);
  const nightEndMs = Math.min(maxMs, Math.max(minMs, preferredNightEnd.getTime()));
  const nightMinutes = minutesBetween(minMs, nightEndMs);
  const finalStep = nightMinutes + 12;

  timeline = { minMs, maxMs, nightEndMs, nightMinutes, finalStep };
  coverageInput.min = "0";
  coverageInput.max = String(finalStep);
  coverageInput.step = "1";
  coverageInput.value = payload.mode === "valmyndigheten-live"
    ? String(finalStep)
    : String(Math.min(finalStep, minutesBetween(minMs, Date.parse("2022-09-11T21:43:00"))));

  const marks = [
    { label: clock.format(new Date(minMs)), step: 0 },
    { label: "21", step: minutesBetween(minMs, new Date(firstDate).setHours(21, 0, 0, 0)) },
    { label: "22", step: minutesBetween(minMs, new Date(firstDate).setHours(22, 0, 0, 0)) },
    { label: "23", step: minutesBetween(minMs, new Date(firstDate).setHours(23, 0, 0, 0)) },
    { label: "00", step: minutesBetween(minMs, new Date(firstDate.getFullYear(), firstDate.getMonth(), firstDate.getDate() + 1, 0, 0, 0).getTime()) },
    { label: "01", step: nightMinutes },
    { label: "slut", step: finalStep },
  ].filter((mark) => mark.step >= 0 && mark.step <= finalStep);

  timeScale.innerHTML = marks.map((mark) => `
    <span style="left:${mark.step / finalStep * 100}%">${mark.label}</span>
  `).join("");
}

function currentCutoff() {
  const step = Number(coverageInput.value);
  if (step > timeline.nightMinutes) {
    return { ms: timeline.maxMs, isFinal: true };
  }
  return { ms: timeline.minMs + step * 60000, isFinal: false };
}

function splitByTime(cutoffMs) {
  return splitAreasByTime(payload.districts, cutoffMs);
}

function groupBy(districts, key) {
  return districts.reduce((groups, district) => {
    const groupKey = key(district);
    groups.set(groupKey, [...(groups.get(groupKey) || []), district]);
    return groups;
  }, new Map());
}

function makeStat(districts) {
  const current = sumDistricts(districts, "valid22", "votes22");
  const baseline = sumDistricts(districts, "valid18", "votes18");
  return { districts: districts.length, current, baseline };
}

function makeModel(counted) {
  const stats = new Map();
  strata.forEach((layer) => {
    groupBy(counted, layer.key).forEach((districts, key) => stats.set(key, makeStat(districts)));
  });
  return { stats, counted: makeStat(counted) };
}

function makeNeighborModel(counted) {
  const groups = new Map();
  counted.forEach((district) => {
    neighborKeys(district).forEach((key) => {
      groups.set(key, [...(groups.get(key) || []), district]);
    });
  });
  const stats = new Map();
  groups.forEach((districts, key) => stats.set(key, makeStat(districts)));
  return { stats };
}

function chooseStratum(model, district) {
  for (const layer of strata) {
    const key = layer.key(district);
    const stat = model.stats.get(key);
    if (stat && stat.districts >= layer.minDistricts && stat.baseline.valid >= layer.minVotes) {
      return { source: layer.source, stat };
    }
  }
  return { source: "riket", stat: model.stats.get("national") };
}

function chooseNeighborStat(model, district) {
  for (const key of neighborKeys(district)) {
    const stat = model.stats.get(key);
    if (stat && stat.districts >= neighborMinAreas && stat.baseline.valid >= neighborMinVotes) {
      return { source: key.split(":")[0], stat };
    }
  }
  return { source: "national", stat: model.stats.get("national") };
}

function neighborBlendWeight(currentVotes, uncountedVotes) {
  if (!uncountedVotes) return 0;
  if (currentVotes >= 2500000) return .6;
  if (currentVotes >= 1500000) return .35;
  if (currentVotes >= 900000) return .15;
  return 0;
}

function uncertaintyFrom(currentVotes, uncountedVotes, blendWeight) {
  let span = 1.4;
  if (currentVotes >= 5100000) span = .12;
  else if (currentVotes >= 4000000) span = .16;
  else if (currentVotes >= 2500000) span = .22;
  else if (currentVotes >= 1500000) span = .28;
  else if (currentVotes >= 900000) span = .35;
  else if (currentVotes >= 350000) span = .55;
  else if (currentVotes >= 100000) span = .85;
  if (blendWeight >= .5) span = Math.max(.12, span - .04);
  if (!uncountedVotes) span = .10;
  return span;
}

function confidenceFrom(countedStat, sourceMix) {
  if (!sourceMix.total) {
    return {
      level: "high",
      label: "Resultatläge",
      note: "Alla jämförelseområden i vyn är räknade i det här läget.",
    };
  }
  const localShare = sourceMix.total ? sourceMix.stratified / sourceMix.total : 0;
  if (countedStat.current.valid >= 1100000 && localShare >= .58) {
    return {
      level: "high",
      label: "Högre säkerhet",
      note: "Mycket underlag är räknat och större delen av oräknat kan jämföras med liknande områden.",
    };
  }
  if (countedStat.current.valid >= 260000 && localShare >= .25) {
    return {
      level: "medium",
      label: "Medel",
      note: "Trenden syns i delar av relevant underlag, men modellen faller fortfarande tillbaka brett.",
    };
  }
  return {
    level: "low",
    label: "Låg",
      note: "Få jämförbara röster eller för lite liknande underlag är inne ännu.",
  };
}

function forecastRows(counted, uncounted, model, officialCounted = counted) {
  const current = sumDistricts(counted, "valid22", "votes22");
  const officialCurrent = sumDistricts(officialCounted, "valid22", "votes22");
  const baseline = sumDistricts(counted, "valid18", "votes18");
  const uncountedBaseline = sumDistricts(uncounted, "valid18", "votes18");
  const fullBaseline = { valid: baseline.valid + uncountedBaseline.valid };
  Object.keys(payload.parties).forEach((party) => {
    fullBaseline[party] = baseline[party] + uncountedBaseline[party];
  });
  const forecastVotes = {};
  const neighborVotes = {};
  const sourceMix = { total: 0, stratified: 0, sources: new Set() };
  const neighborModel = makeNeighborModel(counted);
  const neighborMix = { total: 0, local: 0, sources: new Set() };
  const blendWeight = neighborBlendWeight(current.valid, uncountedBaseline.valid);
  Object.keys(payload.parties).forEach((party) => {
    forecastVotes[party] = current[party];
    neighborVotes[party] = current[party];
  });

  uncounted.forEach((district) => {
    const choice = chooseStratum(model, district);
    const neighborChoice = chooseNeighborStat(neighborModel, district);
    sourceMix.total += district.valid18;
    sourceMix.sources.add(choice.source);
    if (choice.source !== "riket") {
      sourceMix.stratified += district.valid18;
    }
    neighborMix.total += district.valid18;
    neighborMix.sources.add(neighborChoice.source);
    if (neighborChoice.source !== "national") {
      neighborMix.local += district.valid18;
    }
    Object.keys(payload.parties).forEach((party) => {
      const districtBase = district.votes18[party] / district.valid18 * 100;
      const delta = swing(choice.stat.current, choice.stat.baseline, party);
      const neighborDelta = swing(neighborChoice.stat.current, neighborChoice.stat.baseline, party);
      forecastVotes[party] += Math.max(0, districtBase + delta) / 100 * district.valid18;
      neighborVotes[party] += Math.max(0, districtBase + neighborDelta) / 100 * district.valid18;
    });
  });

  const forecastScale = current.valid + uncountedBaseline.valid;
  const uncertainty = uncertaintyFrom(current.valid, uncountedBaseline.valid, blendWeight);
  const rows = Object.entries(payload.parties).map(([party, meta]) => ({
    party,
    ...meta,
    raw: share(officialCurrent, party),
    baselineShare: share(baseline, party),
    previousFinalShare: share(fullBaseline, party),
    rawDelta: share(officialCurrent, party) - share(fullBaseline, party),
    delta: swing(current, baseline, party),
    adjustedForecast: forecastVotes[party] / forecastScale * 100,
    neighborForecast: neighborVotes[party] / forecastScale * 100,
    forecast: (
      forecastVotes[party] * (1 - blendWeight)
      + neighborVotes[party] * blendWeight
    ) / forecastScale * 100,
    uncertainty,
  })).sort((a, b) => b.forecast - a.forecast);

  return {
    rows,
    current,
    officialCurrent,
    baseline,
    uncountedBaseline,
    confidence: confidenceFrom({ current }, sourceMix),
    sourceMix,
    neighborMix,
    blendWeight,
    uncertainty,
  };
}

function confidenceBadge(confidence) {
  return `<span class="confidence ${confidence.level}">${confidence.label}</span>`;
}

function opinionValue(party) {
  const value = opinionReference?.parties?.[party];
  return Number.isFinite(value) ? `${percent.format(value)}%` : "–";
}

function renderRows(target, rows, confidence, options = {}) {
  const showOpinionColumn = options.showOpinion === true;
  target.innerHTML = `
    <div class="party-row labels ${showOpinionColumn ? "with-opinion" : ""}">
      <span>Parti</span><span>Just nu</span><span>Samma områden förra valet</span><span>Prognos</span><span>Osäkerhet</span>${showOpinionColumn ? "<span>Opinion</span>" : ""}
    </div>
    ${rows.map((row) => `
      <div class="party-row ${showOpinionColumn ? "with-opinion" : ""}">
        <span class="party-name"><i style="background:${row.color}"></i>${row.party}</span>
        <span class="value-with-delta">${percent.format(row.raw)}% <small class="${row.rawDelta >= 0 ? "rise" : "fall"}" title="Jämfört med hela förra valets jämförelseunderlag">${signed(row.rawDelta)}</small></span>
        <span class="value-with-delta">${percent.format(row.baselineShare)}% <small class="${row.delta >= 0 ? "rise" : "fall"}" title="Aktuellt val jämfört med samma områden förra valet">${signed(row.delta)}</small></span>
        <strong class="forecast-cell" title="${confidence.label}">${percent.format(row.forecast)}%</strong>
        <span class="uncertainty" title="Praktiskt felspann jämfört mot historiska backtester. Sena röster återstår.">${uncertaintyLabel(row.uncertainty)}</span>
        ${showOpinionColumn ? `<span class="opinion-value">${opinionValue(row.party)}</span>` : ""}
        <b style="--fill:${row.forecast}%;--party:${row.color}"></b>
      </div>
    `).join("")}
  `;
}

function coalitionTotals(rows, parties) {
  const chosen = rows.filter((row) => parties.includes(row.party));
  const totals = chosen.reduce((total, row) => ({
      raw: total.raw + row.raw,
      forecast: total.forecast + row.forecast,
    }), { raw: 0, forecast: 0 });
  const baseUncertainty = chosen.length ? Math.max(...chosen.map((row) => row.uncertainty)) : rows[0]?.uncertainty || 1;
  return {
    ...totals,
    uncertainty: baseUncertainty * (chosen.length >= 3 ? 1.15 : 1),
  };
}

function differenceClass(value) {
  if (Math.abs(value) < .05) return "";
  return value > 0 ? "rise" : "fall";
}

function allocateMandates(rows) {
  const eligible = rows
    .filter((row) => row.forecast >= parliamentThreshold)
    .map((row) => ({ ...row }));
  const eligibleShare = eligible.reduce((sum, row) => sum + row.forecast, 0);
  if (!eligibleShare) {
    return { eligible: [], excluded: rows, seatsByParty: new Map(), eligibleShare: 0 };
  }
  const allocations = eligible.map((row) => {
    const quota = row.forecast / eligibleShare * parliamentSeats;
    return {
      ...row,
      quota,
      seats: Math.floor(quota),
      remainder: quota - Math.floor(quota),
    };
  });
  let remaining = parliamentSeats - allocations.reduce((sum, row) => sum + row.seats, 0);
  allocations
    .sort((a, b) => b.remainder - a.remainder || b.forecast - a.forecast)
    .slice(0, remaining)
    .forEach((row) => {
      row.seats += 1;
    });
  allocations.sort((a, b) => b.seats - a.seats || b.forecast - a.forecast);
  return {
    eligible: allocations,
    excluded: rows.filter((row) => row.forecast < parliamentThreshold),
    seatsByParty: new Map(allocations.map((row) => [row.party, row.seats])),
    eligibleShare,
  };
}

function coalitionSeats(seatsByParty, parties) {
  return parties.reduce((sum, party) => sum + (seatsByParty.get(party) || 0), 0);
}

function thresholdWarnings(rows) {
  return rows
    .filter((row) => Math.abs(row.forecast - parliamentThreshold) <= .6)
    .sort((a, b) => Math.abs(a.forecast - parliamentThreshold) - Math.abs(b.forecast - parliamentThreshold));
}

function partyLabel(parties) {
  return parties.length ? parties.join(" + ") : "Inga partier valda";
}

function renderMandateIndicator(rows) {
  const mandates = allocateMandates(rows);
  const selectedSeats = coalitionSeats(mandates.seatsByParty, [...selectedCoalition]);
  const presetSeats = coalitionOptions.map((option) => ({
    ...option,
    seats: coalitionSeats(mandates.seatsByParty, option.parties),
  }));
  const warnings = thresholdWarnings(rows);
  mandateIndicator.innerHTML = `
    <div class="panel-head mandate-head">
      <div>
        <h3>Mandatindikator</h3>
        <p>Förenklad fördelning av ${parliamentSeats} mandat mellan partier över ${parliamentThreshold} procent.</p>
      </div>
      <strong>${selectedSeats} mandat</strong>
    </div>
    <div class="mandate-blocks">
      ${presetSeats.map((item) => `
        <div>
          <span>${item.name}</span>
          <b>${item.seats}</b>
        </div>
      `).join("")}
      <div>
        <span>${partyLabel([...selectedCoalition])}</span>
        <b>${selectedSeats}</b>
      </div>
    </div>
    <div class="mandate-list">
      ${mandates.eligible.map((row) => `
        <div>
          <span><i style="background:${row.color}"></i>${row.party}</span>
          <b>${row.seats}</b>
        </div>
      `).join("")}
    </div>
    <p class="mandate-warning">
      ${warnings.length
        ? `Spärrnära: ${warnings.map((row) => `${row.party} ${percent.format(row.forecast)}%`).join(", ")}.`
        : "Inga partier i prognosen ligger inom 0,6 procentenheter från riksdagsspärren."}
    </p>
  `;
}

function renderCoalitions(rows) {
  coalitionPresets.innerHTML = coalitionOptions.map((option) => {
    const totals = coalitionTotals(rows, option.parties);
    const difference = totals.forecast - totals.raw;
    return `
      <button type="button" data-parties="${option.parties.join(",")}" title="Använd som egen konstellation">
        <strong>${option.name}</strong>
        <span>Prognos ${percent.format(totals.forecast)}% ${uncertaintyLabel(totals.uncertainty)}</span>
        <small>Av räknade röster ${percent.format(totals.raw)}%. Skillnad <b class="${differenceClass(difference)}">${signed(difference)}</b>.</small>
      </button>
    `;
  }).join("");
  coalitionPresets.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      selectedCoalition = new Set(button.dataset.parties.split(","));
      renderCoalitions(rows);
    });
  });

  coalitionParties.innerHTML = Object.entries(payload.parties).map(([party, meta]) => `
    <button type="button" aria-pressed="${selectedCoalition.has(party)}" data-party="${party}" title="${meta.name}">
      <i style="background:${meta.color}"></i>${party}
    </button>
  `).join("");
  coalitionParties.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      if (selectedCoalition.has(button.dataset.party)) {
        selectedCoalition.delete(button.dataset.party);
      } else {
        selectedCoalition.add(button.dataset.party);
      }
      renderCoalitions(rows);
    });
  });

  const chosen = [...selectedCoalition];
  const totals = coalitionTotals(rows, chosen);
  const difference = totals.forecast - totals.raw;
  coalitionResult.innerHTML = `
    <h3>Vald konstellation</h3>
    <strong>${partyLabel(chosen)}</strong>
    <div>
      <span>Prognos</span>
      <b>${percent.format(totals.forecast)}%</b>
    </div>
    <div>
      <span>Av räknade röster</span>
      <b>${percent.format(totals.raw)}%</b>
    </div>
    <div>
      <span>Skillnad prognos/räkning</span>
      <b class="${differenceClass(difference)}">${signed(difference)}</b>
    </div>
    <div>
      <span>Osäkerhet</span>
      <b>${uncertaintyLabel(totals.uncertainty)}</b>
    </div>
    <p class="coalition-result-note">Skillnaden visar hur mycket prognosen avviker från den faktiska räkningen i samma läge. Osäkerheten visas som en indikator för hela konstellationen, inte hoplagd parti för parti.</p>
  `;
  renderMandateIndicator(rows);
}

function renderTabs() {
  partyTabs.innerHTML = Object.entries(payload.parties).map(([party, meta]) => `
    <button type="button" role="tab" aria-selected="${party === focusParty}" data-party="${party}" title="${meta.name}">
      <i style="background:${meta.color}"></i>${party}
    </button>
  `).join("");
  partyTabs.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      focusParty = button.dataset.party;
      renderTimeReplay();
    });
  });
}

function countyMoves(counted, party) {
  return [...groupBy(counted, (district) => district.county).entries()].map(([county, districts]) => {
    const current = sumDistricts(districts, "valid22", "votes22");
    const base = sumDistricts(districts, "valid18", "votes18");
    return {
      county,
      districts: districts.length,
      votes: current.valid,
      swing: swing(current, base, party),
      now: share(current, party),
      then: share(base, party),
    };
  }).filter((county) => county.votes >= 1200)
    .sort((a, b) => Math.abs(b.swing) - Math.abs(a.swing));
}

function districtMove(district) {
  const now = district.votes22[focusParty] / district.valid22 * 100;
  const then = district.votes18[focusParty] / district.valid18 * 100;
  return { district, now, then, swing: now - then };
}

function renderSignals(counted) {
  const countyRows = countyMoves(counted, focusParty).slice(0, 6);
  const districtRows = counted
    .map(districtMove)
    .filter((row) => row.district.kind === "valdistrikt" && row.district.valid22 >= 250 && row.district.valid18 >= 250)
    .sort((a, b) => Math.abs(b.swing) - Math.abs(a.swing))
    .slice(0, 7);

  countySignals.innerHTML = countyRows.map((row) => `
    <div class="signal">
      <strong>${row.county}</strong>
      <span class="${row.swing >= 0 ? "rise" : "fall"}">${focusParty} ${signed(row.swing)}</span>
      <small>${row.districts} jämförelseområden inne, från ${percent.format(row.then)}% förra valet till ${percent.format(row.now)}% i aktuellt val</small>
    </div>
  `).join("");
  districtSignals.innerHTML = districtRows.map((row) => `
    <div class="signal">
      <strong>${row.district.municipality}</strong>
      <span class="${row.swing >= 0 ? "rise" : "fall"}">${focusParty} ${signed(row.swing)}</span>
      <small>${row.district.name}, ${row.district.historicProfile}, från ${percent.format(row.then)}% förra valet till ${percent.format(row.now)}% i aktuellt val</small>
    </div>
  `).join("");
}

function sourceTags(sourceMix) {
  const order = ["kommuntyp + profil", "kommuntyp", "huvudgrupp + profil", "huvudgrupp", "historisk profil", "län", "riket"];
  return order.filter((source) => sourceMix.sources.has(source));
}

function methodExplainer(sourceMix) {
  if (!sourceMix.total) {
    return `<div class="method-explainer"><small>Ingen prognosdel återstår i den här vyn. Tabellen visar räknat jämförelseunderlag.</small></div>`;
  }
  const similarShare = sourceMix.stratified / sourceMix.total * 100;
  const fallbackShare = Math.max(0, 100 - similarShare);
  const labels = sourceTags(sourceMix).map((source) => {
    if (source === "kommuntyp + profil") return "kommuntyp och tidigare röstmönster";
    if (source === "huvudgrupp + profil") return "bred kommungrupp och tidigare röstmönster";
    if (source === "historisk profil") return "tidigare röstmönster";
    if (source === "riket") return "rikstrend";
    return source;
  });
  return `
    <div class="method-explainer">
      <strong>Så byggs prognosen här</strong>
      <div class="method-meter" aria-hidden="true"><b style="width:${similarShare}%"></b></div>
      <small>${percent.format(similarShare)}% av kvarvarande jämförelseunderlag får en smalare jämförelse. ${percent.format(fallbackShare)}% behöver en bredare jämförelse. Aktuella lager: ${labels.join(", ")}.</small>
    </div>
  `;
}

function hybridNote(result) {
  if (result.blendWeight < .1) {
    return "Huvudprognosen bygger här på viktad jämförelse mot förra valet.";
  }
  const localShare = result.neighborMix.total ? result.neighborMix.local / result.neighborMix.total * 100 : 0;
  return `Huvudprognosen väger också in lokal jämförelse för kvarvarande områden. ${percent.format(localShare)}% av kvarvarande underlag har lokal jämförelse.`;
}

function renderFocus(result) {
  const row = result.rows.find((party) => party.party === focusParty);
  const now = share(result.current, focusParty);
  const then = share(result.baseline, focusParty);
  focusPanel.innerHTML = `
    <div class="focus-number">
      <span>${row.name}</span>
      <strong>${signed(row.delta)} <em>procentenheter</em></strong>
    </div>
    ${confidenceBadge(result.confidence)}
    <p>I hittills räknade jämförelseområden ligger ${row.name} på ${percent.format(now)}% i aktuellt val, mot ${percent.format(then)}% i samma områden förra valet.</p>
    <p>Prognosen pekar mot ${percent.format(row.forecast)}%, med osäkerhet ${uncertaintyLabel(row.uncertainty)}. ${result.confidence.note}</p>
    <p class="quiet">${hybridNote(result)} Sena röster återstår.</p>
    ${methodExplainer(result.sourceMix)}
  `;
}

function renderRadioLine(result) {
  const moves = [...result.rows].sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
  const leader = result.rows[0];
  const move = moves[0];
  const runnerUp = result.rows[1];
  const tido = coalitionTotals(result.rows, coalitionOptions[0].parties);
  const opposition = coalitionTotals(result.rows, coalitionOptions[1].parties);
  const blockLeader = tido.forecast >= opposition.forecast ? coalitionOptions[0] : coalitionOptions[1];
  const blockRunner = tido.forecast >= opposition.forecast ? coalitionOptions[1] : coalitionOptions[0];
  const blockLeadTotals = tido.forecast >= opposition.forecast ? tido : opposition;
  const blockRunnerTotals = tido.forecast >= opposition.forecast ? opposition : tido;
  radioLine.innerHTML = `
    ${confidenceBadge(result.confidence)}
    <p>Prognosen pekar mot ett övertag för <strong>${blockLeader.name}</strong>: ${percent.format(blockLeadTotals.forecast)}% med osäkerhet ${uncertaintyLabel(blockLeadTotals.uncertainty)}, mot ${blockRunner.name} på ${percent.format(blockRunnerTotals.forecast)}%.</p>
    <p><strong>${leader.name}</strong> ser ut att bli största parti på ${percent.format(leader.forecast)}%, före ${runnerUp.name} på ${percent.format(runnerUp.forecast)}%.</p>
    <p>Den tydligaste rörelsen i de räknade jämförelseområdena är <strong>${move.name}</strong>: ${signed(move.delta)} procentenheter jämfört med förra valet.</p>
    <p class="quiet">Av räknade röster omfattar jämförelseunderlaget ${integer.format(result.current.valid)} giltiga röster i aktuellt val. Det är observationen; prognosen är tolkningsstödet. ${hybridNote(result)}</p>
  `;
}

function countyResult(counted, uncounted, model) {
  const countyCounted = counted.filter((district) => district.county === selectedCounty);
  const countyUncounted = uncounted.filter((district) => district.county === selectedCounty);
  return {
    counted: countyCounted,
    uncounted: countyUncounted,
    forecast: forecastRows(countyCounted, countyUncounted, model),
  };
}

function renderCountyOptions() {
  const counties = [...new Set(payload.districts.map((district) => district.county))].sort((a, b) => a.localeCompare(b, "sv"));
  if (!counties.includes(selectedCounty)) {
    selectedCounty = counties[0];
  }
  countySelect.innerHTML = counties.map((county) => `
    <option value="${county}" ${county === selectedCounty ? "selected" : ""}>${county}</option>
  `).join("");
  countySelect.addEventListener("change", () => {
    selectedCounty = countySelect.value;
    renderTimeReplay();
  });
}

function describeMove(row) {
  if (Math.abs(row.delta) < .35) {
    return `${row.name} ligger ungefär still`;
  }
  return `${row.name} ${row.delta > 0 ? "går fram" : "tappar"} ${percent.format(Math.abs(row.delta))} procentenheter jämfört med förra valet`;
}

function countyProgress(counted, uncounted) {
  const totalAreas = counted.length + uncounted.length;
  const localVotes = sumDistricts(counted, "valid22", "votes22").valid;
  const previousVotes = sumDistricts([...counted, ...uncounted], "valid18", "votes18").valid;
  const waitingRests = uncounted
    .filter((district) => district.kind === "kommunrest")
    .sort((a, b) => b.valid22 - a.valid22);
  return {
    countedAreas: counted.length,
    localVotes,
    previousVotes,
    totalAreas,
    waitingRests,
  };
}

function renderCounty(counted, uncounted, model) {
  const county = countyResult(counted, uncounted, model);
  const result = county.forecast;
  const progress = countyProgress(county.counted, county.uncounted);
  const moves = [...result.rows].sort((a, b) => b.delta - a.delta);
  const positive = moves[0];
  const negative = moves[moves.length - 1];
  const largestRest = progress.waitingRests[0];
  renderRows(countyTable, result.rows, result.confidence);
  countyStory.innerHTML = `
    <section class="county-progress" aria-label="Lokalt jämförelseunderlag">
      <h3>Lokalt jämförelseunderlag</h3>
      <div>
        <strong>${progress.countedAreas} / ${progress.totalAreas}</strong>
        <span>områden inne</span>
      </div>
      <div>
        <strong>${integer.format(progress.localVotes)}</strong>
        <span>röster inne i aktuellt val</span>
      </div>
      <p>Som fingervisning: förra valet räknades ${integer.format(progress.previousVotes)} giltiga röster i samma länsunderlag.</p>
      ${progress.waitingRests.length ? `<p><b>${progress.waitingRests.length}</b> kommunrester väntar på att bli kompletta.${largestRest ? ` Störst kvar är ${largestRest.municipality} med ${integer.format(largestRest.valid22)} röster i 2022-underlaget.` : ""}</p>` : `<p>Inga kommunrester väntar i länet i det här läget.</p>`}
    </section>
    ${confidenceBadge(result.confidence)}
    <p>I <strong>${selectedCounty}</strong> ser vi att ${describeMove(positive)}, medan ${describeMove(negative)} i räknade jämförelseområden.</p>
    <p>Av räknade röster bygger länsbilden på ${integer.format(result.current.valid)} giltiga röster i jämförelseunderlaget. Länsprognosens osäkerhet är ${uncertaintyLabel(result.uncertainty)}.</p>
    ${result.sourceMix.total ? `<p>För det som återstår använder prognosen jämförelser med liknande kommuner och tidigare röstmönster när länets eget räknade underlag inte räcker.</p>` : ""}
    ${methodExplainer(result.sourceMix)}
  `;
}

function renderTimeReplay() {
  const cutoff = currentCutoff();
  const { counted, uncounted } = splitByTime(cutoff.ms);
  const officialCounted = payload.currentDistricts
    ? splitAreasByTime(payload.currentDistricts, cutoff.ms).counted
    : counted;
  const model = makeModel(counted);
  const result = forecastRows(counted, uncounted, model, officialCounted);
  coverageLabel.textContent = cutoff.isFinal ? "Slutläge" : formatReplayTime(cutoff.ms);
  countedDistricts.textContent = `${integer.format(counted.length)} / ${integer.format(payload.districts.length)}`;
  countedVotes.textContent = integer.format(result.officialCurrent.valid);
  liveUpdated.textContent = payload.sourceUpdatedAt
    ? formatReplayTime(Date.parse(payload.sourceUpdatedAt))
    : (payload.mode === "valmyndigheten-live" ? "Live" : "Replay");
  renderRows(partyTable, result.rows, result.confidence, { showOpinion });
  renderCoalitions(result.rows);
  renderTabs();
  renderFocus(result);
  renderRadioLine(result);
  renderCounty(counted, uncounted, model);
  renderSignals(counted);
}

function applyOpinionReference(reference) {
  if (!reference?.enabled) {
    opinionToggle.closest(".opinion-toggle")?.classList.add("hidden");
    opinionNote.classList.add("hidden");
    showOpinion = false;
    return;
  }
  opinionReference = reference;
  opinionToggle.closest(".opinion-toggle")?.classList.remove("hidden");
  const source = [reference.source, reference.date].filter(Boolean).join(", ");
  opinionNote.innerHTML = `
    <strong>${reference.label || "Opinionsreferens"}</strong>
    <p>${source ? `${source}. ` : ""}Extern redaktionell referens. Ingår inte i prognosen.</p>
  `;
  renderTimeReplay();
}

function loadOpinionReference() {
  fetch("data/opinion-reference.json")
    .then((response) => response.ok ? response.json() : null)
    .then(applyOpinionReference)
    .catch(() => applyOpinionReference(null));
}

function start(data) {
  payload = data;
  if (payload.mode === "valmyndigheten-live") {
    document.querySelector("#mode-pill").textContent = "Live 2026";
    modeNoteText.textContent = "Live-läget läser Valmyndighetens preliminära riksdagsfil via Vallabbets importer. Tabellen visar rapporterade områden jämfört med samma områden förra valet och prognos för återstående jämförbart underlag.";
  }
  setupTimeline();
  coverageInput.addEventListener("input", renderTimeReplay);
  renderCountyOptions();
  renderTimeReplay();
  loadOpinionReference();
}

viewTabs.forEach((button) => {
  button.addEventListener("click", () => {
    viewTabs.forEach((tab) => tab.setAttribute("aria-selected", String(tab === button)));
    viewPanels.forEach((panel) => panel.classList.toggle("hidden", panel.dataset.viewPanel !== button.dataset.view));
  });
});

opinionToggle.addEventListener("change", () => {
  showOpinion = opinionToggle.checked;
  opinionNote.classList.toggle("hidden", !showOpinion);
  renderTimeReplay();
});

function liveDataUrl() {
  const value = new URLSearchParams(location.search).get("live");
  if (!value) return null;
  if (value === "1" || value === "true") return "data/live/current-riksdag.json";
  return value;
}

const liveUrl = liveDataUrl();
if (liveUrl) {
  fetch(liveUrl, { cache: "no-store" })
    .then((response) => response.json())
    .then(start)
    .catch(() => {
      document.body.innerHTML = "<p class='load-error'>Kunde inte läsa live-underlaget.</p>";
    });
} else if (window.RIKSDAG_REPLAY_DATA) {
  start(window.RIKSDAG_REPLAY_DATA);
} else {
  fetch("data/riksdag-2022-replay.json")
    .then((response) => response.json())
    .then(start)
    .catch(() => {
      document.body.innerHTML = "<p class='load-error'>Kunde inte läsa replay-underlaget.</p>";
    });
}
