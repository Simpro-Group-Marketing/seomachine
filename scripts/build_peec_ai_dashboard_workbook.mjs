import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repo = "C:/Users/patrick.grueschow/Desktop/Repos/seomachine-main";
const sourceDir = path.join(repo, "research", "peec-ai-dashboard-2026-09-18");
const outputDir = path.join(repo, "outputs", "peec-ai-dashboard-2026-09-18");
const outputPath = path.join(outputDir, "peec-ai-dashboard-2026-09-18.xlsx");

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];

    if (inQuotes) {
      if (char === '"' && next === '"') {
        field += '"';
        i += 1;
      } else if (char === '"') {
        inQuotes = false;
      } else {
        field += char;
      }
      continue;
    }

    if (char === '"') {
      inQuotes = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (char !== "\r") {
      field += char;
    }
  }

  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }

  if (rows.length && rows[0][0]?.charCodeAt(0) === 0xfeff) {
    rows[0][0] = rows[0][0].slice(1);
  }
  return rows;
}

function csvObjects(rows) {
  const headers = rows[0];
  return rows.slice(1).filter((row) => row.some((cell) => cell !== "")).map((row) => {
    const item = {};
    headers.forEach((header, index) => {
      item[header] = row[index] ?? "";
    });
    return item;
  });
}

