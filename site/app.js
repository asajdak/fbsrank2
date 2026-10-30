"use strict";

const $ = (id) => document.getElementById(id);
const els = { ranker: $("ranker"), season: $("season"), week: $("week") };
let index;

async function getJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

function fill(select, options, selected) {
  select.replaceChildren(
    ...options.map(({ value, label }) => {
      const opt = new Option(label, value);
      opt.selected = String(value) === String(selected);
      return opt;
    })
  );
}

function seasonEntry() {
  return index.seasons.find((s) => String(s.season) === els.season.value);
}

function fillWeeks(selectLatest) {
  const weeks = seasonEntry().weeks;
  const keep = selectLatest ? null : els.week.value;
  const chosen = weeks.some((w) => String(w.week) === keep) ? keep : weeks[weeks.length - 1].week;
  fill(els.week, weeks.map((w) => ({ value: w.week, label: w.label })), chosen);
}

function cell(text, className) {
  const td = document.createElement("td");
  td.textContent = text;
  if (className) td.className = className;
  return td;
}

function movement(entry, previous) {
  if (!previous) return cell("");
  const before = previous.get(entry.team);
  if (before === undefined || before === entry.rank) return cell("");
  const moved = before - entry.rank;
  return cell(moved > 0 ? `▲${moved}` : `▼${-moved}`, moved > 0 ? "up" : "down");
}

async function render() {
  const ranker = els.ranker.value;
  const season = els.season.value;
  const week = Number(els.week.value);
  const base = `data/${ranker}/${season}`;
  $("status").textContent = "";
  $("description").textContent = index.rankers.find((r) => r.id === ranker).description;

  try {
    const current = await getJSON(`${base}/week-${week}.json`);
    const weeks = seasonEntry().weeks.map((w) => w.week);
    const prevWeek = weeks[weeks.indexOf(week) - 1];
    const prev = prevWeek === undefined ? null : await getJSON(`${base}/week-${prevWeek}.json`);
    const previousRanks = prev && new Map(prev.rankings.map((r) => [r.team, r.rank]));

    const rows = current.rankings.map((r) => {
      const tr = document.createElement("tr");
      const record = `${r.wins}-${r.losses}` + (r.ties ? `-${r.ties}` : "");
      tr.append(cell(r.rank, "num"), movement(r, previousRanks), cell(r.team), cell(r.conference), cell(record), cell(r.rating, "num"));
      return tr;
    });
    document.querySelector("#rankings tbody").replaceChildren(...rows);
  } catch (err) {
    $("status").textContent = `Could not load rankings: ${err.message}`;
  }
}

async function init() {
  try {
    index = await getJSON("data/index.json");
  } catch (err) {
    $("status").textContent = "No data found. Run `python -m fbsrank rank` first.";
    return;
  }
  fill(els.ranker, index.rankers.map((r) => ({ value: r.id, label: r.name })), index.rankers[0].id);
  fill(els.season, index.seasons.map((s) => ({ value: s.season, label: s.season })), index.seasons[0].season);
  fillWeeks(true);

  els.ranker.addEventListener("change", render);
  els.week.addEventListener("change", render);
  els.season.addEventListener("change", () => { fillWeeks(true); render(); });
  render();
}

init();
