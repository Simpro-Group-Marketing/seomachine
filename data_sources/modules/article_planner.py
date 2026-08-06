"""
Article Planner

Creates strategic section-by-section article plans from research data.
Merges competitor analysis, social research, and brand context into
a comprehensive writing plan.

Used by the /article command during the planning phase.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import re


class SectionType(Enum):
    """Types of article sections for specialized writing."""
    INTRO = "intro"
    BODY_HOW_TO = "body_how_to"
    BODY_COMPARISON = "body_comparison"
    BODY_EXPLANATION = "body_explanation"
    BODY_LIST = "body_list"
    FAQ = "faq"
    CONCLUSION = "conclusion"


class CTAType(Enum):
    """CTA or next-action roles used by article section plans."""
    SOFT = "soft"  # Legacy compatibility: learn more, explore
    MEDIUM = "medium"  # Legacy compatibility: try it, start free
    STRONG = "strong"  # Legacy compatibility: convert, sign up now
    SOFT_RESOURCE_ACTION = "soft_resource_action"
    EDUCATIONAL_NEXT_STEP = "educational_next_step"
    CONTEXTUAL_PRODUCT = "contextual_product"
    COMMERCIAL_CONTEXTUAL = "commercial_contextual"
    COMMERCIAL_COMPARISON = "commercial_comparison"
    COMMERCIAL_CONVERSION = "commercial_conversion"
    THOUGHT_LEADERSHIP_NEXT_ACTION = "thought_leadership_next_action"


class FunnelStage(Enum):
    """Reader Contract funnel stages used to plan next actions."""
    TOFU = "tofu"
    MOFU = "mofu"
    BOFU = "bofu"
    THOUGHT_LEADERSHIP = "thought leadership"


@dataclass
class ReaderContract:
    """Editorial contract resolved before article planning."""
    primary_reader: str
    sophistication_level: str
    trigger_problem: str
    existing_belief: str
    decision_task_helped: str
    distinctive_angle: str
    promised_payoff: str
    funnel_stage: FunnelStage
    exclusions: List[str]

    _STRUCTURED_EXCEPTION_TYPES = {
        "content_type",
        "serp_feature",
        "serp_structure",
        "competitor_gap",
        "cta",
    }

    def __post_init__(self) -> None:
        text_fields = (
            "primary_reader",
            "sophistication_level",
            "trigger_problem",
            "existing_belief",
            "decision_task_helped",
            "distinctive_angle",
            "promised_payoff",
        )
        for field_name in text_fields:
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isinstance(self.funnel_stage, FunnelStage):
            raise ValueError("funnel_stage must be a FunnelStage value")
        if not isinstance(self.exclusions, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in self.exclusions
        ):
            raise ValueError("exclusions must be a list of non-empty strings")
        for exclusion in self.exclusions:
            prefix = exclusion.split(":", 1)[0].strip().lower()
            if prefix not in self._STRUCTURED_EXCEPTION_TYPES:
                continue
            match = re.fullmatch(r"([^:]+):\s*(.+?)\s+-\s+(.+)", exclusion.strip())
            if not match or not all(part.strip() for part in match.groups()):
                raise ValueError(
                    f"{prefix} exclusions must document a reason and subject"
                )

    def exception_reason(self, decision_type: str, subject: str) -> Optional[str]:
        """Return the documented reason for a qualified SEO-default exception."""
        normalized_type = decision_type.strip().lower()
        normalized_subject = subject.strip().casefold()
        for exclusion in self.exclusions:
            match = re.fullmatch(r"([^:]+):\s*(.+?)\s+-\s+(.+)", exclusion.strip())
            if not match:
                continue
            candidate_type, candidate_subject, reason = match.groups()
            if (
                candidate_type.strip().lower() == normalized_type
                and candidate_subject.strip().casefold() == normalized_subject
            ):
                return reason.strip()
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_reader": self.primary_reader,
            "sophistication_level": self.sophistication_level,
            "trigger_problem": self.trigger_problem,
            "existing_belief": self.existing_belief,
            "decision_task_helped": self.decision_task_helped,
            "distinctive_angle": self.distinctive_angle,
            "promised_payoff": self.promised_payoff,
            "funnel_stage": self.funnel_stage.value,
            "exclusions": self.exclusions,
        }


@dataclass
class SectionPlan:
    """Detailed plan for a single article section."""
    section_number: int
    section_type: SectionType
    heading: str
    word_target: int
    strategic_angle: str
    engagement_hook: Optional[str] = None
    knowledge_gaps_addressed: List[str] = field(default_factory=list)
    unique_data_to_include: List[str] = field(default_factory=list)
    internal_links: List[str] = field(default_factory=list)
    cta_type: Optional[CTAType] = None
    mini_story_planned: bool = False
    featured_snippet_target: bool = False
    next_action_type: Optional[CTAType] = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.section_number, bool)
            or not isinstance(self.section_number, int)
            or self.section_number <= 0
        ):
            raise ValueError("section_number must be a positive integer")
        if not isinstance(self.section_type, SectionType):
            raise ValueError("section_type must be a SectionType value")
        for field_name in ("heading", "strategic_angle"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if (
            isinstance(self.word_target, bool)
            or not isinstance(self.word_target, int)
            or self.word_target <= 0
        ):
            raise ValueError("word_target must be a positive integer")
        if self.engagement_hook is not None and (
            not isinstance(self.engagement_hook, str)
            or not self.engagement_hook.strip()
        ):
            raise ValueError("engagement_hook must be a non-empty string or None")
        for field_name in (
            "knowledge_gaps_addressed",
            "unique_data_to_include",
            "internal_links",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, list) or any(
                not isinstance(item, str) or not item.strip() for item in values
            ):
                raise ValueError(f"{field_name} must be a list of non-empty strings")
        for field_name in ("cta_type", "next_action_type"):
            value = getattr(self, field_name)
            if value is not None and not isinstance(value, CTAType):
                raise ValueError(f"{field_name} must be a CTAType value or None")
        for field_name in ("mini_story_planned", "featured_snippet_target"):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{field_name} must be a boolean")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_number": self.section_number,
            "type": self.section_type.value,
            "heading": self.heading,
            "word_target": self.word_target,
            "strategic_angle": self.strategic_angle,
            "engagement_hook": self.engagement_hook,
            "knowledge_gaps": self.knowledge_gaps_addressed,
            "unique_data": self.unique_data_to_include,
            "internal_links": self.internal_links,
            "cta": self.cta_type.value if self.cta_type else None,
            "next_action": self.next_action_type.value if self.next_action_type else None,
            "mini_story": self.mini_story_planned,
            "featured_snippet": self.featured_snippet_target
        }


@dataclass
class MetaElements:
    """Meta elements for the article."""
    title_options: List[str]
    meta_title: str
    meta_description: str
    url_slug: str
    primary_keyword: str
    secondary_keywords: List[str]

    def __post_init__(self) -> None:
        if not isinstance(self.title_options, list) or not self.title_options or any(
            not isinstance(item, str) or not item.strip()
            for item in self.title_options
        ):
            raise ValueError("title_options must be a non-empty list of non-empty strings")
        for field_name in (
            "meta_title",
            "meta_description",
            "url_slug",
            "primary_keyword",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isinstance(self.secondary_keywords, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in self.secondary_keywords
        ):
            raise ValueError("secondary_keywords must be a list of non-empty strings")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title_options": self.title_options,
            "meta_title": self.meta_title,
            "meta_description": self.meta_description,
            "url_slug": self.url_slug,
            "primary_keyword": self.primary_keyword,
            "secondary_keywords": self.secondary_keywords
        }


@dataclass
class EngagementMap:
    """Maps engagement elements to sections."""
    mini_story_locations: List[int]  # Legacy field: optional editorial scene section numbers
    cta_locations: Dict[str, int]  # CTA/next-action role -> section number
    featured_snippet_sections: List[int]
    next_action_locations: Dict[str, int] = field(default_factory=dict)
    cta_exception_reason: Optional[str] = None

    def __post_init__(self) -> None:
        for field_name, values in (
            ("mini_story_locations", self.mini_story_locations),
            ("featured_snippet_sections", self.featured_snippet_sections),
        ):
            if not isinstance(values, list) or any(
                isinstance(item, bool)
                or not isinstance(item, int)
                or item <= 0
                for item in values
            ):
                raise ValueError(f"{field_name} must be a list of positive integers")
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must contain distinct section numbers")
        if len(self.mini_story_locations) > 2:
            raise ValueError("mini_story_locations allows at most two sections")

        for field_name, locations in (
            ("cta_locations", self.cta_locations),
            ("next_action_locations", self.next_action_locations),
        ):
            if not isinstance(locations, dict):
                raise ValueError(f"{field_name} must be a dictionary")
            for role, section_number in locations.items():
                try:
                    CTAType(role)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"{field_name} contains an unsupported role: {role}"
                    ) from exc
                if (
                    isinstance(section_number, bool)
                    or not isinstance(section_number, int)
                    or section_number <= 0
                ):
                    raise ValueError(
                        f"{field_name} values must be positive section numbers"
                    )
            if len(locations.values()) != len(set(locations.values())):
                raise ValueError(f"{field_name} must use distinct section numbers")

        if set(self.cta_locations.values()) & set(self.next_action_locations.values()):
            raise ValueError(
                "cta_locations and next_action_locations cannot share a section"
            )
        if self.cta_exception_reason is not None and (
            not isinstance(self.cta_exception_reason, str)
            or not self.cta_exception_reason.strip()
        ):
            raise ValueError("cta_exception_reason must be a non-empty string or None")
        if self.cta_exception_reason is not None and self.cta_locations:
            raise ValueError(
                "cta_exception_reason requires cta_locations to be empty"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mini_stories": self.mini_story_locations,
            "ctas": self.cta_locations,
            "featured_snippets": self.featured_snippet_sections,
            "next_actions": self.next_action_locations,
            "cta_exception_reason": self.cta_exception_reason,
        }


@dataclass
class ArticlePlan:
    """Complete article plan ready for section-by-section writing."""
    topic: str
    date: str
    meta: MetaElements
    total_word_target: int
    sections: List[SectionPlan]
    engagement_map: EngagementMap
    gap_to_section_mapping: Dict[str, int]  # gap description -> section number
    insight_to_section_mapping: Dict[str, int]  # insight -> section number
    reader_contract: ReaderContract
    dominant_content_type: Optional[str] = None
    selected_content_type: Optional[str] = None
    observed_serp_features: Optional[List[str]] = None
    targeted_serp_features: Optional[List[str]] = None
    must_fill_gaps: Optional[List[str]] = None
    included_gaps: Optional[List[str]] = None
    observed_must_have_sections: Optional[List[str]] = None
    included_must_have_sections: Optional[List[str]] = None
    serp_strategy_decisions: Optional[Dict[str, Any]] = field(
        init=False,
        default=None,
        repr=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.topic, str) or not self.topic.strip():
            raise ValueError("topic must be a non-empty string")
        if not isinstance(self.date, str) or not self.date.strip():
            raise ValueError("date must be a non-empty string")
        if not isinstance(self.meta, MetaElements):
            raise ValueError("meta must be a MetaElements value")
        if not isinstance(self.engagement_map, EngagementMap):
            raise ValueError("engagement_map must be an EngagementMap value")
        if not isinstance(self.reader_contract, ReaderContract):
            raise ValueError("reader_contract must be a ReaderContract value")
        if (
            isinstance(self.total_word_target, bool)
            or not isinstance(self.total_word_target, int)
            or self.total_word_target <= 0
        ):
            raise ValueError("total_word_target must be a positive integer")
        if not isinstance(self.sections, list) or not self.sections or any(
            not isinstance(section, SectionPlan) for section in self.sections
        ):
            raise ValueError("sections must be a non-empty list of SectionPlan values")
        section_numbers = [section.section_number for section in self.sections]
        expected_section_numbers = list(range(1, len(self.sections) + 1))
        if section_numbers != expected_section_numbers:
            raise ValueError(
                "sections must use contiguous section numbers starting at 1"
            )
        section_total = sum(section.word_target for section in self.sections)
        if section_total != self.total_word_target:
            raise ValueError(
                "total_word_target must equal the sum of section word targets "
                f"({section_total})"
            )

        valid_section_numbers = set(expected_section_numbers)
        engagement_references = (
            self.engagement_map.mini_story_locations
            + self.engagement_map.featured_snippet_sections
            + list(self.engagement_map.cta_locations.values())
            + list(self.engagement_map.next_action_locations.values())
        )
        if any(
            section_number not in valid_section_numbers
            for section_number in engagement_references
        ):
            raise ValueError(
                "engagement_map contains a section reference outside the article plan"
            )
        for section in self.sections:
            planned_cta = next(
                (
                    CTAType(role)
                    for role, section_number in self.engagement_map.cta_locations.items()
                    if section_number == section.section_number
                ),
                None,
            )
            if section.cta_type != planned_cta:
                raise ValueError(
                    f"Section {section.section_number} CTA assignment must match engagement_map"
                )
            planned_next_action = next(
                (
                    CTAType(role)
                    for role, section_number in self.engagement_map.next_action_locations.items()
                    if section_number == section.section_number
                ),
                None,
            )
            if section.next_action_type != planned_next_action:
                raise ValueError(
                    f"Section {section.section_number} next-action assignment must match engagement_map"
                )
            scene_planned = (
                section.section_number in self.engagement_map.mini_story_locations
            )
            if section.mini_story_planned != scene_planned:
                raise ValueError(
                    f"Section {section.section_number} editorial-scene assignment must match engagement_map"
                )
            featured_snippet_planned = (
                section.section_number
                in self.engagement_map.featured_snippet_sections
            )
            if section.featured_snippet_target != featured_snippet_planned:
                raise ValueError(
                    f"Section {section.section_number} featured-snippet assignment "
                    "must match engagement_map"
                )

        stage = self.reader_contract.funnel_stage
        stage_exception = self.reader_contract.exception_reason("cta", stage.value)
        map_exception = self.engagement_map.cta_exception_reason
        if map_exception is not None:
            if stage_exception != map_exception:
                raise ValueError(
                    "cta_exception_reason must match the documented Reader Contract "
                    f"exception for funnel stage {stage.value}"
                )
            expected_engagement = ArticlePlanner().plan_engagement_distribution(
                len(self.sections),
                stage,
                cta_exception_reason=map_exception,
            )
        else:
            if stage_exception is not None:
                raise ValueError(
                    "The Reader Contract CTA exception must be applied to the engagement map"
                )
            include_optional_tofu_cta = bool(self.engagement_map.cta_locations)
            expected_engagement = ArticlePlanner().plan_engagement_distribution(
                len(self.sections),
                stage,
                include_optional_tofu_cta=include_optional_tofu_cta,
            )
        if (
            self.engagement_map.cta_locations != expected_engagement.cta_locations
            or self.engagement_map.next_action_locations
            != expected_engagement.next_action_locations
        ):
            raise ValueError(
                "engagement_map CTA and next-action assignments must match the "
                f"Reader Contract funnel stage {stage.value}"
            )
        for field_name in (
            "gap_to_section_mapping",
            "insight_to_section_mapping",
        ):
            mapping = getattr(self, field_name)
            if not isinstance(mapping, dict) or any(
                not isinstance(label, str)
                or not label.strip()
                or isinstance(section_number, bool)
                or not isinstance(section_number, int)
                or section_number not in valid_section_numbers
                for label, section_number in mapping.items()
            ):
                raise ValueError(
                    f"{field_name} must map non-empty strings to valid section numbers"
                )

        strategy_inputs = (
            self.dominant_content_type,
            self.selected_content_type,
            self.observed_serp_features,
            self.targeted_serp_features,
            self.must_fill_gaps,
            self.included_gaps,
        )
        if all(value is None for value in strategy_inputs):
            if (
                self.observed_must_have_sections is not None
                or self.included_must_have_sections is not None
            ):
                raise ValueError(
                    "ArticlePlan SERP structure context requires the full SERP strategy context"
                )
            self.serp_strategy_decisions = {
                "status": "unresolved_no_verified_serp_context",
                "content_type": {
                    "observed": None,
                    "selected": None,
                    "status": "unresolved",
                },
                "serp_features": {},
                "serp_structure": {},
                "competitor_gaps": {},
                "exception_reasons": {
                    "serp_features": {},
                    "serp_structure": {},
                    "competitor_gaps": {},
                },
            }
            return
        if any(value is None for value in strategy_inputs):
            raise ValueError(
                "ArticlePlan SERP strategy context must supply content types, "
                "feature lists, and gap lists together"
            )
        if (self.observed_must_have_sections is None) != (
            self.included_must_have_sections is None
        ):
            raise ValueError(
                "ArticlePlan SERP structure context must supply observed and included "
                "must-have sections together"
            )
        self.serp_strategy_decisions = ArticlePlanner().validate_serp_strategy(
            reader_contract=self.reader_contract,
            dominant_content_type=self.dominant_content_type,
            selected_content_type=self.selected_content_type,
            observed_serp_features=self.observed_serp_features,
            targeted_serp_features=self.targeted_serp_features,
            must_fill_gaps=self.must_fill_gaps,
            included_gaps=self.included_gaps,
            observed_must_have_sections=self.observed_must_have_sections,
            included_must_have_sections=self.included_must_have_sections,
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "topic": self.topic,
            "date": self.date,
            "meta": self.meta.to_dict(),
            "total_word_target": self.total_word_target,
            "sections": [s.to_dict() for s in self.sections],
            "engagement_map": self.engagement_map.to_dict(),
            "gap_mapping": self.gap_to_section_mapping,
            "insight_mapping": self.insight_to_section_mapping,
            "reader_contract": self.reader_contract.to_dict(),
        }
        result["serp_strategy"] = self.serp_strategy_decisions
        return result


class ArticlePlanner:
    """
    Creates strategic article plans from research.

    This class provides structure and logic for the /article command
    to use when creating section-by-section writing plans.
    """

    # Keywords that indicate section type
    SECTION_TYPE_KEYWORDS = {
        SectionType.BODY_HOW_TO: ['how to', 'steps', 'guide', 'tutorial', 'process'],
        SectionType.BODY_COMPARISON: ['vs', 'compare', 'versus', 'difference', 'best'],
        SectionType.BODY_EXPLANATION: ['what is', 'why', 'overview', 'understand'],
        SectionType.BODY_LIST: ['top', 'best', 'tips', 'ways', 'methods', 'strategies'],
        SectionType.FAQ: ['faq', 'questions', 'asked'],
        SectionType.CONCLUSION: ['conclusion', 'summary', 'final', 'next step', 'wrap'],
    }

    @staticmethod
    def _validate_strategy_items(name: str, items: List[str]) -> None:
        if not isinstance(items, list) or any(
            not isinstance(item, str) or not item.strip() for item in items
        ):
            raise ValueError(f"{name} must be a list of non-empty strings")

    def validate_serp_strategy(
        self,
        reader_contract: ReaderContract,
        dominant_content_type: str,
        selected_content_type: str,
        observed_serp_features: List[str],
        targeted_serp_features: List[str],
        must_fill_gaps: List[str],
        included_gaps: List[str],
        observed_must_have_sections: Optional[List[str]] = None,
        included_must_have_sections: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Enforce strong SERP defaults or a reasoned Reader Contract exception."""
        if not isinstance(reader_contract, ReaderContract):
            raise ValueError("reader_contract must be a ReaderContract")
        for name, value in (
            ("dominant_content_type", dominant_content_type),
            ("selected_content_type", selected_content_type),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        for name, values in (
            ("observed_serp_features", observed_serp_features),
            ("targeted_serp_features", targeted_serp_features),
            ("must_fill_gaps", must_fill_gaps),
            ("included_gaps", included_gaps),
        ):
            self._validate_strategy_items(name, values)
        if (observed_must_have_sections is None) != (
            included_must_have_sections is None
        ):
            raise ValueError(
                "observed_must_have_sections and included_must_have_sections "
                "must be supplied together"
            )
        observed_must_have_sections = observed_must_have_sections or []
        included_must_have_sections = included_must_have_sections or []
        self._validate_strategy_items(
            "observed_must_have_sections", observed_must_have_sections
        )
        self._validate_strategy_items(
            "included_must_have_sections", included_must_have_sections
        )

        observed_features = {item.casefold() for item in observed_serp_features}
        targeted = {item.casefold() for item in targeted_serp_features}
        qualified_gaps = {item.casefold() for item in must_fill_gaps}
        included = {item.casefold() for item in included_gaps}
        observed_structure = {
            item.casefold() for item in observed_must_have_sections
        }
        included_structure = {
            item.casefold() for item in included_must_have_sections
        }
        if not targeted.issubset(observed_features):
            raise ValueError(
                "targeted_serp_features must contain only observed SERP features"
            )
        if not included.issubset(qualified_gaps):
            raise ValueError("included_gaps must contain only must_fill_gaps")
        if not included_structure.issubset(observed_structure):
            raise ValueError(
                "included_must_have_sections must contain only observed must-have sections"
            )
        decisions: Dict[str, Any] = {
            "content_type": {
                "observed": dominant_content_type,
                "selected": selected_content_type,
                "status": "matched_default",
            },
            "serp_features": {},
            "serp_structure": {},
            "competitor_gaps": {},
            "exception_reasons": {
                "serp_features": {},
                "serp_structure": {},
                "competitor_gaps": {},
            },
        }

        if dominant_content_type.casefold() != selected_content_type.casefold():
            reason = reader_contract.exception_reason(
                "content_type", dominant_content_type
            )
            if not reason:
                raise ValueError(
                    "content_type deviation from "
                    f"{dominant_content_type} requires a documented Reader Contract reason"
                )
            decisions["content_type"].update(
                status="documented_exception",
                reason=reason,
            )

        for feature in observed_serp_features:
            if feature.casefold() in targeted:
                decisions["serp_features"][feature] = "targeted"
                continue
            reason = reader_contract.exception_reason("serp_feature", feature)
            if not reason:
                raise ValueError(
                    f"serp_feature {feature} requires targeting or a documented "
                    "Reader Contract reason"
                )
            decisions["serp_features"][feature] = "documented_exception"
            decisions["exception_reasons"]["serp_features"][feature] = reason

        for section in observed_must_have_sections:
            if section.casefold() in included_structure:
                decisions["serp_structure"][section] = "included"
                continue
            reason = reader_contract.exception_reason("serp_structure", section)
            if not reason:
                raise ValueError(
                    f"serp_structure {section} requires inclusion or a documented "
                    "Reader Contract reason"
                )
            decisions["serp_structure"][section] = "documented_exception"
            decisions["exception_reasons"]["serp_structure"][section] = reason

        for gap in must_fill_gaps:
            if gap.casefold() in included:
                decisions["competitor_gaps"][gap] = "included"
                continue
            reason = reader_contract.exception_reason("competitor_gap", gap)
            if not reason:
                raise ValueError(
                    f"competitor_gap {gap} requires inclusion or a documented "
                    "Reader Contract reason"
                )
            decisions["competitor_gaps"][gap] = "documented_exception"
            decisions["exception_reasons"]["competitor_gaps"][gap] = reason

        return decisions

    def classify_section_type(self, heading: str) -> SectionType:
        """
        Classify a section heading into a section type.

        Args:
            heading: The H2 heading text

        Returns:
            SectionType enum value
        """
        heading_lower = heading.lower()

        for section_type, keywords in self.SECTION_TYPE_KEYWORDS.items():
            if any(kw in heading_lower for kw in keywords):
                return section_type

        return SectionType.BODY_EXPLANATION  # Default

    def plan_engagement_distribution(
        self,
        num_sections: int,
        funnel_stage: Optional[FunnelStage] = None,
        editorial_scene_locations: Optional[List[int]] = None,
        include_optional_tofu_cta: bool = False,
        cta_exception_reason: Optional[str] = None,
    ) -> EngagementMap:
        """
        Plan where engagement elements should go.

        Args:
            num_sections: Total number of sections
            funnel_stage: Reader Contract stage. None means no inferred CTA.
            editorial_scene_locations: Explicit 0-2 scene locations.
            include_optional_tofu_cta: Whether ToFu receives its optional soft CTA.
            cta_exception_reason: Documented Reader Contract reason to suppress stage CTAs.

        Returns:
            EngagementMap with locations
        """
        if (
            not isinstance(num_sections, int)
            or isinstance(num_sections, bool)
            or num_sections < 1
        ):
            raise ValueError("num_sections must be a positive integer")
        if funnel_stage is not None and not isinstance(funnel_stage, FunnelStage):
            raise ValueError("funnel_stage must be a FunnelStage value or None")
        if not isinstance(include_optional_tofu_cta, bool):
            raise ValueError("include_optional_tofu_cta must be a boolean")
        if include_optional_tofu_cta and funnel_stage != FunnelStage.TOFU:
            raise ValueError("include_optional_tofu_cta is only valid for tofu")
        if cta_exception_reason is not None and (
            not isinstance(cta_exception_reason, str)
            or not cta_exception_reason.strip()
        ):
            raise ValueError("cta_exception_reason must be a non-empty string or None")
        if cta_exception_reason is not None and funnel_stage not in (
            FunnelStage.MOFU,
            FunnelStage.BOFU,
        ):
            raise ValueError(
                "cta_exception_reason is valid only for mofu or bofu CTA defaults"
            )
        if include_optional_tofu_cta and cta_exception_reason is not None:
            raise ValueError(
                "include_optional_tofu_cta cannot be combined with cta_exception_reason"
            )
        if editorial_scene_locations is not None and not isinstance(
            editorial_scene_locations,
            list,
        ):
            raise ValueError("editorial_scene_locations must be a list")

        mini_story_locations = editorial_scene_locations or []
        if len(mini_story_locations) > 2:
            raise ValueError("editorial_scene_locations allows at most 2 distinct sections")
        for location in mini_story_locations:
            if not isinstance(location, int) or isinstance(location, bool):
                raise ValueError("editorial_scene_locations must contain integers")
            if location < 1 or location > num_sections:
                raise ValueError(
                    f"editorial scene locations must be between 1 and {num_sections}"
                )
        if len(set(mini_story_locations)) != len(mini_story_locations):
            raise ValueError("editorial_scene_locations must contain distinct sections")

        cta_locations: Dict[str, int] = {}
        next_action_locations: Dict[str, int] = {}
        if cta_exception_reason is not None:
            cta_locations = {}
            next_action_locations = {"educational_next_step": num_sections}
        elif funnel_stage == FunnelStage.TOFU and include_optional_tofu_cta:
            cta_locations = {"soft_resource_action": min(2, num_sections)}
        elif funnel_stage == FunnelStage.MOFU:
            if num_sections < 2:
                raise ValueError("mofu engagement planning requires at least 2 sections")
            cta_locations = {
                "educational_next_step": 1 if num_sections == 2 else 2,
                "contextual_product": num_sections,
            }
        elif funnel_stage == FunnelStage.BOFU:
            if num_sections < 2:
                raise ValueError("bofu engagement planning requires at least 2 sections")
            if num_sections == 2:
                cta_locations = {
                    "commercial_contextual": 1,
                    "commercial_conversion": 2,
                }
            else:
                first = 1 if num_sections == 3 else 2
                middle = max(first + 1, num_sections // 2 + 1)
                middle = min(middle, num_sections - 1)
                cta_locations = {
                    "commercial_contextual": first,
                    "commercial_comparison": middle,
                    "commercial_conversion": num_sections,
                }
        elif funnel_stage == FunnelStage.THOUGHT_LEADERSHIP:
            next_action_locations = {"thought_leadership_next_action": num_sections}

        # Featured snippets: FAQ and definition sections
        featured_snippets = []  # Will be identified during planning

        return EngagementMap(
            mini_story_locations=mini_story_locations,
            cta_locations=cta_locations,
            featured_snippet_sections=featured_snippets,
            next_action_locations=next_action_locations,
            cta_exception_reason=(
                cta_exception_reason.strip() if cta_exception_reason is not None else None
            ),
        )

    def create_section_plan(
        self,
        section_number: int,
        heading: str,
        gaps_to_address: List[str],
        insights_to_include: List[str],
        internal_links: List[str],
        engagement_map: EngagementMap,
        word_target: int,
    ) -> SectionPlan:
        """
        Create a detailed plan for a single section.

        Args:
            section_number: Position in article (1-indexed)
            heading: H2 heading text
            gaps_to_address: Competitor gaps this section should fill
            insights_to_include: Social research insights to use
            internal_links: Your pages to link
            engagement_map: Overall engagement distribution plan
            word_target: Intent/evidence-complete target resolved by the caller

        Returns:
            SectionPlan with all details
        """
        if not isinstance(word_target, int) or isinstance(word_target, bool) or word_target <= 0:
            raise ValueError("word_target must be a positive integer")

        section_type = self.classify_section_type(heading)

        # Special handling for intro
        if section_number == 1:
            section_type = SectionType.INTRO

        # Special handling for FAQ
        if 'faq' in heading.lower() or 'question' in heading.lower():
            section_type = SectionType.FAQ

        # Determine CTA type if applicable
        cta_type = None
        for cta, section_num in engagement_map.cta_locations.items():
            if section_num == section_number:
                cta_type = CTAType(cta)
                break

        next_action_type = None
        for next_action, section_num in engagement_map.next_action_locations.items():
            if section_num == section_number:
                next_action_type = CTAType(next_action)
                break

        # Check if an optional editorial scene is planned here.
        mini_story = section_number in engagement_map.mini_story_locations

        # Use only the verified feature target supplied by the engagement map.
        featured_snippet = section_number in engagement_map.featured_snippet_sections

        return SectionPlan(
            section_number=section_number,
            section_type=section_type,
            heading=heading,
            word_target=word_target,
            strategic_angle=self._generate_angle(heading, gaps_to_address),
            engagement_hook=self._generate_hook_idea(section_type, insights_to_include),
            knowledge_gaps_addressed=gaps_to_address,
            unique_data_to_include=insights_to_include,
            internal_links=internal_links,
            cta_type=cta_type,
            next_action_type=next_action_type,
            mini_story_planned=mini_story,
            featured_snippet_target=featured_snippet
        )

    def _generate_angle(
        self,
        heading: str,
        gaps: List[str]
    ) -> str:
        """Generate a strategic angle description."""
        if gaps:
            return f"Address competitor gaps: {', '.join(gaps[:2])}"
        return f"Comprehensive coverage of {heading}"

    def _generate_hook_idea(
        self,
        section_type: SectionType,
        insights: List[str]
    ) -> str:
        """Generate engagement hook suggestion."""
        if section_type == SectionType.INTRO:
            return "Open with scenario/question based on social research pain points"
        elif section_type == SectionType.BODY_HOW_TO:
            return "Lead with the outcome readers will achieve"
        elif section_type == SectionType.BODY_COMPARISON:
            return "Start with the key differentiator"
        elif section_type == SectionType.FAQ:
            return "Use real questions from Reddit/YouTube research"
        else:
            return "Connect to reader's situation immediately"


def format_article_plan(plan: ArticlePlan) -> str:
    """
    Format article plan as markdown.

    This generates the article-plan-[topic]-[date].md file.
    """
    contract = plan.reader_contract
    exclusions = "; ".join(contract.exclusions) if contract.exclusions else "None"
    report = f"""# Article Plan: {plan.topic}

**Date**: {plan.date}
**Total Word Target**: {plan.total_word_target} words
**Primary Keyword**: {plan.meta.primary_keyword}
**Secondary Keywords**: {', '.join(plan.meta.secondary_keywords)}

## Reader Contract
- **Primary reader**: {contract.primary_reader}
- **Sophistication level**: {contract.sophistication_level}
- **Trigger problem**: {contract.trigger_problem}
- **Existing belief**: {contract.existing_belief}
- **Decision or task helped**: {contract.decision_task_helped}
- **Distinctive angle**: {contract.distinctive_angle}
- **Promised payoff**: {contract.promised_payoff}
- **Funnel stage**: {contract.funnel_stage.value}
- **Exclusions**: {exclusions}
"""
    if plan.serp_strategy_decisions.get("status") == "unresolved_no_verified_serp_context":
        report += """
## SERP Strategy Decision
- **Observation**: Unresolved because no verified SERP strategy context was supplied
- **Default recommendation**: Pending verified dominant content type, observed features, recurring structure, and qualified must-fill gaps
- **Exception decision**: None; no deviation may be inferred from this unresolved state
- **Proof status**: No SERP observation is claimed; public claims still require approved proof
"""
    else:
        decisions = plan.serp_strategy_decisions
        report += f"""
## SERP Strategy Decision
- **Observed dominant content type**: {plan.dominant_content_type}
- **Selected content type**: {plan.selected_content_type}
- **Content-type decision**: {decisions['content_type']['status']}{f" - {decisions['content_type']['reason']}" if decisions['content_type'].get('reason') else ''}
"""
        for feature, status in decisions["serp_features"].items():
            reason = decisions["exception_reasons"]["serp_features"].get(feature)
            suffix = f" - {reason}" if reason else ""
            report += f"- **SERP feature**: {feature}: {status}{suffix}\n"
        for section, status in decisions["serp_structure"].items():
            reason = decisions["exception_reasons"]["serp_structure"].get(section)
            suffix = f" - {reason}" if reason else ""
            report += f"- **SERP structure**: {section}: {status}{suffix}\n"
        for gap, status in decisions["competitor_gaps"].items():
            reason = decisions["exception_reasons"]["competitor_gaps"].get(gap)
            suffix = f" - {reason}" if reason else ""
            report += f"- **Competitor gap**: {gap}: {status}{suffix}\n"
        report += (
            "- **Proof status**: SERP observations guide structure only; public "
            "claims still require approved proof.\n"
        )

    report += """

---

## Meta Elements

**Title Options:**
"""
    for i, title in enumerate(plan.meta.title_options, 1):
        report += f"{i}. {title}\n"

    report += f"""
**Meta Description**: {plan.meta.meta_description}
**URL Slug**: /blog/{plan.meta.url_slug}

---

## Section Plan

| # | Type | Heading | Words | CTA / Next Action | Editorial Scene |
|---|------|---------|-------|-------------------|------------------|
"""

    for section in plan.sections:
        action = "-"
        if section.cta_type:
            action = f"CTA: {section.cta_type.value}"
        elif section.next_action_type:
            action = f"Next Action: {section.next_action_type.value}"
        story = "Optional" if section.mini_story_planned else "-"
        report += f"| {section.section_number} | {section.section_type.value} | {section.heading} | {section.word_target} | {action} | {story} |\n"

    report += "\n---\n\n## Section Details\n\n"

    for section in plan.sections:
        report += f"""### {section.section_number}. {section.heading}
- **Type**: {section.section_type.value}
- **Word Target**: {section.word_target}
- **Strategic Angle**: {section.strategic_angle}
"""
        if section.engagement_hook:
            report += f"- **Hook**: {section.engagement_hook}\n"
        if section.knowledge_gaps_addressed:
            report += f"- **Gaps Addressed**: {', '.join(section.knowledge_gaps_addressed)}\n"
        if section.unique_data_to_include:
            report += f"- **Unique Data**: {', '.join(section.unique_data_to_include[:3])}\n"
        if section.internal_links:
            report += f"- **Internal Links**: {', '.join(section.internal_links)}\n"
        if section.cta_type:
            report += f"- **CTA Type**: {section.cta_type.value}\n"
        if section.next_action_type:
            report += f"- **Next Action Type**: {section.next_action_type.value}\n"
        if section.mini_story_planned:
            report += "- **Editorial Scene**: Optional unnamed workflow scene, or a named person/business only with approved proof\n"
        if section.featured_snippet_target:
            report += "- **Featured Snippet**: Target for snippet optimization\n"
        report += "\n"

    report += """---

## Engagement Map

| Element | Location |
|---------|----------|
"""
    for loc in plan.engagement_map.mini_story_locations:
        section = plan.sections[loc - 1] if loc <= len(plan.sections) else None
        heading = section.heading if section else f"Section {loc}"
        report += f"| Optional editorial scene | Section {loc}: {heading} |\n"

    for cta_type, loc in plan.engagement_map.cta_locations.items():
        section = plan.sections[loc - 1] if loc <= len(plan.sections) else None
        heading = section.heading if section else f"Section {loc}"
        report += f"| CTA ({cta_type}) | Section {loc}: {heading} |\n"

    for action_type, loc in plan.engagement_map.next_action_locations.items():
        section = plan.sections[loc - 1] if loc <= len(plan.sections) else None
        heading = section.heading if section else f"Section {loc}"
        report += f"| Next Action ({action_type}) | Section {loc}: {heading} |\n"

    if plan.engagement_map.cta_exception_reason:
        report += (
            "| CTA exception | "
            f"{plan.engagement_map.cta_exception_reason} |\n"
        )

    report += """
---

## Gap-to-Section Mapping

"""
    if plan.gap_to_section_mapping:
        for gap, section_num in plan.gap_to_section_mapping.items():
            report += f"- **{gap}** → Section {section_num}\n"
    else:
        report += "- No specific gap mappings defined yet\n"

    report += """
## Insight-to-Section Mapping

"""
    if plan.insight_to_section_mapping:
        for insight, section_num in plan.insight_to_section_mapping.items():
            report += f"- **{insight[:50]}...** → Section {section_num}\n"
    else:
        report += "- No specific insight mappings defined yet\n"

    report += """

## Continuity Pass
- [ ] Every section advances the headline promise.
- [ ] Each section answers a question created by the previous section.
- [ ] Repeated resets were removed.
- [ ] Transitions explain a logical relationship.
- [ ] The conclusion completes the introduction.
- [ ] Remove or justify any section that does not increase the promised payoff.
"""

    return report


def create_default_structure(topic: str) -> List[str]:
    """
    Create a default article structure for common topics.

    This provides a starting point that should be modified based
    on competitor research.
    """
    return [
        "Introduction",
        f"What is {topic}?",
        f"Why {topic} Matters",
        f"How to Get Started with {topic}",
        f"Best Practices for {topic}",
        "Common Mistakes to Avoid",
        "Frequently Asked Questions",
        "Conclusion"
    ]


if __name__ == "__main__":
    print("Article Planner")
    print("=" * 50)
    print("This module is used by the /article command")
    print("to create section-by-section article plans.")
    print()
    print("Section Types:")
    for section_type in SectionType:
        print(f"  - {section_type.value}")
    print()
    print("CTA Types:")
    for cta_type in CTAType:
        print(f"  - {cta_type.value}")
