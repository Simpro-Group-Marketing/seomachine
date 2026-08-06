"""
Section Writer

Provides section-type-specific writing prompts and guidelines.
Routes sections to specialized approaches based on their type.

Used by the /article command during the section-by-section writing phase.
"""

from typing import List
from dataclasses import dataclass
from enum import Enum


class SectionType(Enum):
    """Types of article sections for specialized writing."""
    INTRO = "intro"
    BODY_HOW_TO = "body_how_to"
    BODY_COMPARISON = "body_comparison"
    BODY_EXPLANATION = "body_explanation"
    BODY_LIST = "body_list"
    FAQ = "faq"
    CONCLUSION = "conclusion"


@dataclass
class WritingGuidelines:
    """Guidelines for writing a specific section type."""
    section_type: SectionType
    requirements: List[str]
    dos: List[str]
    donts: List[str]
    quality_checks: List[str]


@dataclass
class EditingChecklist:
    """Checklist for editing a section."""
    universal_checks: List[str]
    section_specific_checks: List[str]


class SectionWriter:
    """
    Provides section-type-specific writing and editing guidelines.

    This class contains the writing prompts and quality criteria
    used by the /article command during section-by-section writing.
    """

    # AI phrases to remove during editing
    AI_PHRASES_TO_REMOVE = [
        "In today's",
        "When it comes to",
        "It's important to note",
        "It's worth noting",
        "In the world of",
        "At the end of the day",
        "Moving forward",
        "In order to",
        "First and foremost",
        "Last but not least",
        "Without further ado",
        "Needless to say",
        "As mentioned earlier",
        "It goes without saying",
        "In conclusion",  # Unless in actual conclusion
        "To summarize",  # Unless in actual conclusion
    ]

    # Vague words to replace with proof-safe specificity.
    VAGUE_WORDS = {
        "many": "approved proof-backed quantity or concrete workflow detail",
        "some": "scoped group or concrete workflow subset",
        "various": "workflow-specific examples",
        "numerous": "approved proof-backed quantity or softer wording",
        "significant": "supported consequence or softer wording",
        "substantial": "supported quantity or material consequence",
        "a lot of": "concrete workflow detail or approved proof",
        "several": "scoped count only when proof supports it",
        "often": "supported frequency or contextual wording",
        "usually": "supported frequency or scoped qualifier",
        "sometimes": "concrete workflow scenario",
        "things": "specific items or workflow details",
        "stuff": "specific items or workflow details",
        "good": "specific benefit supported by the section evidence",
        "bad": "specific drawback supported by the section evidence",
        "nice": "specific quality supported by the section evidence",
        "great": "specific advantage supported by the section evidence",
    }

    def get_writing_guidelines(
        self,
        section_type: SectionType
    ) -> WritingGuidelines:
        """
        Get writing guidelines for a specific section type.

        Args:
            section_type: The type of section being written

        Returns:
            WritingGuidelines with requirements, dos, and donts
        """
        guidelines = {
            SectionType.INTRO: self._intro_guidelines(),
            SectionType.BODY_HOW_TO: self._how_to_guidelines(),
            SectionType.BODY_COMPARISON: self._comparison_guidelines(),
            SectionType.BODY_EXPLANATION: self._explanation_guidelines(),
            SectionType.BODY_LIST: self._list_guidelines(),
            SectionType.FAQ: self._faq_guidelines(),
            SectionType.CONCLUSION: self._conclusion_guidelines(),
        }

        return guidelines.get(section_type, self._explanation_guidelines())

    def get_editing_checklist(
        self,
        section_type: SectionType
    ) -> EditingChecklist:
        """
        Get editing checklist for a section type.

        Args:
            section_type: The type of section being edited

        Returns:
            EditingChecklist with universal and specific checks
        """
        universal = [
            "Remove AI phrases from the removal list",
            "Replace vague words with approved proof-backed detail or concrete workflow detail",
            "Ensure no paragraph exceeds 4 sentences",
            "Mix short sentences (5-10 words) with longer ones (15-25 words)",
            "Add contractions for natural voice",
            "Use active voice (target 80%+)",
            "Add parenthetical asides or questions for engagement",
            "Verify brand voice consistency",
        ]

        specific_checks = self._get_specific_editing_checks(section_type)

        return EditingChecklist(
            universal_checks=universal,
            section_specific_checks=specific_checks
        )

    def _intro_guidelines(self) -> WritingGuidelines:
        """Guidelines for introduction sections."""
        return WritingGuidelines(
            section_type=SectionType.INTRO,
            requirements=[
                "Use the caller-supplied section word target without padding",
                "Compelling hook in first 1-2 sentences",
                "APP Formula: Agree, Promise, Preview",
                "Primary keyword in first 100 words",
                "Trust signal or credibility indicator",
            ],
            dos=[
                "Open with a provocative question",
                "Use a proof-safe operational scene when it materially improves understanding",
                "Lead with a proof-approved statistic only when it materially advances the reader promise",
                "Make a bold/counterintuitive statement",
                "Acknowledge reader's situation (Agree)",
                "Promise clear value (Promise)",
                "Preview what's coming (Preview)",
            ],
            donts=[
                "Start with '[Topic] is...'",
                "Use 'When it comes to...'",
                "Open with 'If you're looking for...'",
                "Begin with 'In today's world...'",
                "Start with a dictionary definition",
                "Use generic phrases like 'Welcome to...'",
            ],
            quality_checks=[
                "Hook grabs attention immediately",
                "Reader knows what they'll learn",
                "Brand credibility established",
                "Tone matches brand voice",
            ]
        )

    def _how_to_guidelines(self) -> WritingGuidelines:
        """Guidelines for how-to/tutorial sections."""
        return WritingGuidelines(
            section_type=SectionType.BODY_HOW_TO,
            requirements=[
                "Use the caller-supplied section word target without padding",
                "Numbered steps for sequential processes",
                "Each step must be actionable",
                "Include expected outcomes",
                "Mention time estimates where helpful",
            ],
            dos=[
                "Use numbered lists for steps",
                "Start each step with an action verb",
                "Include specific tool/platform names",
                "Add 'Pro tip' callouts for advanced users",
                "Note common mistakes at relevant steps",
                "Show what success looks like",
            ],
            donts=[
                "Use vague instructions",
                "Skip important sub-steps",
                "Assume prior knowledge without explaining",
                "Forget to mention prerequisites",
            ],
            quality_checks=[
                "Steps are in logical order",
                "Each step is independently actionable",
                "Outcomes are clear",
                "Reader can follow without guessing",
            ]
        )

    def _comparison_guidelines(self) -> WritingGuidelines:
        """Guidelines for comparison sections."""
        return WritingGuidelines(
            section_type=SectionType.BODY_COMPARISON,
            requirements=[
                "Use the caller-supplied section word target without padding",
                "Balanced perspective (fair to competitors)",
                "Proof-approved comparison details, or concrete workflow distinctions when proof is unavailable",
                "'Best for' recommendations",
                "Comparison table if 3+ items",
            ],
            dos=[
                "Use tables for proof-approved metrics or clearly scoped feature/workflow distinctions",
                "Acknowledge competitor strengths",
                "Be specific about prices and features only when approved proof supports them",
                "Explain WHY your product excels where it does",
                "Include 'Best for X' recommendations",
                "Cite sources for competitor info",
            ],
            donts=[
                "Dismiss competitors unfairly",
                "Use vague comparisons",
                "Make unsupported claims",
                "Be overly promotional",
                "Ignore legitimate competitor advantages",
            ],
            quality_checks=[
                "Comparison feels fair and balanced",
                "Approved proof supports any numeric comparison",
                "Reader can make informed decision",
                "Product advantages are clear but not pushy",
            ]
        )

    def _explanation_guidelines(self) -> WritingGuidelines:
        """Guidelines for explanation/educational sections."""
        return WritingGuidelines(
            section_type=SectionType.BODY_EXPLANATION,
            requirements=[
                "Use the caller-supplied section word target without padding",
                "Progressive complexity (simple to advanced)",
                "Concrete examples",
                "Analogies for complex concepts",
            ],
            dos=[
                "Start with the simplest explanation",
                "Use analogies to familiar concepts",
                "Include real-world examples",
                "Define technical terms",
                "Connect to reader's experience",
            ],
            donts=[
                "Assume technical knowledge",
                "Use jargon without explanation",
                "Stay abstract without examples",
                "Overcomplicate simple concepts",
            ],
            quality_checks=[
                "Beginner could understand this",
                "Expert wouldn't be bored",
                "Examples are concrete and relatable",
                "Complexity builds appropriately",
            ]
        )

    def _list_guidelines(self) -> WritingGuidelines:
        """Guidelines for list-based sections."""
        return WritingGuidelines(
            section_type=SectionType.BODY_LIST,
            requirements=[
                "Use the caller-supplied section word target without padding",
                "Clear numbering or bullets",
                "Brief explanation for each item",
                "Consistent format across items",
            ],
            dos=[
                "Number items for scannability",
                "Include 1-2 sentence explanation per item",
                "Highlight standout items",
                "Order by importance or logic",
                "Use parallel structure",
            ],
            donts=[
                "List without explanation",
                "Vary format inconsistently",
                "Include too many items (7-10 max)",
                "Use wall-of-text format for lists",
            ],
            quality_checks=[
                "Items are scannable",
                "Each item is explained",
                "Format is consistent",
                "Order makes sense",
            ]
        )

    def _faq_guidelines(self) -> WritingGuidelines:
        """Guidelines for FAQ sections."""
        return WritingGuidelines(
            section_type=SectionType.FAQ,
            requirements=[
                "Use the caller-supplied section word target without padding",
                "4-6 questions",
                "40-60 word answers (featured snippet optimized)",
                "Questions from real user research",
            ],
            dos=[
                "Use real questions from Reddit/YouTube research",
                "Format as Q&A with clear separation",
                "Start answers with direct response",
                "Add context after the direct answer",
                "Target featured snippet format",
            ],
            donts=[
                "Use generic/obvious questions",
                "Write essay-length answers",
                "Start answers with 'Yes' or 'No' alone",
                "Repeat information from earlier sections",
            ],
            quality_checks=[
                "Questions feel authentic (not manufactured)",
                "Answers are 40-60 words (snippet length)",
                "Direct answer comes first",
                "Questions aren't answered elsewhere in article",
            ]
        )

    def _conclusion_guidelines(self) -> WritingGuidelines:
        """Guidelines for conclusion sections."""
        return WritingGuidelines(
            section_type=SectionType.CONCLUSION,
            requirements=[
                "NOT just a summary - add value",
                "Close the Reader Contract promise",
                "Conclusion includes an intent-appropriate next action",
            ],
            dos=[
                "Use the next action style implied by funnel stage and section plan",
                "Offer reflection, discussion, evidence resources, or practical follow-up when commercial action is not appropriate",
                "End on empowering, forward-looking note",
                "Follow the supplied CTA plan; do not add a CTA when none is specified",
                "Add primary keyword naturally",
            ],
            donts=[
                "Simply restate the introduction",
                "Introduce new information",
                "End with generic 'good luck'",
                "Add a commercial CTA when the supplied plan does not call for one",
                "Make the CTA feel forced",
                "Turn every conclusion into a task list",
            ],
            quality_checks=[
                "Reader has a useful next action that matches intent",
                "Takeaways are actionable, not platitudes",
                "Any planned CTA feels natural and valuable",
                "Tone is empowering, not preachy",
            ]
        )

    def _get_specific_editing_checks(
        self,
        section_type: SectionType
    ) -> List[str]:
        """Get section-specific editing checks."""
        checks = {
            SectionType.INTRO: [
                "Hook is compelling (not generic)",
                "APP formula present",
                "Primary keyword in first 100 words",
                "Trust signal included",
            ],
            SectionType.BODY_HOW_TO: [
                "Steps are numbered",
                "Each step is actionable",
                "Specific tools/platforms named",
                "Outcomes are clear",
            ],
            SectionType.BODY_COMPARISON: [
                "Comparison is fair",
                "Approved proof supports any numeric comparison",
                "'Best for' recommendations included",
                "Not overly promotional",
            ],
            SectionType.BODY_EXPLANATION: [
                "Complexity builds appropriately",
                "Analogies/examples present",
                "Technical terms defined",
            ],
            SectionType.BODY_LIST: [
                "Items are consistently formatted",
                "Each item has explanation",
                "Order is logical",
            ],
            SectionType.FAQ: [
                "Questions are authentic",
                "Answers are 40-60 words",
                "Direct answer first in each",
            ],
            SectionType.CONCLUSION: [
                "More than summary",
                "Closes the Reader Contract promise",
                "Conclusion includes an intent-appropriate next action",
                "Empowering tone",
            ],
        }

        return checks.get(section_type, [])


