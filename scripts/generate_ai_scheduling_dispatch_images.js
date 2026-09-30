const fs = require("fs");
const path = require("path");
const sharp = require("sharp");

const root = path.resolve(__dirname, "..");
const slug = "ai-scheduling-dispatch-field-service";
const outDir = path.join(root, "assets", "images", "blog", slug);
const researchDir = path.join(root, "research");

const palette = {
  navy: "#0A2240",
  yellow: "#FFC600",
  green: "#01B59A",
  orange: "#E75C0D",
  blue: "#00A3D9",
  grey: "#BDC6CC",
  lightGrey: "#EEF3F6",
  white: "#FFFFFF",
  ink: "#15314F",
};

const vaultBasis = {
  resource_id: "res-339d828f9b875c738f530a65ccbc3587",
  title: "Simpro Group Brand Usage Guide",
  content_sha256: "402331bb9e8e808ec9bb3f95e9d8d88e2be4f42e269a59de0a983b896881c92b",
  guidance: "Use Simpro product brand for product-led, customer-facing visuals; verify typography, palette, and assets against the current SimproGroup Style Sheet route.",
};

function esc(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function textBlock(lines, x, y, opts = {}) {
  const size = opts.size || 28;
  const weight = opts.weight || 600;
  const fill = opts.fill || palette.navy;
  const anchor = opts.anchor || "start";
  const lineHeight = opts.lineHeight || Math.round(size * 1.28);
  return `<text x="${x}" y="${y}" fill="${fill}" font-size="${size}" font-weight="${weight}" text-anchor="${anchor}">${lines
    .map((line, index) => `<tspan x="${x}" dy="${index === 0 ? 0 : lineHeight}">${esc(line)}</tspan>`)
    .join("")}</text>`;
}

function roundedRect(x, y, width, height, radius, fill, stroke = "none", strokeWidth = 0) {
  return `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"/>`;
}

function pill(x, y, width, label, fill, color = palette.white) {
  return `${roundedRect(x, y, width, 44, 22, fill)}${textBlock([label], x + width / 2, y + 29, {
    size: 18,
    weight: 700,
    fill: color,
    anchor: "middle",
  })}`;
}

function iconCircle(cx, cy, label, fill, color = palette.white) {
  return `<circle cx="${cx}" cy="${cy}" r="35" fill="${fill}"/>${textBlock([label], cx, cy + 10, {
    size: 25,
    weight: 800,
    fill: color,
    anchor: "middle",
  })}`;
}

function arrow(x1, y1, x2, y2, color = palette.blue, width = 5) {
  const angle = Math.atan2(y2 - y1, x2 - x1);
  const head = 14;
  const hx1 = x2 - head * Math.cos(angle - Math.PI / 7);
  const hy1 = y2 - head * Math.sin(angle - Math.PI / 7);
  const hx2 = x2 - head * Math.cos(angle + Math.PI / 7);
  const hy2 = y2 - head * Math.sin(angle + Math.PI / 7);
  return `<path d="M ${x1} ${y1} L ${x2} ${y2}" stroke="${color}" stroke-width="${width}" stroke-linecap="round" fill="none"/>
<path d="M ${x2} ${y2} L ${hx1} ${hy1} M ${x2} ${y2} L ${hx2} ${hy2}" stroke="${color}" stroke-width="${width}" stroke-linecap="round" fill="none"/>`;
}

function card(x, y, width, height, title, subtitle, options = {}) {
  const fill = options.fill || palette.white;
  const stroke = options.stroke || "none";
  const strokeWidth = options.strokeWidth || 0;
  const titleSize = options.titleSize || 23;
  const subtitleSize = options.subtitleSize || 17;
  const titleY = y + (options.titleOffset || 44);
  const subtitleY = y + (options.subtitleOffset || 78);
  return `<g filter="url(#shadow)">
    ${roundedRect(x, y, width, height, 22, fill, stroke, strokeWidth)}
    ${textBlock([title], x + width / 2, titleY, { size: titleSize, weight: 800, anchor: "middle", fill: options.titleFill || palette.navy })}
    ${subtitle ? textBlock([subtitle], x + width / 2, subtitleY, { size: subtitleSize, weight: 600, anchor: "middle", fill: options.subtitleFill || palette.ink }) : ""}
  </g>`;
}

function baseSvg(width, height, title, subtitle, body) {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(title)}" font-family="Urbanist, Inter, Arial, Helvetica, sans-serif">
  <defs>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#0A2240" flood-opacity="0.15"/>
    </filter>
    <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">
      <path d="M 48 0 L 0 0 0 48" fill="none" stroke="#D8E1E7" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="${width}" height="${height}" fill="${palette.lightGrey}"/>
  <rect width="${width}" height="${height}" fill="url(#grid)" opacity="0.55"/>
  <rect x="0" y="0" width="${width}" height="18" fill="${palette.yellow}"/>
  <text x="72" y="78" fill="${palette.navy}" font-size="30" font-weight="800">Simpro</text>
  ${textBlock([title], 72, 142, { size: width > 1300 ? 52 : 40, weight: 800, fill: palette.navy })}
  ${textBlock([subtitle], 74, width > 1300 ? 188 : 184, { size: width > 1300 ? 23 : 20, weight: 500, fill: palette.ink })}
  ${body}
</svg>`;
}

function heroSvg() {
  const width = 1600;
  const height = 900;
  const boardX = 510;
  const boardY = 260;
  const boardW = 1010;
  const boardH = 500;
  const colW = 220;
  const colX = [590, 810, 1030, 1250];
  const body = `
  <g filter="url(#shadow)">
    ${roundedRect(76, 286, 352, 430, 28, palette.white)}
    ${textBlock(["Dispatcher checks"], 118, 356, { size: 32, weight: 800 })}
    ${pill(118, 396, 130, "Skills", palette.green)}
    ${pill(270, 396, 116, "Priority", palette.orange)}
    ${pill(118, 462, 126, "Location", palette.blue)}
    ${pill(264, 462, 120, "Parts", palette.navy)}
    ${textBlock(["Approve valid moves,", "hold customer promises,", "recover manually."], 118, 570, {
      size: 26,
      weight: 600,
      fill: palette.ink,
      lineHeight: 40,
    })}
  </g>
  <g filter="url(#shadow)">
    ${roundedRect(boardX, boardY, boardW, boardH, 30, palette.white)}
    ${roundedRect(boardX, boardY, boardW, 80, 30, palette.navy)}
    ${textBlock(["AI-assisted schedule board"], boardX + 42, boardY + 52, { size: 29, weight: 800, fill: palette.white })}
    ${["Mon", "Tue", "Wed", "Thu"].map((day, i) =>
      textBlock([day], colX[i] + colW / 2, boardY + 132, { size: 24, weight: 800, fill: palette.navy, anchor: "middle" })
    ).join("")}
    ${[0, 1, 2, 3].map((i) => `<line x1="${colX[i]}" y1="${boardY + 162}" x2="${colX[i]}" y2="${boardY + 445}" stroke="#D8E1E7" stroke-width="2"/>`).join("")}
    ${[
      [560, 438, 190, 76, palette.green, "Install", "Matched skills"],
      [780, 420, 190, 76, palette.blue, "Repair", "Near site"],
      [1000, 522, 190, 76, palette.orange, "Emergency", "Review first"],
      [1220, 446, 190, 76, palette.navy, "Maintenance", "Fixed window"],
      [670, 616, 190, 76, palette.yellow, "Open slot", "Candidate fill", palette.navy],
    ].map(([x, y, w, h, fill, label, sub, color]) => `
      ${roundedRect(x, y, w, h, 16, fill)}
      ${textBlock([label], x + 22, y + 31, { size: 21, weight: 800, fill: color || palette.white })}
      ${textBlock([sub], x + 22, y + 59, { size: 17, weight: 600, fill: color || palette.white })}
    `).join("")}
    ${arrow(1306, 625, 1408, 625, palette.green, 6)}
    ${textBlock(["Suggested move"], 1180, 677, { size: 23, weight: 800, fill: palette.green })}
  </g>`;
  return baseSvg(width, height, "AI scheduling and dispatch optimization", "Branded operational diagram for field service scheduling decisions", body);
}

function dataMapSvg() {
  const width = 1200;
  const height = 675;
  const nodeW = 300;
  const nodeH = 96;
  const nodes = [
    [95, 252, "Techs", "Skills and certs", palette.green],
    [450, 252, "Jobs", "Type and priority", palette.blue],
    [805, 252, "Sites", "Access and windows", palette.orange],
    [95, 390, "Customers", "Commitments", palette.blue],
    [450, 390, "Policy", "Rules and promises", palette.yellow, palette.navy],
    [805, 390, "Parts", "Availability", palette.navy],
  ];
  const recommendation = { x: 300, y: 545, width: 600, height: 92 };
  const body = `
    <path d="M 245 488 L 245 516 L 600 516 L 600 545" stroke="#8FA4B2" stroke-width="4" stroke-linecap="round" fill="none"/>
    <path d="M 600 488 L 600 545" stroke="#8FA4B2" stroke-width="4" stroke-linecap="round" fill="none"/>
    <path d="M 955 488 L 955 516 L 600 516" stroke="#8FA4B2" stroke-width="4" stroke-linecap="round" fill="none"/>
    <path d="M 245 348 L 245 516" stroke="#8FA4B2" stroke-width="4" stroke-linecap="round" fill="none" opacity="0.7"/>
    <path d="M 600 348 L 600 545" stroke="#8FA4B2" stroke-width="4" stroke-linecap="round" fill="none" opacity="0.7"/>
    <path d="M 955 348 L 955 516" stroke="#8FA4B2" stroke-width="4" stroke-linecap="round" fill="none" opacity="0.7"/>
    <g filter="url(#shadow)">
      ${roundedRect(recommendation.x, recommendation.y, recommendation.width, recommendation.height, 24, palette.white, palette.green, 5)}
      ${textBlock(["Scheduling recommendation"], 600, 583, { size: 28, weight: 800, anchor: "middle" })}
      ${textBlock(["Only valid options move forward"], 600, 616, { size: 17, weight: 700, fill: palette.ink, anchor: "middle" })}
    </g>
    ${nodes.map(([x, y, label, sub, fill, color]) => `
      <g filter="url(#shadow)">
        ${roundedRect(x, y, nodeW, nodeH, 22, palette.white)}
        ${iconCircle(x + 54, y + 48, label.slice(0, 1), fill, color || palette.white)}
        ${textBlock([label], x + 118, y + 41, { size: 23, weight: 800 })}
        ${textBlock([sub], x + 118, y + 70, { size: 15, weight: 600, fill: palette.ink })}
      </g>
    `).join("")}`;
  return baseSvg(width, height, "Data inputs for AI scheduling", "Complete operating records feed safer scheduling decisions", body);
}

function controlLoopSvg() {
  const width = 1200;
  const height = 675;
  const steps = [
    [60, "1", "Schedule event", "New job or change", palette.blue],
    [280, "2", "AI recommendation", "Valid options only", palette.green],
    [500, "3", "Dispatcher approval", "Promises checked", palette.orange],
    [720, "4", "Field update", "Write confirmed", palette.navy],
    [940, "5", "Manual fallback", "Recover if needed", palette.yellow, palette.navy],
  ];
  const body = `
    ${[245, 465, 685, 905].map((x) => arrow(x, 408, x + 34, 408, palette.grey, 5)).join("")}
    <path d="M 1030 302 C 930 238 274 238 170 302" stroke="${palette.grey}" stroke-width="5" stroke-linecap="round" fill="none" stroke-dasharray="12 16"/>
    ${steps.map(([x, number, label, sub, fill, color]) => `
      <g filter="url(#shadow)">
        ${roundedRect(x, 320, 206, 176, 24, palette.white)}
        ${iconCircle(x + 103, 368, number, fill, color || palette.white)}
        ${textBlock([label], x + 103, 438, { size: 20, weight: 800, anchor: "middle" })}
        ${textBlock([sub], x + 103, 468, { size: 15, weight: 600, fill: palette.ink, anchor: "middle" })}
      </g>
    `).join("")}`;
  return baseSvg(width, height, "Dispatcher control workflow", "Human review stays visible before scheduling changes reach the field", body);
}

function pilotSvg() {
  const width = 1200;
  const height = 675;
  const points = [
    [140, 390, "Days 1-5", "Baseline", palette.blue],
    [365, 390, "Days 6-12", "Shadow mode", palette.green],
    [590, 390, "Days 13-21", "Approved use", palette.orange],
    [815, 390, "Days 22-27", "Exception testing", palette.navy],
    [1040, 390, "Days 28-30", "Scale decision", palette.yellow, palette.navy],
  ];
  const body = `
    <line x1="140" y1="390" x2="1040" y2="390" stroke="${palette.grey}" stroke-width="8" stroke-linecap="round"/>
    ${points.slice(0, -1).map((point, index) => arrow(point[0] + 58, 390, points[index + 1][0] - 62, 390, palette.grey, 5)).join("")}
    ${points.map(([x, y, top, bottom, fill, color], index) => `
      <g filter="url(#shadow)">
        <circle cx="${x}" cy="${y}" r="56" fill="${fill}"/>
        ${textBlock([String(index + 1)], x, y + 12, { size: 34, weight: 800, fill: color || palette.white, anchor: "middle" })}
        ${roundedRect(x - 104, y + 92, 208, 100, 20, palette.white)}
        ${textBlock([top], x, y + 130, { size: 17, weight: 800, anchor: "middle" })}
        ${textBlock([bottom], x, y + 160, { size: 17, weight: 700, fill: palette.ink, anchor: "middle" })}
      </g>
    `).join("")}
    <g filter="url(#shadow)">
      ${roundedRect(118, 242, 964, 72, 20, palette.white)}
      ${textBlock(["One event. One owner. One fallback. Review evidence before expanding."], 600, 288, {
        size: 24,
        weight: 800,
        fill: palette.navy,
        anchor: "middle",
      })}
    </g>`;
  return baseSvg(width, height, "30-day AI scheduling pilot", "Controlled rollout plan for field service scheduling teams", body);
}

const assets = [
  {
    key: "hero",
    filename: "ai-scheduling-dispatch-field-service-hero.webp",
    source: "ai-scheduling-dispatch-field-service-hero.svg",
    width: 1600,
    height: 900,
    alt: "AI scheduling and dispatch optimization for field service teams",
    placement: "line 41 placeholder",
    render_target: "featured image",
    svg: heroSvg,
  },
  {
    key: "data-rules",
    filename: "ai-scheduling-dispatch-field-service-data-rules.webp",
    source: "ai-scheduling-dispatch-field-service-data-rules.svg",
    width: 1200,
    height: 675,
    alt: "Data inputs used for AI field service scheduling decisions",
    placement: "line 79 placeholder",
    render_target: "data and business rules section",
    svg: dataMapSvg,
  },
  {
    key: "dispatcher-control",
    filename: "ai-scheduling-dispatch-field-service-dispatcher-control.webp",
    source: "ai-scheduling-dispatch-field-service-dispatcher-control.svg",
    width: 1200,
    height: 675,
    alt: "AI scheduling recommendation and dispatcher override workflow",
    placement: "line 97 placeholder",
    render_target: "dispatcher control section",
    svg: controlLoopSvg,
  },
  {
    key: "pilot-workflow",
    filename: "ai-scheduling-dispatch-field-service-30-day-pilot.webp",
    source: "ai-scheduling-dispatch-field-service-30-day-pilot.svg",
    width: 1200,
    height: 675,
    alt: "30-day AI scheduling and dispatch pilot for field service teams",
    placement: "line 170 placeholder",
    render_target: "controlled pilot section",
    svg: pilotSvg,
  },
];

async function writeAssets() {
  fs.mkdirSync(outDir, { recursive: true });
  fs.mkdirSync(researchDir, { recursive: true });

  const records = [];
  for (const asset of assets) {
    const svg = asset.svg();
    const svgPath = path.join(outDir, asset.source);
    const webpPath = path.join(outDir, asset.filename);
    fs.writeFileSync(svgPath, svg, "utf8");
    await sharp(Buffer.from(svg))
      .resize(asset.width, asset.height, { fit: "cover" })
      .webp({ quality: 86, effort: 6 })
      .toFile(webpPath);

    const stats = fs.statSync(webpPath);
    records.push({
      key: asset.key,
      filename: `assets/images/blog/${slug}/${asset.filename}`,
      source_svg: `assets/images/blog/${slug}/${asset.source}`,
      dimensions: `${asset.width} x ${asset.height}`,
      format: "WebP",
      bytes: stats.size,
      alt: asset.alt,
      alt_length: asset.alt.length,
      placement: asset.placement,
      render_target: asset.render_target,
      compression_status: "compressed with sharp webp quality 86 effort 6",
      cms_upload_url: "pending CMS upload",
    });
  }

  const generatedAt = new Date().toISOString();
  const metadata = {
    schema: "simpro-blog-image-handoff/v1",
    article: "published/ai-scheduling-dispatch-field-service-2026-07-17.md",
    slug,
    generated_at: generatedAt,
    source_article_mutated: false,
    vault_basis: vaultBasis,
    brand_direction: {
      brand: "Simpro",
      asset_type: "branded explanatory diagrams",
      palette,
      typography: "Urbanist where available; Inter, Arial, sans-serif fallback",
      restrictions: [
        "No fake Simpro UI",
        "No unsupported AI feature states",
        "No customer names",
        "No outcome metrics",
        "No rankings",
        "No competitor logos",
        "No generic stock-photo dispatch imagery",
      ],
    },
    assets: records,
    cms_qa_required: [
      "Replace source placeholders with uploaded CMS image URLs",
      "Verify desktop and mobile rendering",
      "Verify thumbnail crop for featured image",
      "Verify alt text is present and under 125 characters",
      "Verify featured image is represented by ImageObject in deployed schema",
      "Verify existing VideoObject remains only with the verified video embed",
      "Run launch QA for canonical, indexability, links, schema, responsive video, mobile layout, accessibility, and Core Web Vitals",
    ],
  };

  const jsonPath = path.join(researchDir, "image-handoff-ai-scheduling-dispatch-field-service-2026-09-29.json");
  fs.writeFileSync(jsonPath, `${JSON.stringify(metadata, null, 2)}\n`, "utf8");
  fs.writeFileSync(path.join(outDir, "image-handoff-2026-09-29.json"), `${JSON.stringify(metadata, null, 2)}\n`, "utf8");

  const rows = records
    .map(
      (record) =>
        `| ${record.render_target} | \`${record.filename}\` | ${record.dimensions} | ${record.bytes} | ${record.alt} | ${record.cms_upload_url} |`
    )
    .join("\n");
  const md = `# AI Scheduling Dispatch Image Handoff

Generated: ${generatedAt}

Article: \`published/ai-scheduling-dispatch-field-service-2026-07-17.md\`

Source article mutated: no.

## Vault Basis

- Resource ID: \`${vaultBasis.resource_id}\`
- Title: ${vaultBasis.title}
- Content SHA-256: \`${vaultBasis.content_sha256}\`
- Applied guidance: ${vaultBasis.guidance}

## Brand Direction

- Brand: Simpro product brand, not Simpro Group.
- Asset type: branded explanatory diagrams.
- Palette: Navy \`${palette.navy}\`, Yellow \`${palette.yellow}\`, Green \`${palette.green}\`, Orange \`${palette.orange}\`, Blue \`${palette.blue}\`, Grey \`${palette.grey}\`.
- Typography: Urbanist where available, with Inter, Arial, sans-serif fallback.
- Restrictions: no fake Simpro UI, unsupported AI feature states, customer names, outcome metrics, rankings, competitor logos, or generic stock-photo dispatch imagery.

## Final Assets

| Render target | File | Dimensions | Bytes | Alt text | CMS upload URL |
| --- | --- | --- | ---: | --- | --- |
${rows}

## CMS Launch QA

- Replace the four source placeholders with uploaded CMS image URLs.
- Verify desktop and mobile rendering without important-content cropping.
- Verify the featured image thumbnail crop.
- Verify alt text is present and under 125 characters.
- Verify deployed schema includes \`ImageObject\` for the featured image.
- Verify the existing \`VideoObject\` remains only with the verified Microsoft video embed.
- Run launch QA for canonical, indexability, links, schema, responsive video, mobile layout, accessibility, and Core Web Vitals.
`;
  fs.writeFileSync(path.join(researchDir, "image-handoff-ai-scheduling-dispatch-field-service-2026-09-29.md"), md, "utf8");
  fs.writeFileSync(path.join(outDir, "image-handoff-2026-09-29.md"), md, "utf8");
}

writeAssets().catch((error) => {
  console.error(error);
  process.exit(1);
});
