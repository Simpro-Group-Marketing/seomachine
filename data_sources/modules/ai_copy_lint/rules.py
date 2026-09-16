"""Static rule definitions for the AI copy linter."""

from __future__ import annotations

import re
from typing import Pattern


APPROVED_PROPER_NOUNS = [
    "Simpro", "Simpro.ai", "Simpro Group", "Lightning AI", "G2", "Capterra",
    "Software Advice", "GetApp", "TrustRadius", "Gartner Digital Markets",
    "Gartner", "Trustpilot", "Google reviews",
]

FAQ_QUESTION_HEADING_RE = re.compile(r"^\s{0,3}#{2,6}\s+.+\?\s*$")
COMPARISON_LABEL_RE = re.compile(r"^\s*\*\*(?:Best fit|Pricing route):\*\*", re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
NON_VISIBLE_HTML_OPEN_RE = re.compile(r"<\s*(script|style)\b", re.IGNORECASE)
NON_VISIBLE_HTML_CLOSE_RE = re.compile(r"<\s*/\s*(script|style)\s*>", re.IGNORECASE)
HOW_CAN_HEADING_RE = re.compile(r"^\s{0,3}##\s+How\b.+\bCan\b.+$", re.IGNORECASE)
MODAL_VERB_TOKEN_RE = re.compile(r"\b(?:can|may|could|should|might)\b", re.IGNORECASE)
APPROVED_MODAL_CAVEAT_LINES = {"All RAIN feature timing reflects current targets and may shift."}

ERROR_RULES: list[tuple[str, Pattern[str], str, str]] = [
    ("em_dash", re.compile(r"\u2014"), "Em dashes are not allowed in Simpro web copy.", "Replace with a comma, period, colon, or parentheses."),
    ("semicolon", re.compile(r";"), "Semicolons are not allowed in Simpro web copy.", "Split the sentence or use a comma or period."),
    ("hashtag", re.compile(r"(?<![#\w])#[A-Za-z][A-Za-z0-9_-]*"), "Hashtags are not allowed in final copy.", "Remove the hashtag or rewrite it as plain text if needed."),
    ("not_just_but_also", re.compile(r"\bnot\s+just\b.{0,100}\bbut\s+also\b", re.IGNORECASE), "Avoid the formulaic 'not just X, but also Y' construction.", "State the stronger point directly."),
    ("setup_phrase", re.compile(r"\b(?:in conclusion|in closing|in summary|to summarize|to sum up|without further ado|all things considered|at the end of the day)\b,?", re.IGNORECASE), "Avoid generic setup or closing language.", "Delete the setup phrase and lead with the point."),
    ("ai_phrase", re.compile(r"\b(?:in today's|in a world where|imagine a world where|shed light|dive deep|delve|embark|glimpse into|navigating the landscape|ever-evolving|not alone|pave the way|a myriad of|a plethora of)\b", re.IGNORECASE), "This phrase is a common AI-writing tell.", "Use clear, direct language."),
    ("unsupported_hype", re.compile(r"\b(?:game[- ]changer|revolutionize|disruptive|skyrocket|groundbreaking|cutting-edge|remarkable|pivotal|intricate|tapestry|abyss|illuminate|unveil|elucidate|harness|utilize|utilizing|unlock|discover|boost|powerful)\b", re.IGNORECASE), "Avoid hype terms unless a brief explicitly approves the claim.", "Use a specific outcome, metric, or feature instead."),
    ("internal_process_language", re.compile(r"\b(?:repo context|repository context|approved internal proof path|rewrite can route readers|PAA artifact|change summary|source map|confirmed WordPress author|WordPress author before publish|schema notes)\b|\bcontext/(?:features|internal-links-map|target-keywords|brand-voice|aeo-geo-blog-strategy|writing-examples|style-guide)\.md\b", re.IGNORECASE), "Internal workflow or repo-context language is not allowed in public blog copy.", "Use context files only to guide writing. Cite public URLs or remove the internal note."),
    ("editorial_process_leakage", re.compile(r"\b(?:the\s+brief\s+(?:asks|asked|calls|called|requires|required)|(?:right|wrong)\s+editorial\s+lane|this\s+(?:article|blog|post|draft)\s+uses|(?:this|the)\s+(?:article|blog|post|draft)\s+(?:does\s+not\s+name|doesn't\s+name|avoids\s+naming|routes?\s+readers)|(?:frontmatter|metadata|validation\s+sidecar|assembly\s+BOM|publish[- ]readiness)\s+(?:says|records|requires|allows|blocks))\b", re.IGNORECASE), "Editorial process notes are not allowed in public blog body copy.", "Move rationale to frontmatter, the validation sidecar, the BOM, or the editorial plan."),
    ("source_meta_commentary", re.compile(r"\b(?:this|that|the)\s+(?:case study|source|statistic|stat|example|proof point|article|blog|section)\s+(?:is|are|was|were)\s+(?:useful|helpful|relevant|important|good|strong|appropriate)\s+for\s+(?:this|the)\s+(?:topic|article|blog|post|section|rewrite|draft)\b|\b(?:this|that|the)\s+(?:case study|source|statistic|stat|example|proof point|article|blog|section)\s+(?:belongs|fits|works)\s+(?:in|for)\s+(?:this|the)\s+(?:topic|article|blog|post|section|rewrite|draft)\b", re.IGNORECASE), "Public blog copy must not explain why a source or proof point is useful for the draft.", "Translate the source into an audience-facing takeaway, outcome, or workflow lesson."),
    ("named_fictional_scenario", re.compile(r"\b(?:Picture|Imagine|Meet)\s+(?:Marissa|Sarah|Mike|Marcus|Lisa|John|David|Emily|Chris|Alex|Tom|Anna|James|Maria|Rachel|Dan|Kate)\b(?=\s*(?:,|\.|\bwho\b|\btrying\b|\bas\b|\ban?\b|\bthe\b))|\b(?:Marissa|Sarah|Mike|Marcus|Lisa|John|David|Emily|Chris|Alex|Tom|Anna|James|Maria|Rachel|Dan|Kate)\s*,\s+(?:an?|the)\s+(?:operations manager|office manager|contractor|estimator|technician|coordinator|dispatcher|business owner|project manager)\b", re.IGNORECASE), "Named fictional scenarios are not allowed in proof-sensitive blog copy.", "Use an unnamed workflow example, or use an actual customer/review POV with proof in the validation sidecar."),
]

COPY_AVOID_RULES: list[tuple[str, str, Pattern[str], str, str]] = [
    ("modal_verb", "error", re.compile(r"\b(?:can|may|could|should|might)\b", re.IGNORECASE), "Modal verbs weaken copy and often hide uncertainty.", "Use a direct verb when the claim is supported."),
    ("filler_word", "error", re.compile(r"\b(?:just|very|really|literally|actually|certainly|probably|basically|maybe|hence|furthermore|moreover|however|additionally|ultimately|essentially|clearly|obviously|quite)\b", re.IGNORECASE), "This filler word often adds no useful meaning.", "Delete it or replace it with a specific detail."),
    ("passive_voice", "error", re.compile(r"\b(?:is|are|was|were|be|been|being)\s+(?:\w+ed|known|made|built|driven|given|taken|seen|done|set|run)\b", re.IGNORECASE), "Passive voice weakens the sentence.", "Rewrite with a clear actor and active verb."),
    ("vague_generalization", "error", re.compile(r"\b(?:many|some|various|numerous|several|often|usually|typically|generally|a lot of|things|stuff|businesses today|teams today)\b", re.IGNORECASE), "Vague language needs proof or a concrete example.", "Use approved proof or a specific unnamed operational detail."),
]

LOCKED_TITLE_CASE_EXCEPTIONS = frozenset({"AI Field Service Economics: What to Measure Before You Automate", "Build the Business Case With Your Own Numbers"})
LOCKED_MODAL_HEADING_EXCEPTIONS = frozenset({"## Where AI Can Change the Economics of a Job"})
RHETORICAL_QUESTION = re.compile(r"^\s*(?:are you|do you|have you|ever wondered|what if|want to|looking for)\b.*\?", re.IGNORECASE)
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\([^\)]*\)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->")
STRAIGHT_QUOTE_RE = re.compile(r'"[^"\n]*"')
SMART_QUOTE_RE = re.compile(r"\u201c[^\u201d\n]*\u201d")
WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z']*\b")
TITLE_FRONTMATTER_RE = re.compile(r"^\s*(?:title|meta_title)\s*:\s*(.+?)\s*$", re.IGNORECASE)
TITLE_PREPOSITIONS = {"About", "Above", "Across", "After", "Against", "Along", "Among", "Around", "As", "At", "Before", "Behind", "Below", "Beneath", "Beside", "Between", "Beyond", "By", "Despite", "Down", "During", "For", "From", "In", "Inside", "Into", "Like", "Near", "Of", "Off", "On", "Onto", "Out", "Over", "Past", "Per", "Since", "Through", "Throughout", "To", "Toward", "Towards", "Under", "Until", "Up", "Upon", "Via", "With", "Within", "Without"}
