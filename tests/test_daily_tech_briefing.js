const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const workflow = JSON.parse(fs.readFileSync(
  path.join(__dirname, "../workflows/daily-tech-briefing.json"), "utf8"));
const code = workflow.nodes.find(node => node.id === "format-report").parameters.jsCode;
const requestNode = workflow.nodes.find(node => node.id === "build-request");
const historyNode = workflow.nodes.find(node => node.id === "slack-history");
assert.equal(historyNode.parameters.returnAll, false);
assert.equal(historyNode.parameters.limit, 100);
assert.match(requestNode.parameters.jsCode, /task\.length > 32000/);
assert.match(workflow.nodes.find(node => node.id === "generate").parameters.jsonBody, /max_output_tokens:1200/);
assert.match(requestNode.parameters.jsCode, /NON VERIFICATA/);
assert.match(requestNode.parameters.jsCode, /Non imporre calcoli aritmetici/);
assert.match(requestNode.parameters.jsCode, /non scartare una notizia.*contraddice o non la conferma/i);
assert.equal(workflow.nodes.find(node => node.type === "n8n-nodes-base.scheduleTrigger").parameters.rule.interval[0].triggerAtHour, 8);
assert.equal(workflow.settings.timezone, "Europe/Rome");
assert.equal(workflow.settings.availableInMCP, true);
assert.equal(workflow.nodes.find(node => node.id === "load-prompt").parameters.workflowId.value, "pocPromptLoader20261107");
assert.equal(workflow.nodes.find(node => node.id === "e7963091-4991-4128-96fc-0f0ef89acded").parameters.workflowId.value, "iY736K0RGUKznWpl");


function run(report, url = "https://example.com/2026/story", annotationUrl = url, priorMessages = []) {
  const response = {
    output_text: report,
    output: [
      { type: "message", content: [{
        type: "output_text", text: report,
        annotations: annotationUrl ? [{ type: "url_citation", url: annotationUrl }] : [],
      }] },
      { type: "web_search_call", action: { sources: [{ url }] } },
    ],
  };
  const context = {
    $json: response,
    $: name => {
      assert.equal(name, "Leggi storico del canale");
      return { all: () => priorMessages.map(text => ({ json: { user: "U0BP05KJACA", text } })) };
    },
  };
  return vm.runInNewContext("(function(){" + code + "\n})()", context)[0].json;
}

const verified = "NEWS: Lancio prodotto | FACT: La fonte conferma il lancio | STATUS: VERIFICATA | URL: https://example.com/2026/story | WHY: Novità rilevante";
const unverified = "NEWS: Dato consegne | FACT: La fonte riporta 621 consegne; il totale di 870 non è confermato | STATUS: NON VERIFICATA | URL: https://example.com/2026/story | WHY: Il dato annuale resta incerto";
assert.match(run(verified).report, /_Stato: VERIFICATA_/);
assert.match(run(verified).report, /<https:\/\/example\.com\/2026\/story\|Fonte>/);
assert.match(run(unverified).report, /_Stato: NON VERIFICATA_/);
assert.match(run(unverified).report, /totale di 870 non è confermato/i);
assert.match(run(unverified).report, /<https:\/\/example\.com\/2026\/story\|Fonte>/);
const trackedCitation = "https://example.com/2026/story?utm_source=openai";
assert.match(run(verified, "https://example.com/2026/story", trackedCitation).report, /_Stato: VERIFICATA_/);
assert.match(
  run(verified, "https://example.com/2026/story", null).report,
  /<https:\/\/example\.com\/2026\/story\|Fonte>/,
  "a web_search result URL is sufficient when no inline annotation is returned",
);
assert.throws(
  () => run(verified, "https://example.com/2026/other", null),
  /missing a web_search URL citation/,
  "the story URL must match a web_search result",
);
assert.throws(
  () => run(verified, "https://example.com/2026/story/", null),
  /missing a web_search URL citation/,
  "a trailing slash is part of the source path",
);
const apId = "fe9a92cc7631b58fd630ccebf9692f6c";
const apStory = verified.replace("https://example.com/2026/story", `https://apnews.com/article/booker-prize-fiction-winner-${apId}`);
assert.match(
  run(apStory, `https://apnews.com/article/${apId}`, null).report,
  new RegExp(`<https://apnews\\.com/article/${apId}\\|Fonte>`),
  "a source result's canonical AP URL replaces a matching slugged article URL",
);
assert.throws(
  () => run(verified.replace("https://example.com/2026/story", "https://user@example.com/2026/story"), "https://user@example.com/2026/story", "https://user@example.com/2026/story"),
  /HTTPS link/,
  "source links must not contain credentials",
);

const archive = unverified.replace("https://example.com/2026/story", "https://example.com/news/2026/11");
assert.match(run(archive, "https://example.com/news/2026/11").report, /_Stato: NON VERIFICATA_/);
const unsupportedNumber = "NEWS: Dato | FACT: Airbus had delivered 999 aircraft by October | STATUS: NON VERIFICATA | URL: https://example.com/2026/story | WHY: Impatto";
assert.match(run(unsupportedNumber).report, /999 aircraft/);
assert.match(run(unsupportedNumber).report, /_Stato: NON VERIFICATA_/);

const marker = "_Briefing tech quotidiano · ref:daily-tech-briefing_";
const legacyPosted = "• *Lancio prodotto* — La fonte conferma il lancio\n  <https://example.com/2026/story|Fonte>\n  _Perché conta: Novità rilevante_\n\n" + marker;
const statusPosted = "• *Lancio prodotto* — La fonte conferma il lancio\n  _Stato: VERIFICATA_\n  <https://example.com/2026/story|Fonte>\n  _Perché conta: Novità rilevante_\n\n" + marker;
assert.equal(run(verified, undefined, undefined, [legacyPosted]).deduplicatedCount, 1);
assert.equal(run(verified, undefined, undefined, [statusPosted]).deduplicatedCount, 1);

assert.throws(
  () => run(verified.replace("STATUS: VERIFICATA", "STATUS: DUBBIA")),
  /one to three complete/,
  "only the two agreed status values are accepted",
);
assert.throws(
  () => run(verified.replace("https://example.com/2026/story", "http://example.com/story"), "http://example.com/story"),
  /HTTPS URL/,
  "source links must use HTTPS",
);
assert.throws(
  () => run("Ecco il briefing.\n" + verified),
  /one to three complete/,
  "unstructured preambles are rejected",
);
assert.throws(
  () => run([verified, verified, verified, verified].join("\n")),
  /one to three complete/,
  "more than three stories are rejected",
);
assert.match(run("NESSUN AGGIORNAMENTO — nessuna azione richiesta").report, /NESSUN AGGIORNAMENTO/);
assert.throws(
  () => run("NESSUN AGGIORNAMENTO — nessuna azione richiesta\n" + verified),
  /No-update response contains extra claims/,
);

assert.throws(
  () => vm.runInNewContext("(function(){" + requestNode.parameters.jsCode + "\n})()", {
    $: () => ({ first: () => ({ json: {
      contratto_comune: "x".repeat(32000), prompt: "", titolo: "briefing",
    } }) }),
  }),
  /32000-character input cap/,
  "oversized prompt data fails before the LiteLLM request",
);

console.log("PASS: verified/unverified labels and source links; format, citations, HTTPS, limits, and no-update behavior");
