# FAQ Answer Quality Rule

Apply this rule to every FAQ in a blog draft, rewrite, or published Markdown handoff.

## Drafting rules

- Ask only questions that are production BOM PAA questions, in their exact wording, as `###` headings under the FAQ section.
- Write the first visible FAQ paragraph as a 40-60 word answer.
- Lead with an extractable answer: a supported number or range, named recommendation, definition, concrete action, or explained yes/no response.
- Do not open with a generic deflection such as `There is no`, `It depends`, `Pricing depends`, `Costs vary`, `We do not know`, `It is unclear`, or `No source ranks`.
- Put limitations and suitability caveats after the direct answer.
- Fact-driven or high-risk FAQ claims use `inline_required`: add a natural descriptive anchor to an authoritative public source in the first visible answer paragraph, and that source must be a BOM fact or proof URL. Prefer a neutral or non-competing expert source; never use a competitor-owned source. When the answer states compliance, legal, regulatory, statistical, or research-backed claims, link a non-owned public source. Lower-risk answers follow their machine-assigned `section_source_allowed`, `sidecar_only`, or `proof_not_required` mode without quota-only links.
- Replace or remove a question when no defensible, evidence-backed answer is available.

## What the release enforces

`/publish-readiness` runs `python -m data_sources.modules.production.release`, which checks FAQs this way:

- Truth blocks any visible FAQ question that is not a BOM PAA question, and any question in the FAQ section that is not a `###` question heading.
- Truth blocks a claim that cites a source outside the BOM, and a material number that no BOM fact or proof item linked in the same paragraph supports.
- Coverage blocks when a `must` BOM PAA question is missing from the FAQ.
- The AEO/GEO scorer always runs its FAQ policy check: it fails when the BOM selects PAA questions and the article has no visible FAQ, or when the article shows a FAQ the BOM selected no questions for.
- When a visible FAQ exists, the scorer also runs its question, answer length (first paragraph 40-60 words), answer quality (no generic deflection opener), and FAQ proof checks (each answer meets its citation mode against the FAQ Proof Map the release renders from the BOM, and competitor-owned FAQ sources are prohibited). Without a visible FAQ those four checks are not applicable.
- A failed FAQ check fails the AEO/GEO gate.

The release does not run the standalone non-owned research-link check, so the non-owned source requirement for compliance, legal, regulatory, statistical, or research-backed FAQ claims is a drafting rule. Canonical policy lives in `context/aeo-geo-blog-strategy.md`.