function numberValue(value) {
  if (value === "" || value === null || value === undefined) {
    return 0;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}

function percentPoint(value) {
  return numberValue(value);
}

function dateValue(value) {
  const [year, month, day] = String(value).split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

function safeCell(value) {
  if (value === null || value === undefined) {
    return "";
  }
  return value;
}

function sheetRangeFor(rows, cols) {
  const letters = [];
  let number = cols;
  while (number > 0) {
    const modulo = (number - 1) % 26;
    letters.unshift(String.fromCharCode(65 + modulo));
    number = Math.floor((number - modulo) / 26);
  }
  return `A1:${letters.join("")}${rows}`;
}

function writeTable(sheet, anchorRow, anchorCol, headers, rows, tableName) {
  const matrix = [headers, ...rows];
  const range = sheet.getRangeByIndexes(anchorRow, anchorCol, matrix.length, headers.length);
  range.values = matrix;
  const tableRange = `${range.address.split("!").pop()}`;
  const table = sheet.tables.add(tableRange, true, tableName);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  return range;
}

function formatHeader(range) {
  range.format = {
    fill: "#1F2937",
    font: { bold: true, color: "#FFFFFF", name: "Arial" },
  };
  range.format.verticalAlignment = "center";
}

function formatTitle(sheet, title, subtitle) {
  sheet.showGridLines = false;
  sheet.getRange("A1").values = [[title]];
  sheet.getRange("A1").format.font = { bold: true, size: 16, name: "Arial", color: "#111827" };
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange("A2").format.font = { italic: true, size: 10, name: "Arial", color: "#4B5563" };
  sheet.getRange("A3:H3").format.borders = {
    bottom: { style: "thin", color: "#D1D5DB" },
  };
}

function autofit(sheet, rangeAddress) {
  const range = sheet.getRange(rangeAddress);
  range.format.font = { name: "Arial", size: 10 };
  range.format.autofitColumns();
  range.format.autofitRows();
}

const summaryCsv = parseCsv(await fs.readFile(path.join(sourceDir, "peec-dashboard-summary.csv"), "utf8"));
const evidenceCsv = parseCsv(await fs.readFile(path.join(sourceDir, "peec-url-channel-evidence.csv"), "utf8"));
const manifest = JSON.parse(await fs.readFile(path.join(sourceDir, "source-manifest.json"), "utf8"));
const currentRaw = JSON.parse(await fs.readFile(path.join(sourceDir, "raw", "peec-current.json"), "utf8"));
const priorRaw = JSON.parse(await fs.readFile(path.join(sourceDir, "raw", "peec-prior.json"), "utf8"));

const summaryObjects = csvObjects(summaryCsv);
const evidenceObjects = csvObjects(evidenceCsv);
const allSummary = summaryObjects.find((row) => row.segment === "ALL");

const workbook = Workbook.create();

const dashboard = workbook.worksheets.add("Dashboard");
formatTitle(
  dashboard,
  "PEEC AI dashboard",
  "Simpro PEEC project. Current window 2026-09-11 to 2026-09-18; prior window 2026-09-03 to 2026-09-10."
);

const kpiRows = [
  ["Metric", "Prior", "Current", "Change", "Change %"],
  [
    "Retrievals",
    numberValue(allSummary.retrieval_count_prior),
    numberValue(allSummary.retrieval_count_current),
    numberValue(allSummary.retrieval_count_delta),
    numberValue(allSummary.retrieval_count_pct_delta) / 100,
  ],
  [
    "Citations",
    numberValue(allSummary.citation_count_prior),
    numberValue(allSummary.citation_count_current),
    numberValue(allSummary.citation_count_delta),
    numberValue(allSummary.citation_count_pct_delta) / 100,
  ],
  [
    "Citation rate",
    numberValue(allSummary.citation_rate_prior),
    numberValue(allSummary.citation_rate_current),
    numberValue(allSummary.citation_rate_delta),
    "",
  ],
  [
    "Matched URL/channel rows",
    numberValue(allSummary.matched_rows_prior),
    numberValue(allSummary.matched_rows_current),
    numberValue(allSummary.matched_rows_current) - numberValue(allSummary.matched_rows_prior),
    "",
  ],
];
dashboard.getRange("A5:E9").values = kpiRows;
formatHeader(dashboard.getRange("A5:E5"));
dashboard.getRange("B6:D7").format.numberFormat = "#,##0";
dashboard.getRange("E6:E7").format.numberFormat = "0.0%";
dashboard.getRange("B8:D8").format.numberFormat = "0.00%";
dashboard.getRange("B9:D9").format.numberFormat = "#,##0";

const channelHeaders = [
  "Channel",
  "Ret prior",
  "Ret current",
  "Ret change %",
  "Cit prior",
  "Cit current",
  "Cit change %",
  "Cit rate current",
];
const channelRows = summaryObjects
  .filter((row) => row.segment !== "ALL")
  .sort((a, b) => a.segment.localeCompare(b.segment))
  .map((row) => [
    row.segment,
    numberValue(row.retrieval_count_prior),
    numberValue(row.retrieval_count_current),
    numberValue(row.retrieval_count_pct_delta) / 100,
    numberValue(row.citation_count_prior),
    numberValue(row.citation_count_current),
    numberValue(row.citation_count_pct_delta) / 100,
    numberValue(row.citation_rate_current),
  ]);
dashboard.getRange("A12:H15").values = [channelHeaders, ...channelRows];
formatHeader(dashboard.getRange("A12:H12"));
dashboard.getRange("B13:C15").format.numberFormat = "#,##0";
dashboard.getRange("D13:D15").format.numberFormat = "0.0%";
dashboard.getRange("E13:F15").format.numberFormat = "#,##0";
dashboard.getRange("G13:H15").format.numberFormat = "0.0%";
dashboard.getRange("A12:H12").format.wrapText = true;
dashboard.getRange("A:A").format.columnWidthPx = 210;
dashboard.getRange("B:H").format.columnWidthPx = 118;

dashboard.getRange("A18").values = [["Source boundary"]];
dashboard.getRange("A18").format.font = { bold: true, name: "Arial", color: "#111827" };
dashboard.getRange("A19:H20").merge();
dashboard.getRange("A19").values = [[
  "PEEC proves monitored retrieval and citation activity inside the Simpro PEEC project for the configured channels and windows. Do not use this workbook to claim traffic, leads, revenue, rankings, or conversion impact.",
]];
dashboard.getRange("A19").format.wrapText = true;
dashboard.getRange("A19").format.font = { name: "Arial", size: 10, color: "#374151" };
dashboard.freezePanes.freezeRows(5);
autofit(dashboard, "A1:H20");
dashboard.getRange("A:A").format.columnWidthPx = 210;
dashboard.getRange("B:H").format.columnWidthPx = 118;
dashboard.getRange("A19:H20").format.rowHeightPx = 54;

const summarySheet = workbook.worksheets.add("Channel summary");
formatTitle(summarySheet, "Channel summary", "Current and prior PEEC metrics by active model channel.");
const summaryHeaders = summaryCsv[0];
const summaryRows = summaryCsv.slice(1).map((row) =>
  row.map((cell, index) => (index === 0 ? cell : numberValue(cell)))
);
writeTable(summarySheet, 4, 0, summaryHeaders, summaryRows, "PeecChannelSummary");
formatHeader(summarySheet.getRangeByIndexes(4, 0, 1, summaryHeaders.length));
summarySheet.getRange("B6:M9").format.numberFormat = "#,##0.0000";
summarySheet.freezePanes.freezeRows(5);
autofit(summarySheet, sheetRangeFor(summaryRows.length + 5, summaryHeaders.length));

const evidenceSheet = workbook.worksheets.add("URL channel evidence");
formatTitle(evidenceSheet, "URL channel evidence", "Normalized PEEC URL and channel rows with zero-filled missing period rows.");
const evidenceHeaders = evidenceCsv[0];
const numericEvidence = new Set([
  "retrieval_count_current",
  "retrieval_count_prior",
  "retrieval_count_delta",
  "retrieval_count_pct_delta",
  "citation_count_current",
  "citation_count_prior",
  "citation_count_delta",
  "citation_count_pct_delta",
  "citation_rate_current",
  "citation_rate_prior",
  "citation_rate_delta",
  "raw_row_count_current",
  "raw_row_count_prior",
]);
const dateEvidence = new Set(["current_start", "current_end", "prior_start", "prior_end"]);
const evidenceRows = evidenceObjects.map((row) =>
  evidenceHeaders.map((header) => {
    if (numericEvidence.has(header)) return numberValue(row[header]);
    if (dateEvidence.has(header)) return dateValue(row[header]);
    return safeCell(row[header]);
  })
);
writeTable(evidenceSheet, 4, 0, evidenceHeaders, evidenceRows, "PeecUrlChannelEvidence");
formatHeader(evidenceSheet.getRangeByIndexes(4, 0, 1, evidenceHeaders.length));
evidenceSheet.freezePanes.freezeRows(5);
evidenceSheet.freezePanes.freezeColumns(2);
const evidenceUsedRange = sheetRangeFor(evidenceRows.length + 5, evidenceHeaders.length);
evidenceSheet.getRange("F6:I6806").format.numberFormat = "yyyy-mm-dd";
evidenceSheet.getRange("J6:Q6806").format.numberFormat = "#,##0.0000";
evidenceSheet.getRange("R6:T6806").format.numberFormat = "0.0000";
autofit(evidenceSheet, evidenceUsedRange);
evidenceSheet.getRange("A:A").format.columnWidthPx = 270;
evidenceSheet.getRange("B:B").format.columnWidthPx = 270;
evidenceSheet.getRange("Y:Z").format.columnWidthPx = 280;

const manifestSheet = workbook.worksheets.add("Manifest");
formatTitle(manifestSheet, "Source manifest", "Run metadata and validation copied from source-manifest.json.");
const manifestRows = [
  ["Field", "Value"],
  ["Schema version", manifest.schema_version],
  ["Run date", manifest.run_date],
  ["Generated at", manifest.generated_at],
  ["Project", manifest.project.name],
  ["Project ID", manifest.project.project_id],
  ["Current window", `${manifest.windows.current.start_date} to ${manifest.windows.current.end_date}`],
  ["Prior window", `${manifest.windows.prior.start_date} to ${manifest.windows.prior.end_date}`],
  ["Current raw channel rows", manifest.row_counts.current_raw_channel_rows],
  ["Prior raw channel rows", manifest.row_counts.prior_raw_channel_rows],
  ["Evidence rows", manifest.row_counts.evidence_rows],
  ["Zero-filled current rows", manifest.row_counts.zero_filled_current_rows],
  ["Zero-filled prior rows", manifest.row_counts.zero_filled_prior_rows],
  ["PEEC report", manifest.source_tools.peec.report],
  ["PEEC MCP URL", manifest.source_tools.peec.url],
  ["Source boundary", manifest.proof_boundary.join(" ")],
];
manifestSheet.getRange(`A5:B${manifestRows.length + 4}`).values = manifestRows;
formatHeader(manifestSheet.getRange("A5:B5"));
manifestSheet.getRange("B6:B20").format.wrapText = true;
manifestSheet.getRange("A:A").format.columnWidthPx = 210;
manifestSheet.getRange("B:B").format.columnWidthPx = 620;
manifestSheet.freezePanes.freezeRows(5);

const rawIndex = workbook.worksheets.add("Raw source index");
formatTitle(rawIndex, "Raw source index", "Raw PEEC payload files and channel row counts used to build this workbook.");
const rawRows = [
  ["Period", "File", "Channel", "Channel ID", "Rows"],
  ...currentRaw.channel_payloads.map((item) => [
    "current",
    "raw/peec-current.json",
    item.channel_name,
    item.channel_id,
    item.parsed_row_count,
  ]),
  ...priorRaw.channel_payloads.map((item) => [
    "prior",
    "raw/peec-prior.json",
    item.channel_name,
    item.channel_id,
    item.parsed_row_count,
  ]),
];
rawIndex.getRange(`A5:E${rawRows.length + 4}`).values = rawRows;
formatHeader(rawIndex.getRange("A5:E5"));
rawIndex.getRange("E6:E11").format.numberFormat = "#,##0";
rawIndex.freezePanes.freezeRows(5);
autofit(rawIndex, "A1:E12");

const dashboardInspect = await workbook.inspect({
  kind: "table",
  sheetId: "Dashboard",
  range: "A1:H20",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 12,
});
console.log(dashboardInspect.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

await fs.mkdir(outputDir, { recursive: true });
const preview = await workbook.render({
  sheetName: "Dashboard",
  range: "A1:H20",
  scale: 2,
  format: "png",
});
await fs.writeFile(
  path.join(outputDir, "peec-ai-dashboard-2026-09-18-dashboard-preview.png"),
  new Uint8Array(await preview.arrayBuffer())
);

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(JSON.stringify({ outputPath, rows: evidenceRows.length, sheets: workbook.worksheets.items.length }));