def format_writing_prompt(
    section_type: SectionType,
    heading: str,
    word_target: int,
    strategic_angle: str,
    unique_data: List[str],
    internal_links: List[str],
    has_mini_story: bool,
    has_cta: str
) -> str:
    """
    Format a complete writing prompt for a section.

    This generates the prompt that guides section writing.
    """
    writer = SectionWriter()
    guidelines = writer.get_writing_guidelines(section_type)

    prompt = f"""## Write Section: {heading}

**Type**: {section_type.value}
**Word Target**: {word_target} words
**Strategic Angle**: {strategic_angle}

### Requirements
"""
    for req in guidelines.requirements:
        prompt += f"- {req}\n"

    prompt += "\n### Do\n"
    for do in guidelines.dos[:5]:
        prompt += f"- {do}\n"

    prompt += "\n### Don't\n"
    for dont in guidelines.donts[:4]:
        prompt += f"- {dont}\n"

    if unique_data:
        prompt += "\n### Include These Unique Insights\n"
        for insight in unique_data[:3]:
            prompt += f"- {insight}\n"

    if internal_links:
        prompt += "\n### Internal Links to Include\n"
        for link in internal_links[:3]:
            prompt += f"- {link}\n"

    if has_mini_story:
        prompt += """
### Optional Editorial Scene
Unnamed workflow scenes are allowed only when they materially improve understanding; they are explanatory and do not count as E-E-A-T proof.
Named people or businesses require approved proof in the validation sidecar and a source-backed reason to include them.
Omit the scene when it does not improve this section.
Do not invent names, companies, dates, metrics, quotes, outcomes, or testimonial wording.
"""

    if has_cta:
        cta_labels = {
            "soft_resource_action": "soft resource/action",
            "educational_next_step": "educational next step",
            "contextual_product": "contextual product",
            "commercial_contextual": "contextual commercial",
            "commercial_comparison": "commercial comparison",
            "commercial_conversion": "commercial conversion",
            "thought_leadership_next_action": "thought leadership next action",
        }
        cta_label = cta_labels.get(has_cta, has_cta.replace("_", " "))
        if has_cta == "thought_leadership_next_action":
            prompt += f"""
### Next Action Required ({cta_label})
Close with a reflection, discussion, evidence resource, or other useful next action that fits the article's thought-leadership intent.
"""
        else:
            prompt += f"""
### CTA Required ({cta_label})
Include a {cta_label} call-to-action that feels natural in context.
"""

    prompt += """
### Quality Checks Before Finishing
"""
    for check in guidelines.quality_checks:
        prompt += f"- [ ] {check}\n"

    return prompt


