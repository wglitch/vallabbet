const coverageInput = document.querySelector("#coverage");
const coverageLabel = document.querySelector("#coverage-label");
const countedDistricts = document.querySelector("#counted-districts");
const countedVotes = document.querySelector("#counted-votes");
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
const percent = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
const integer = new Intl.NumberFormat("sv-SE");

let payload;
let focusParty = "S";
let selectedCounty = "Jämtland";
let showOpinion = false;
let selectedCoalition = new Set(["M", "KD", "L", "SD"]);

const opinionPlaceholder = {
  M: null,
  C: null,
  L: null,
  KD: null,
  S: null,
  V: null,
  MP: null,
  SD: null,
};

const coalitionOptions = [
  { name: "Tidöpartierna", parties: ["M", "KD", "L", "SD"] },
  { name: "S + V + C + MP", parties: ["S", "V", "C", "MP"] },
];

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

function share(total, party) {
  return total.valid ? total[party] / total.valid * 100 : 0;
}

function swing(current, baseline, party) {
  return share(current, party) - share(baseline, party);
}

function signed(value) {
  return `${value > 0 ? "+" : ""}${percent.format(value)}`;
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

function forecastRows(counted, uncounted, model) {
  const current = sumDistricts(counted, "valid22", "votes22");
  const baseline = sumDistricts(counted, "valid18", "votes18");
  const uncountedBaseline = sumDistricts(uncounted, "valid18", "votes18");
  const forecastVotes = {};
  const sourceMix = { total: 0, stratified: 0, sources: new Set() };
  Object.keys(payload.parties).forEach((party) => forecastVotes[party] = current[party]);

  uncounted.forEach((district) => {
    const choice = chooseStratum(model, district);
    sourceMix.total += district.valid18;
    sourceMix.sources.add(choice.source);
    if (choice.source !== "riket") {
      sourceMix.stratified += district.valid18;
    }
    Object.keys(payload.parties).forEach((party) => {
      const districtBase = district.votes18[party] / district.valid18 * 100;
      const delta = swing(choice.stat.current, choice.stat.baseline, party);
      const projectedShare = Math.max(0, districtBase + delta);
      forecastVotes[party] += projectedShare / 100 * district.valid18;
    });
  });

  const forecastScale = current.valid + uncountedBaseline.valid;
  const rows = Object.entries(payload.parties).map(([party, meta]) => ({
    party,
    ...meta,
    raw: share(current, party),
    delta: swing(current, baseline, party),
    forecast: forecastVotes[party] / forecastScale * 100,
  })).sort((a, b) => b.forecast - a.forecast);

  return {
    rows,
    current,
    baseline,
    uncountedBaseline,
    confidence: confidenceFrom({ current }, sourceMix),
    sourceMix,
  };
}

function confidenceBadge(confidence) {
  return `<span class="confidence ${confidence.level}">${confidence.label}</span>`;
}

function renderRows(target, rows, confidence, options = {}) {
  const showOpinionColumn = options.showOpinion === true;
  target.innerHTML = `
    <div class="party-row labels ${showOpinionColumn ? "with-opinion" : ""}">
      <span>Parti</span><span>Just nu</span><span>Förändring</span><span>Prognos</span>${showOpinionColumn ? "<span>Opinion</span>" : ""}
    </div>
    ${rows.map((row) => `
      <div class="party-row ${showOpinionColumn ? "with-opinion" : ""}">
        <span class="party-name"><i style="background:${row.color}"></i>${row.party}</span>
        <span>${percent.format(row.raw)}%</span>
        <span class="${row.delta >= 0 ? "rise" : "fall"}">${signed(row.delta)}</span>
        <strong title="${confidence.label}">${percent.format(row.forecast)}%</strong>
        ${showOpinionColumn ? `<span class="opinion-value">${opinionPlaceholder[row.party] === null ? "Referens" : `${percent.format(opinionPlaceholder[row.party])}%`}</span>` : ""}
        <b style="--fill:${row.forecast}%;--party:${row.color}"></b>
      </div>
    `).join("")}
  `;
}

function coalitionTotals(rows, parties) {
  return rows
    .filter((row) => parties.includes(row.party))
    .reduce((total, row) => ({
      raw: total.raw + row.raw,
      forecast: total.forecast + row.forecast,
    }), { raw: 0, forecast: 0 });
}

function partyLabel(parties) {
  return parties.length ? parties.join(" + ") : "Inga partier valda";
}

function renderCoalitions(rows) {
  coalitionPresets.innerHTML = coalitionOptions.map((option) => {
    const totals = coalitionTotals(rows, option.parties);
    return `
      <button type="button" data-parties="${option.parties.join(",")}" title="Använd som egen konstellation">
        <strong>${option.name}</strong>
        <span>Prognos ${percent.format(totals.forecast)}%</span>
        <small>Just nu ${percent.format(totals.raw)}%</small>
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
  coalitionResult.innerHTML = `
    <h3>Vald konstellation</h3>
    <strong>${partyLabel(chosen)}</strong>
    <div>
      <span>Prognosandel</span>
      <b>${percent.format(totals.forecast)}%</b>
    </div>
    <div>
      <span>Just nu</span>
      <b>${percent.format(totals.raw)}%</b>
    </div>
  `;
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
      render();
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
      <small>${row.districts} jämförelseområden inne, ${percent.format(row.then)}% till ${percent.format(row.now)}%</small>
    </div>
  `).join("");
  districtSignals.innerHTML = districtRows.map((row) => `
    <div class="signal">
      <strong>${row.district.municipality}</strong>
      <span class="${row.swing >= 0 ? "rise" : "fall"}">${focusParty} ${signed(row.swing)}</span>
      <small>${row.district.name}, ${row.district.historicProfile}, ${percent.format(row.then)}% till ${percent.format(row.now)}%</small>
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
    <p>I hittills räknade jämförelseområden ligger ${row.name} på ${percent.format(now)}%, mot ${percent.format(then)}% i samma områden 2018.</p>
    <p>Prognosen pekar mot ${percent.format(row.forecast)}%. ${result.confidence.note}</p>
    ${methodExplainer(result.sourceMix)}
  `;
}

function renderRadioLine(result) {
  const moves = [...result.rows].sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
  const leader = result.rows[0];
  const move = moves[0];
  const runnerUp = result.rows[1];
  radioLine.innerHTML = `
    ${confidenceBadge(result.confidence)}
    <p>Prognosen sätter <strong>${leader.name}</strong> först på ${percent.format(leader.forecast)}%, före ${runnerUp.name} på ${percent.format(runnerUp.forecast)}%.</p>
    <p>Den tydligaste rörelsen i de räknade jämförelseområdena är <strong>${move.name}</strong>: ${signed(move.delta)} procentenheter mot 2018.</p>
    <p class="quiet">Just nu omfattar jämförelseunderlaget ${integer.format(result.current.valid)} giltiga röster. Det är observationen; prognosen är tolkningsstödet.</p>
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
    render();
  });
}

function describeMove(row) {
  if (Math.abs(row.delta) < .35) {
    return `${row.name} ligger ungefär still`;
  }
  return `${row.name} ${row.delta > 0 ? "går fram" : "tappar"} ${percent.format(Math.abs(row.delta))} procentenheter`;
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
        <span>röster inne</span>
      </div>
      <p>Som fingervisning: förra valet räknades ${integer.format(progress.previousVotes)} giltiga röster i samma länsunderlag.</p>
      ${progress.waitingRests.length ? `<p><b>${progress.waitingRests.length}</b> kommunrester väntar på att bli kompletta.${largestRest ? ` Störst kvar är ${largestRest.municipality} med ${integer.format(largestRest.valid22)} röster i 2022-underlaget.` : ""}</p>` : `<p>Inga kommunrester väntar i länet i det här läget.</p>`}
    </section>
    ${confidenceBadge(result.confidence)}
    <p>I <strong>${selectedCounty}</strong> ser vi att ${describeMove(positive)}, medan ${describeMove(negative)} i räknade jämförelseområden.</p>
    <p>Just nu bygger länsbilden på ${integer.format(result.current.valid)} giltiga röster i jämförelseunderlaget.</p>
    ${result.sourceMix.total ? `<p>För det som återstår använder prognosen jämförelser med liknande kommuner och tidigare röstmönster när länets eget räknade underlag inte räcker.</p>` : ""}
    ${methodExplainer(result.sourceMix)}
  `;
}

function render() {
  const target = Number(coverageInput.value);
  const take = Math.max(1, Math.round(payload.districts.length * target / 100));
  const counted = payload.districts.slice(0, take);
  const uncounted = payload.districts.slice(take);
  const model = makeModel(counted);
  const result = forecastRows(counted, uncounted, model);
  coverageLabel.textContent = `${target}% av jämförelseunderlaget`;
  countedDistricts.textContent = `${integer.format(counted.length)} / ${integer.format(payload.districts.length)}`;
  countedVotes.textContent = integer.format(result.current.valid);
  renderRows(partyTable, result.rows, result.confidence, { showOpinion });
  renderCoalitions(result.rows);
  renderTabs();
  renderFocus(result);
  renderRadioLine(result);
  renderCounty(counted, uncounted, model);
  renderSignals(counted);
}

function start(data) {
  payload = data;
  coverageInput.addEventListener("input", render);
  renderCountyOptions();
  render();
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
  render();
});

if (window.RIKSDAG_REPLAY_DATA) {
  start(window.RIKSDAG_REPLAY_DATA);
} else {
  fetch("data/riksdag-2022-replay.json")
    .then((response) => response.json())
    .then(start)
    .catch(() => {
      document.body.innerHTML = "<p class='load-error'>Kunde inte läsa replay-underlaget.</p>";
    });
}