def format_editing_prompt(
    section_type: SectionType,
    draft: str
) -> str:
    """
    Format an editing prompt for a section draft.

    This generates the prompt for the editing pass.
    """
    writer = SectionWriter()
    checklist = writer.get_editing_checklist(section_type)

    prompt = f"""## Edit This {section_type.value} Section

### Draft to Edit
{draft}

---

### Universal Editing Checks
"""
    for check in checklist.universal_checks:
        prompt += f"- [ ] {check}\n"

    prompt += f"""
### Section-Specific Checks ({section_type.value})
"""
    for check in checklist.section_specific_checks:
        prompt += f"- [ ] {check}\n"

    prompt += """
### AI Phrases to Remove
"""
    for phrase in writer.AI_PHRASES_TO_REMOVE[:8]:
        prompt += f"- \"{phrase}\"\n"

    prompt += """
### Vague Words to Replace
"""
    for vague, replacement in list(writer.VAGUE_WORDS.items())[:6]:
        prompt += f"- \"{vague}\" → {replacement}\n"

    return prompt


if __name__ == "__main__":
    print("Section Writer")
    print("=" * 50)
    print("This module provides section-type-specific writing")
    print("and editing guidelines for the /article command.")
    print()
    print("Section Types:")
    for section_type in SectionType:
        print(f"  - {section_type.value}")
    print()
    print("AI Phrases to Remove:")
    writer = SectionWriter()
    for phrase in writer.AI_PHRASES_TO_REMOVE[:5]:
        print(f"  - \"{phrase}\"")
    print("  ...")
