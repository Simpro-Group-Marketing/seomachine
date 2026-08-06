import re
import unittest
from dataclasses import replace
from datetime import datetime

from data_sources.modules.article_planner import (
    ArticlePlan,
    ArticlePlanner,
    CTAType,
    EngagementMap,
    FunnelStage,
    MetaElements,
    ReaderContract,
    SectionPlan,
    SectionType as PlannerSectionType,
    format_article_plan,
)
from data_sources.modules.competitor_gap_analyzer import CompetitorGapAnalyzer
from data_sources.modules.competitor_gap_analyzer import (
    CompetitorAnalysis,
    ContentGap,
    GapPriority,
    GapType,
    format_gap_report,
)
from data_sources.modules.engagement_analyzer import (
    EngagementAnalyzer,
    format_results,
    load_cta_plan,
    parse_cli_args as parse_engagement_cli_args,
)
from data_sources.modules.section_writer import (
    SectionType as WriterSectionType,
    SectionWriter,
    format_writing_prompt,
)
from data_sources.modules.social_research_aggregator import (
    EngagementLevel,
    InsightType,
    RedditInsight,
    RedditResearch,
    SocialResearchAggregator,
    YouTubeResearch,
    format_social_research_report,
)


def reader_contract(
    funnel_stage: FunnelStage = FunnelStage.TOFU,
    exclusions=None,
) -> ReaderContract:
    return ReaderContract(
        primary_reader="Field service operations manager",
        sophistication_level="Intermediate; understands scheduling basics",
        trigger_problem="Recurring dispatch conflicts",
        existing_belief="More scheduling rules will solve the problem",
        decision_task_helped="Choose a practical scheduling workflow",
        distinctive_angle="Separate hard constraints from judgment calls",
        promised_payoff="A workflow the reader can test this month",
        funnel_stage=funnel_stage,
        exclusions=(
            ["Vendor rankings", "Unsupported ROI claims"]
            if exclusions is None
            else exclusions
        ),
    )


def article_plan() -> ArticlePlan:
    section = SectionPlan(
        section_number=1,
        section_type=PlannerSectionType.INTRO,
        heading="Scheduling constraints",
        word_target=275,
        strategic_angle="Start with the dispatch decision",
    )
    return ArticlePlan(
        topic="Field service scheduling",
        date="2026-08-05",
        meta=MetaElements(
            title_options=["Field Service Scheduling Guide"],
            meta_title="Field Service Scheduling Guide for Teams | Simpro",
            meta_description=(
                "Field service scheduling guidance for teams balancing job priority, "
                "technician skills, travel constraints, and customer commitments."
            ),
            url_slug="field-service-scheduling-guide",
            primary_keyword="field service scheduling",
            secondary_keywords=["dispatch workflow"],
        ),
        total_word_target=275,
        sections=[section],
        engagement_map=EngagementMap([], {}, []),
        gap_to_section_mapping={},
        insight_to_section_mapping={},
        reader_contract=reader_contract(),
    )


class ArticlePlannerEditorialContractTests(unittest.TestCase):
    def test_serp_strategy_defaults_require_reasoned_reader_contract_exceptions(self):
        planner = ArticlePlanner()
        contract = reader_contract()

        with self.assertRaisesRegex(ValueError, "content_type.*How-To Guide"):
            planner.validate_serp_strategy(
                reader_contract=contract,
                dominant_content_type="How-To Guide",
                selected_content_type="Comparison",
                observed_serp_features=["people_also_ask", "video"],
                targeted_serp_features=["people_also_ask"],
                must_fill_gaps=["dispatch constraints"],
                included_gaps=[],
            )

        contract.exclusions.extend(
            [
                "content_type: How-To Guide - a comparison better supports the reader decision",
                "serp_feature: video - no verified video input supports the task",
                "competitor_gap: dispatch constraints - approved evidence is unavailable",
            ]
        )
        result = planner.validate_serp_strategy(
            reader_contract=contract,
            dominant_content_type="How-To Guide",
            selected_content_type="Comparison",
            observed_serp_features=["people_also_ask", "video"],
            targeted_serp_features=["people_also_ask"],
            must_fill_gaps=["dispatch constraints"],
            included_gaps=[],
        )

        self.assertEqual(result["content_type"]["status"], "documented_exception")
        self.assertEqual(result["serp_features"]["video"], "documented_exception")
        self.assertEqual(
            result["competitor_gaps"]["dispatch constraints"],
            "documented_exception",
        )

    def test_serp_strategy_requires_must_have_sections_or_documented_exceptions(self):
        planner = ArticlePlanner()
        contract = reader_contract()

        with self.assertRaisesRegex(ValueError, "serp_structure.*pricing factors"):
            planner.validate_serp_strategy(
                reader_contract=contract,
                dominant_content_type="Guide",
                selected_content_type="Guide",
                observed_serp_features=[],
                targeted_serp_features=[],
                must_fill_gaps=[],
                included_gaps=[],
                observed_must_have_sections=["pricing factors"],
                included_must_have_sections=[],
            )

        contract.exclusions.append(
            "serp_structure: pricing factors - pricing is outside this operational brief"
        )
        decisions = planner.validate_serp_strategy(
            reader_contract=contract,
            dominant_content_type="Guide",
            selected_content_type="Guide",
            observed_serp_features=[],
            targeted_serp_features=[],
            must_fill_gaps=[],
            included_gaps=[],
            observed_must_have_sections=["workflow steps", "pricing factors"],
            included_must_have_sections=["workflow steps"],
        )

        self.assertEqual(decisions["serp_structure"]["workflow steps"], "included")
        self.assertEqual(
            decisions["serp_structure"]["pricing factors"],
            "documented_exception",
        )

    def test_serp_strategy_rejects_unobserved_or_unqualified_inclusions(self):
        planner = ArticlePlanner()
        common = {
            "reader_contract": reader_contract(),
            "dominant_content_type": "Guide",
            "selected_content_type": "Guide",
            "observed_serp_features": ["people_also_ask"],
            "targeted_serp_features": ["people_also_ask", "video"],
            "must_fill_gaps": [],
            "included_gaps": [],
        }

        with self.assertRaisesRegex(ValueError, "targeted_serp_features.*observed"):
            planner.validate_serp_strategy(**common)

        common["targeted_serp_features"] = ["people_also_ask"]
        common["included_gaps"] = ["unqualified gap"]
        with self.assertRaisesRegex(ValueError, "included_gaps.*must_fill_gaps"):
            planner.validate_serp_strategy(**common)

    def test_structured_reader_contract_exclusions_require_a_reason(self):
        valid = reader_contract().to_dict()
        valid["funnel_stage"] = FunnelStage.MOFU

        with self.assertRaisesRegex(ValueError, "document a reason"):
            ReaderContract(
                **{
                    **valid,
                    "exclusions": ["serp_feature: video"],
                }
            )

    def test_reader_contract_rejects_missing_or_invalid_required_fields(self):
        valid = {
            "primary_reader": "Field service operations manager",
            "sophistication_level": "Intermediate",
            "trigger_problem": "Recurring dispatch conflicts",
            "existing_belief": "More rules will solve the problem",
            "decision_task_helped": "Choose a scheduling workflow",
            "distinctive_angle": "Separate constraints from judgment",
            "promised_payoff": "A workflow the reader can test",
            "funnel_stage": FunnelStage.MOFU,
            "exclusions": [],
        }

        for field_name in [
            "primary_reader",
            "sophistication_level",
            "trigger_problem",
            "existing_belief",
            "decision_task_helped",
            "distinctive_angle",
            "promised_payoff",
        ]:
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(ValueError, field_name):
                    ReaderContract(**{**valid, field_name: " "})
        with self.assertRaisesRegex(ValueError, "funnel_stage"):
            ReaderContract(**{**valid, "funnel_stage": "mofu"})
        with self.assertRaisesRegex(ValueError, "exclusions"):
            ReaderContract(**{**valid, "exclusions": ("Vendor rankings",)})
        with self.assertRaisesRegex(ValueError, "exclusions"):
            ReaderContract(**{**valid, "exclusions": [""]})

    def test_article_plan_serializes_and_renders_reader_contract_and_continuity_pass(self):
        plan = article_plan()

        serialized = plan.to_dict()
        rendered = format_article_plan(plan)

        self.assertEqual(
            serialized["serp_strategy"]["status"],
            "unresolved_no_verified_serp_context",
        )
        self.assertIn("No SERP observation is claimed", rendered)
        self.assertEqual(
            serialized["reader_contract"],
            {
                "primary_reader": "Field service operations manager",
                "sophistication_level": "Intermediate; understands scheduling basics",
                "trigger_problem": "Recurring dispatch conflicts",
                "existing_belief": "More scheduling rules will solve the problem",
                "decision_task_helped": "Choose a practical scheduling workflow",
                "distinctive_angle": "Separate hard constraints from judgment calls",
                "promised_payoff": "A workflow the reader can test this month",
                "funnel_stage": "tofu",
                "exclusions": ["Vendor rankings", "Unsupported ROI claims"],
            },
        )
        for expected in [
            "## Reader Contract",
            "Field service operations manager",
            "## Continuity Pass",
            "Every section advances the headline promise",
            "Each section answers a question created by the previous section",
            "Repeated resets were removed",
            "Transitions explain a logical relationship",
            "The conclusion completes the introduction",
            "Remove or justify any section that does not increase the promised payoff",
        ]:
            self.assertIn(expected, rendered)

    def test_article_plan_enforces_and_renders_supplied_serp_strategy_context(self):
        contract = replace(
            reader_contract(),
            exclusions=[
                "serp_feature: video - no verified video input supports the task",
            ],
        )
        plan = replace(
            article_plan(),
            reader_contract=contract,
            dominant_content_type="How-To Guide",
            selected_content_type="How-To Guide",
            observed_serp_features=["people_also_ask", "video"],
            targeted_serp_features=["people_also_ask"],
            must_fill_gaps=["dispatch constraints"],
            included_gaps=["dispatch constraints"],
        )

        serialized = plan.to_dict()
        rendered = format_article_plan(plan)

        self.assertEqual(
            serialized["serp_strategy"]["content_type"]["status"],
            "matched_default",
        )
        self.assertIn("## SERP Strategy Decision", rendered)
        self.assertIn("video: documented_exception", rendered)
        self.assertEqual(
            serialized["serp_strategy"]["exception_reasons"]["serp_features"]["video"],
            "no verified video input supports the task",
        )
        self.assertIn(
            "video: documented_exception - no verified video input supports the task",
            rendered,
        )
        self.assertIn("dispatch constraints: included", rendered)

        with self.assertRaisesRegex(ValueError, "serp_feature video"):
            replace(plan, reader_contract=reader_contract())

    def test_article_plan_preserves_and_renders_content_type_exception_reason(self):
        contract = replace(
            reader_contract(),
            exclusions=[
                "content_type: How-To Guide - a comparison supports the reader decision",
            ],
        )
        plan = replace(
            article_plan(),
            reader_contract=contract,
            dominant_content_type="How-To Guide",
            selected_content_type="Comparison",
            observed_serp_features=[],
            targeted_serp_features=[],
            must_fill_gaps=[],
            included_gaps=[],
        )

        serialized = plan.to_dict()["serp_strategy"]
        rendered = format_article_plan(plan)

        self.assertEqual(serialized["content_type"]["observed"], "How-To Guide")
        self.assertEqual(
            serialized["content_type"]["reason"],
            "a comparison supports the reader decision",
        )
        self.assertIn(
            "documented_exception - a comparison supports the reader decision",
            rendered,
        )

    def test_article_plan_rejects_incoherent_section_and_engagement_references(self):
        base = article_plan()

        with self.assertRaisesRegex(ValueError, "contiguous"):
            replace(
                base,
                sections=[replace(base.sections[0], section_number=2)],
            )
        with self.assertRaisesRegex(ValueError, "engagement_map"):
            replace(base, engagement_map=EngagementMap([], {"soft": 2}, []))
        with self.assertRaisesRegex(ValueError, "gap_to_section_mapping"):
            replace(base, gap_to_section_mapping={"dispatch gap": 2})
        with self.assertRaisesRegex(ValueError, "CTA assignment"):
            replace(base, engagement_map=EngagementMap([], {"soft": 1}, []))

    def test_section_and_engagement_artifacts_validate_direct_construction(self):
        base_section = article_plan().sections[0]

        with self.assertRaisesRegex(ValueError, "section_number"):
            replace(base_section, section_number=True)
        with self.assertRaisesRegex(ValueError, "word_target"):
            replace(base_section, word_target=0)
        with self.assertRaisesRegex(ValueError, "heading"):
            replace(base_section, heading=" ")
        with self.assertRaisesRegex(ValueError, "mini_story_locations"):
            EngagementMap([1, 1], {}, [])
        with self.assertRaisesRegex(ValueError, "cta_locations"):
            EngagementMap([], {"unknown_cta": 1}, [])
        with self.assertRaisesRegex(ValueError, "cta_exception_reason"):
            EngagementMap([], {"soft": 1}, [], cta_exception_reason="Excluded")
        with self.assertRaisesRegex(ValueError, "meta_title"):
            replace(article_plan().meta, meta_title=" ")

    def test_section_plan_preserves_legacy_positional_field_order(self):
        section = SectionPlan(
            1,
            PlannerSectionType.INTRO,
            "Scheduling pressure",
            200,
            "Open with the dispatch decision",
            None,
            [],
            [],
            [],
            None,
            True,
            False,
        )

        self.assertTrue(section.mini_story_planned)
        self.assertFalse(section.featured_snippet_target)
        self.assertIsNone(section.next_action_type)

    def test_article_plan_requires_stage_coherent_engagement_map(self):
        plan = article_plan()

        with self.assertRaisesRegex(ValueError, "mofu|funnel stage"):
            replace(plan, reader_contract=reader_contract(FunnelStage.MOFU))

        reason = "No relevant product action supports this reader task"
        exception_plan = replace(
            plan,
            reader_contract=reader_contract(
                FunnelStage.MOFU,
                [f"cta: mofu - {reason}"],
            ),
            sections=[
                replace(
                    plan.sections[0],
                    next_action_type=CTAType.EDUCATIONAL_NEXT_STEP,
                )
            ],
            engagement_map=EngagementMap(
                [],
                {},
                [],
                {"educational_next_step": 1},
                reason,
            ),
        )

        self.assertEqual(exception_plan.engagement_map.cta_exception_reason, reason)

    def test_article_plan_rejects_unbound_cta_exception_or_feature_assignment(self):
        plan = article_plan()
        reason = "No relevant product action supports this reader task"

        with self.assertRaisesRegex(ValueError, "Reader Contract"):
            replace(
                plan,
                reader_contract=reader_contract(FunnelStage.MOFU),
                sections=[
                    replace(
                        plan.sections[0],
                        next_action_type=CTAType.EDUCATIONAL_NEXT_STEP,
                    )
                ],
                engagement_map=EngagementMap(
                    [],
                    {},
                    [],
                    {"educational_next_step": 1},
                    reason,
                ),
            )

        with self.assertRaisesRegex(ValueError, "featured-snippet"):
            replace(
                plan,
                sections=[replace(plan.sections[0], featured_snippet_target=True)],
            )

    def test_engagement_distribution_does_not_invent_scenes_or_ctas_without_a_stage(self):
        distribution = ArticlePlanner().plan_engagement_distribution(5)

        self.assertEqual(distribution.mini_story_locations, [])
        self.assertEqual(distribution.cta_locations, {})

    def test_engagement_distribution_applies_intent_sensitive_cta_defaults(self):
        planner = ArticlePlanner()

        tofu = planner.plan_engagement_distribution(5, FunnelStage.TOFU)
        tofu_with_cta = planner.plan_engagement_distribution(
            5,
            FunnelStage.TOFU,
            include_optional_tofu_cta=True,
        )
        mofu = planner.plan_engagement_distribution(5, FunnelStage.MOFU)
        bofu_short = planner.plan_engagement_distribution(2, FunnelStage.BOFU)
        bofu = planner.plan_engagement_distribution(5, FunnelStage.BOFU)
        thought_leadership = planner.plan_engagement_distribution(
            5,
            FunnelStage.THOUGHT_LEADERSHIP,
        )

        self.assertEqual(tofu.cta_locations, {})
        self.assertEqual(set(tofu_with_cta.cta_locations), {"soft_resource_action"})
        self.assertEqual(
            set(mofu.cta_locations),
            {"educational_next_step", "contextual_product"},
        )
        self.assertEqual(
            set(bofu_short.cta_locations),
            {"commercial_contextual", "commercial_conversion"},
        )
        self.assertEqual(
            set(bofu.cta_locations),
            {
                "commercial_contextual",
                "commercial_comparison",
                "commercial_conversion",
            },
        )
        self.assertEqual(len(set(bofu.cta_locations.values())), 3)
        self.assertEqual(
            thought_leadership.next_action_locations,
            {"thought_leadership_next_action": 5},
        )
        self.assertEqual(thought_leadership.cta_locations, {})

    def test_engagement_distribution_supports_documented_cta_exceptions(self):
        planner = ArticlePlanner()

        for stage in (FunnelStage.MOFU, FunnelStage.BOFU):
            with self.subTest(stage=stage):
                distribution = planner.plan_engagement_distribution(
                    5,
                    stage,
                    cta_exception_reason=(
                        "Reader Contract excludes product actions because this brief only "
                        "supports an operational decision"
                    ),
                )
                self.assertEqual(distribution.cta_locations, {})
                self.assertEqual(
                    distribution.next_action_locations,
                    {"educational_next_step": 5},
                )
                self.assertIn("Reader Contract", distribution.cta_exception_reason)

        with self.assertRaisesRegex(ValueError, "cta_exception_reason"):
            planner.plan_engagement_distribution(
                5,
                FunnelStage.MOFU,
                cta_exception_reason=" ",
            )
        for stage in (None, FunnelStage.TOFU, FunnelStage.THOUGHT_LEADERSHIP):
            with self.subTest(stage=stage):
                with self.assertRaisesRegex(ValueError, "mofu or bofu"):
                    planner.plan_engagement_distribution(
                        5,
                        stage,
                        cta_exception_reason="Reader Contract excludes commercial CTAs",
                    )

    def test_thought_leadership_section_renders_next_action_not_cta(self):
        planner = ArticlePlanner()
        distribution = planner.plan_engagement_distribution(
            2,
            FunnelStage.THOUGHT_LEADERSHIP,
        )
        section = planner.create_section_plan(
            section_number=2,
            heading="What this changes",
            gaps_to_address=[],
            insights_to_include=[],
            internal_links=[],
            engagement_map=distribution,
            word_target=275,
        )
        plan = replace(
            article_plan(),
            total_word_target=550,
            sections=[replace(article_plan().sections[0], word_target=275), section],
            engagement_map=distribution,
            reader_contract=reader_contract(FunnelStage.THOUGHT_LEADERSHIP),
        )

        rendered = format_article_plan(plan)
        self.assertIsNone(section.cta_type)
        self.assertEqual(
            section.next_action_type,
            CTAType.THOUGHT_LEADERSHIP_NEXT_ACTION,
        )
        self.assertIn("Next Action Type", rendered)
        self.assertNotIn("CTA Type: thought_leadership_next_action", rendered)

    def test_section_plan_preserves_semantic_cta_role(self):
        planner = ArticlePlanner()
        distribution = planner.plan_engagement_distribution(5, FunnelStage.MOFU)

        section = planner.create_section_plan(
            section_number=5,
            heading="How to choose the next step",
            gaps_to_address=[],
            insights_to_include=[],
            internal_links=[],
            engagement_map=distribution,
            word_target=300,
        )

        self.assertEqual(section.cta_type.value, "contextual_product")

    def test_engagement_distribution_accepts_zero_to_two_explicit_scenes(self):
        planner = ArticlePlanner()

        distribution = planner.plan_engagement_distribution(
            5,
            FunnelStage.MOFU,
            editorial_scene_locations=[2, 4],
        )

        self.assertEqual(distribution.mini_story_locations, [2, 4])

    def test_engagement_distribution_rejects_invalid_stage_scene_or_section_count(self):
        planner = ArticlePlanner()

        with self.assertRaisesRegex(ValueError, "funnel_stage"):
            planner.plan_engagement_distribution(5, "consideration")
        with self.assertRaisesRegex(ValueError, "at most 2"):
            planner.plan_engagement_distribution(
                5,
                FunnelStage.MOFU,
                editorial_scene_locations=[1, 2, 3],
            )
        with self.assertRaisesRegex(ValueError, "distinct"):
            planner.plan_engagement_distribution(
                5,
                FunnelStage.MOFU,
                editorial_scene_locations=[2, 2],
            )
        with self.assertRaisesRegex(ValueError, "between 1 and 5"):
            planner.plan_engagement_distribution(
                5,
                FunnelStage.MOFU,
                editorial_scene_locations=[0],
            )
        with self.assertRaisesRegex(ValueError, "integers"):
            planner.plan_engagement_distribution(
                5,
                FunnelStage.MOFU,
                editorial_scene_locations=["2"],
            )
        with self.assertRaisesRegex(ValueError, "integers"):
            planner.plan_engagement_distribution(
                5,
                FunnelStage.MOFU,
                editorial_scene_locations=[[]],
            )
        with self.assertRaisesRegex(ValueError, "integers"):
            planner.plan_engagement_distribution(
                5,
                FunnelStage.MOFU,
                editorial_scene_locations=[{}],
            )
        with self.assertRaisesRegex(ValueError, "num_sections"):
            planner.plan_engagement_distribution(0, FunnelStage.TOFU)
        with self.assertRaisesRegex(ValueError, "num_sections"):
            planner.plan_engagement_distribution(2.5, FunnelStage.BOFU)
        with self.assertRaisesRegex(ValueError, "num_sections"):
            planner.plan_engagement_distribution(True, FunnelStage.TOFU)
        with self.assertRaisesRegex(ValueError, "editorial_scene_locations"):
            planner.plan_engagement_distribution(
                3,
                FunnelStage.TOFU,
                editorial_scene_locations=2,
            )
        with self.assertRaisesRegex(ValueError, "include_optional_tofu_cta"):
            planner.plan_engagement_distribution(
                3,
                FunnelStage.TOFU,
                include_optional_tofu_cta="yes",
            )
        with self.assertRaisesRegex(ValueError, "only valid for tofu"):
            planner.plan_engagement_distribution(
                3,
                FunnelStage.MOFU,
                include_optional_tofu_cta=True,
            )

    def test_article_plan_preserves_legacy_scene_fields_but_renders_editorial_scene(self):
        plan = article_plan()
        plan.sections[0].mini_story_planned = True
        plan.engagement_map.mini_story_locations = [1]

        serialized = plan.to_dict()
        rendered = format_article_plan(plan)

        self.assertEqual(serialized["engagement_map"]["mini_stories"], [1])
        self.assertTrue(serialized["sections"][0]["mini_story"])
        self.assertIn("Editorial Scene", rendered)
        self.assertNotIn("Proof-Backed POV", rendered)

    def test_article_plan_rejects_invalid_or_unreconciled_total_word_target(self):
        plan = article_plan()

        for invalid in [0, -10, True, 275.5]:
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "total_word_target"):
                    replace(plan, total_word_target=invalid)

        with self.assertRaisesRegex(ValueError, "sum of section word targets"):
            replace(plan, total_word_target=300)

    def test_section_plan_uses_caller_supplied_positive_word_target(self):
        planner = ArticlePlanner()
        distribution = planner.plan_engagement_distribution(3, FunnelStage.MOFU)

        section = planner.create_section_plan(
            section_number=2,
            heading="How dispatch decisions work",
            gaps_to_address=["Explain hard constraints"],
            insights_to_include=[],
            internal_links=[],
            engagement_map=distribution,
            word_target=475,
        )

        self.assertEqual(section.word_target, 475)
        with self.assertRaisesRegex(ValueError, "word_target"):
            planner.create_section_plan(
                section_number=2,
                heading="How dispatch decisions work",
                gaps_to_address=[],
                insights_to_include=[],
                internal_links=[],
                engagement_map=distribution,
                word_target=0,
            )
        with self.assertRaisesRegex(ValueError, "word_target"):
            planner.create_section_plan(
                section_number=2,
                heading="How dispatch decisions work",
                gaps_to_address=[],
                insights_to_include=[],
                internal_links=[],
                engagement_map=distribution,
                word_target=475.5,
            )


class RuntimeEditorialGuidanceTests(unittest.TestCase):
    def test_planner_section_and_cta_enums_flow_into_writer_prompt(self):
        prompt = format_writing_prompt(
            section_type=PlannerSectionType.INTRO,
            heading="Introduction",
            word_target=180,
            strategic_angle="Resolve the reader's immediate decision",
            unique_data=[],
            internal_links=[],
            has_mini_story=False,
            has_cta=CTAType.CONTEXTUAL_PRODUCT,
        )

        self.assertIn("**Type**: intro", prompt)
        self.assertIn("Compelling hook", prompt)
        self.assertIn("CTA Required (contextual product)", prompt)

    def test_social_success_story_leads_preserve_source_urls_and_proof_status(self):
        lead = RedditInsight(
            thread_title="Dispatch workflow discussion",
            thread_url="https://reddit.com/r/fieldservice/example",
            insight_type=InsightType.SUCCESS_STORY,
            content="A dispatcher described resolving repeated schedule conflicts.",
            engagement=EngagementLevel.MEDIUM,
        )
        reddit = RedditResearch(
            threads_analyzed=1,
            insights=[lead],
            pain_points=[],
            success_stories=[lead.content],
            questions=[],
            recommendations=[],
            real_language=[],
        )
        youtube = YouTubeResearch(0, [], [], [], [], [])
        synthesis = SocialResearchAggregator().synthesize_research(reddit, youtube)

        report = format_social_research_report(
            "field service scheduling", reddit, youtube, synthesis
        )

        success_block = report.split("### Success Stories Found", 1)[1].split(
            "### Real User Language", 1
        )[0]
        self.assertIn(lead.content, success_block)
        self.assertIn(lead.thread_url, success_block)
        self.assertIn("research lead only", success_block)
        self.assertIn("customer-proof approval", success_block)

    def test_social_success_leads_do_not_become_editorial_scenes(self):
        lead = RedditInsight(
            thread_title="Scheduling result",
            thread_url="https://reddit.com/r/fieldservice/example",
            insight_type=InsightType.SUCCESS_STORY,
            content="A team changed its dispatch review and reduced rework",
            engagement=EngagementLevel.HIGH,
            quotable="This changed our week",
        )
        reddit = RedditResearch(
            threads_analyzed=1,
            insights=[lead],
            pain_points=[],
            success_stories=[lead.content],
            questions=[],
            recommendations=[],
            real_language=[],
        )
        youtube = YouTubeResearch(0, [], [], [], [], [])
        synthesis = SocialResearchAggregator().synthesize_research(reddit, youtube)

        report = format_social_research_report(
            "field service scheduling", reddit, youtube, synthesis
        )
        scene_block = report.split("### Editorial Scene Opportunities", 1)[1]

        self.assertEqual(synthesis.story_seeds, [])
        self.assertNotIn(lead.content, scene_block)
        self.assertNotIn(lead.thread_url, scene_block)
        self.assertIn("Do not anonymize an unapproved success claim", scene_block)
        self.assertIn("Quote research lead", report)
        self.assertNotIn("**Quotable**", report)

    def test_social_video_review_query_uses_current_year(self):
        queries = SocialResearchAggregator().build_search_queries("scheduling")

        self.assertTrue(
            any(str(datetime.now().year) in query for query in queries["youtube"])
        )

    def test_unlinked_legacy_success_story_is_not_treated_as_public_proof(self):
        reddit = RedditResearch(
            threads_analyzed=0,
            insights=[],
            pain_points=[],
            success_stories=["Legacy success note"],
            questions=[],
            recommendations=[],
            real_language=[],
        )
        youtube = YouTubeResearch(0, [], [], [], [], [])
        synthesis = SocialResearchAggregator().synthesize_research(reddit, youtube)

        report = format_social_research_report(
            "field service scheduling", reddit, youtube, synthesis
        )

        self.assertIn("Source URL unresolved", report)
        self.assertIn("not eligible for public use", report)

    def test_engagement_analyzer_reports_unplanned_ctas_without_penalizing_absence(self):
        result = EngagementAnalyzer().analyze(
            "Dispatchers need a clear way to resolve scheduling conflicts.\n\n"
            "A practical workflow separates fixed constraints from judgment calls."
        )

        self.assertEqual(result["ctas"]["evaluation_status"], "reported")
        self.assertEqual(result["ctas"]["count"], 0)
        self.assertIsNone(result["scores"]["ctas"])
        self.assertEqual(result["total_criteria"], 3)
        self.assertTrue(result["all_passed"])

        report = format_results([result])
        self.assertIn("N/A", report)
        self.assertNotIn("4/4", report)
        self.assertNotIn("2025-12-10", report)

        parsed = parse_engagement_cli_args(["--glob", "rewrites/*.md"])
        self.assertEqual(parsed.pattern, "rewrites/*.md")

    def test_engagement_cli_loads_serialized_article_plan_ctas(self):
        plan = load_cta_plan(
            '{"engagement_map":{"ctas":{"educational_next_step":4}}}'
        )

        self.assertEqual(plan, {"educational_next_step": 4})

    def test_engagement_analyzer_counts_overlapping_markdown_cta_once(self):
        result = EngagementAnalyzer().analyze(
            "A practical workflow starts with fixed constraints.\n\n"
            "**[Learn more]**",
            cta_plan={"educational_next_step": 1},
        )

        self.assertEqual(result["ctas"]["count"], 1)
        self.assertTrue(result["ctas"]["meets_plan"])

    def test_engagement_analyzer_enforces_explicit_zero_cta_plan(self):
        result = EngagementAnalyzer().analyze(
            "Dispatchers need a clear way to resolve scheduling conflicts.\n\n"
            "Learn more about the workflow.",
            cta_plan={},
        )

        self.assertEqual(result["ctas"]["evaluation_status"], "evaluated")
        self.assertEqual(result["ctas"]["required_count"], 0)
        self.assertFalse(result["scores"]["ctas"])

    def test_engagement_analyzer_validates_public_text_inputs(self):
        analyzer = EngagementAnalyzer()

        with self.assertRaisesRegex(ValueError, "content"):
            analyzer.analyze(None)
        with self.assertRaisesRegex(ValueError, "filename"):
            analyzer.analyze("Scheduling content", filename=42)

    def test_engagement_analyzer_checks_planned_section_locations(self):
        result = EngagementAnalyzer().analyze(
            "Dispatchers need a clear way to resolve scheduling conflicts.\n\n"
            "## Define constraints\n\nSeparate hard constraints.\n\n"
            "## Prioritize work\n\nOrder the queue.\n\n"
            "## Review exceptions\n\nLearn more about the workflow.\n\n"
            "## Choose the next step\n\nReady to see the scheduling process.",
            cta_plan={
                "educational_next_step": 4,
                "contextual_product": 5,
            },
        )

        self.assertEqual(result["ctas"]["evaluation_status"], "evaluated")
        self.assertEqual(result["ctas"]["required_count"], 2)
        self.assertEqual(result["ctas"]["observed_section_locations"], [4, 5])
        self.assertTrue(result["ctas"]["locations_match_plan"])
        self.assertTrue(result["ctas"]["meets_plan"])
        self.assertTrue(result["scores"]["ctas"])

    def test_engagement_analyzer_rejects_generic_ctas_for_commercial_roles(self):
        result = EngagementAnalyzer().analyze(
            "## Compare options\n\nLearn more about the options.\n\n"
            "## Choose a platform\n\nLearn more about the platform.",
            cta_plan={
                "commercial_contextual": 2,
                "commercial_conversion": 3,
            },
        )

        self.assertTrue(result["ctas"]["locations_match_plan"])
        self.assertFalse(result["ctas"]["roles_match_plan"])
        self.assertFalse(result["ctas"]["meets_plan"])
        self.assertEqual(len(result["ctas"]["role_mismatches"]), 2)

    def test_engagement_analyzer_rejects_right_count_in_wrong_sections(self):
        result = EngagementAnalyzer().analyze(
            "Dispatchers need a clear way to resolve scheduling conflicts.\n\n"
            "## Define constraints\n\nLearn more about the workflow.\n\n"
            "## Prioritize work\n\nReady to see the scheduling process.\n\n"
            "## Review exceptions\n\nReview the queue.\n\n"
            "## Choose the next step\n\nSelect the action.",
            cta_plan={
                "educational_next_step": 4,
                "contextual_product": 5,
            },
        )

        self.assertEqual(result["ctas"]["count"], 2)
        self.assertFalse(result["ctas"]["locations_match_plan"])
        self.assertFalse(result["ctas"]["meets_plan"])
        self.assertFalse(result["scores"]["ctas"])

    def test_competitor_blueprint_only_marks_qualified_recurring_gaps_as_must_fill(self):
        qualified = ContentGap(
            gap_type=GapType.MISSING_PERSPECTIVE,
            description="Dispatch constraint decision guidance is missing",
            location="Dispatch workflow",
            competitor_url="https://example.com/one",
            priority=GapPriority.HIGH,
            opportunity="Explain the decision with approved operational evidence",
            reader_critical=True,
            evidence_available=True,
        )
        unqualified = ContentGap(
            gap_type=GapType.STRUCTURAL_GAP,
            description="No FAQ section",
            location="Article structure",
            competitor_url="https://example.com/one",
            priority=GapPriority.HIGH,
            opportunity="Evaluate whether verified questions help the reader",
        )
        analyses = []
        for index in range(3):
            analyses.append(
                CompetitorAnalysis(
                    url=f"https://example.com/{index}",
                    title=f"Competitor {index}",
                    word_count=900,
                    structure=["Dispatch workflow"],
                    strengths=[],
                    gaps=[qualified, unqualified],
                    outdated_items=[],
                )
            )

        blueprint = CompetitorGapAnalyzer().create_blueprint(analyses)
        report = format_gap_report("field service scheduling", analyses, blueprint)

        self.assertEqual(blueprint.must_fill_gaps, [qualified])
        self.assertIn("### MUST-FILL GAPS", report)
        self.assertIn("recurring, reader-critical, and evidence-supported", report)
        self.assertNotIn("High-Frequency Gaps To Evaluate", report)

    def test_content_gap_rejects_non_boolean_qualification_values(self):
        base = {
            "gap_type": GapType.MISSING_PERSPECTIVE,
            "description": "Dispatch decision guidance is missing",
            "location": "Dispatch workflow",
            "competitor_url": "https://example.com/one",
            "priority": GapPriority.HIGH,
            "opportunity": "Explain the decision with approved evidence",
        }

        for field_name in ("reader_critical", "evidence_available"):
            for invalid in ("false", 0, 1, None):
                with self.subTest(field_name=field_name, invalid=invalid):
                    with self.assertRaisesRegex(ValueError, field_name):
                        ContentGap(**base, **{field_name: invalid})

    def test_competitor_recurrence_requires_distinct_urls_and_accepts_explicit_qualification(self):
        gap = ContentGap(
            gap_type=GapType.MISSING_PERSPECTIVE,
            description="Dispatch constraint decision guidance is missing",
            location="Dispatch workflow",
            competitor_url="https://example.com/one",
            priority=GapPriority.HIGH,
            opportunity="Explain the decision with approved operational evidence",
        )
        duplicate_analysis = CompetitorAnalysis(
            url="https://example.com/one",
            title="Competitor one",
            word_count=900,
            structure=[],
            strengths=[],
            gaps=[gap, gap, gap],
            outdated_items=[],
        )
        analyzer = CompetitorGapAnalyzer()

        duplicate_blueprint = analyzer.create_blueprint(
            [duplicate_analysis],
            reader_critical_gaps=[gap.description],
            evidence_supported_gaps=[gap.description],
        )
        self.assertEqual(duplicate_blueprint.must_fill_gaps, [])

        distinct_analyses = [
            replace(
                duplicate_analysis,
                url=f"https://example.com/{index}",
                gaps=[replace(gap, competitor_url=f"https://example.com/{index}")],
            )
            for index in range(3)
        ]
        qualified_blueprint = analyzer.create_blueprint(
            distinct_analyses,
            reader_critical_gaps=[gap.description],
            evidence_supported_gaps=[gap.description],
        )

        self.assertEqual(len(qualified_blueprint.must_fill_gaps), 1)
        self.assertTrue(qualified_blueprint.must_fill_gaps[0].reader_critical)
        self.assertTrue(qualified_blueprint.must_fill_gaps[0].evidence_available)

    def test_competitor_structure_recurrence_requires_distinct_urls(self):
        analyzer = CompetitorGapAnalyzer()
        duplicate = CompetitorAnalysis(
            url="https://example.com/one",
            title="Competitor one",
            word_count=900,
            structure=["Dispatch workflow", "Dispatch workflow", "Dispatch workflow"],
            strengths=[],
            gaps=[],
            outdated_items=[],
        )

        self.assertEqual(analyzer.create_blueprint([duplicate]).structure_to_match, [])

        distinct = [
            replace(duplicate, url=f"https://example.com/{index}", structure=["Dispatch workflow"])
            for index in range(3)
        ]
        self.assertEqual(
            analyzer.create_blueprint(distinct).structure_to_match,
            ["Dispatch workflow"],
        )

    def test_competitor_structure_preserves_observed_heading_capitalization(self):
        analyzer = CompetitorGapAnalyzer()
        analyses = [
            CompetitorAnalysis(
                url=f"https://example.com/{index}",
                title=f"Competitor {index}",
                word_count=900,
                structure=["HVAC FAQs"],
                strengths=[],
                gaps=[],
                outdated_items=[],
            )
            for index in range(3)
        ]

        blueprint = analyzer.create_blueprint(analyses)
        report = format_gap_report("hvac software", analyses, blueprint)

        self.assertEqual(blueprint.structure_to_match, ["HVAC FAQs"])
        self.assertIn("- HVAC FAQs", report)

    def test_competitor_analysis_does_not_invent_generic_structural_gaps(self):
        analysis = CompetitorGapAnalyzer().analyze_content(
            "# Scheduling guide\n\n## Dispatch workflow\n\nAssign work by skill and urgency.",
            "https://example.com/scheduling",
        )

        self.assertFalse(
            any(gap.gap_type == GapType.STRUCTURAL_GAP for gap in analysis.gaps)
        )
        self.assertFalse(
            any("FAQ" in gap.description or "conclusion" in gap.description for gap in analysis.gaps)
        )

    def test_old_years_are_freshness_review_candidates_not_outdated_claims(self):
        analyzer = CompetitorGapAnalyzer()
        candidates = analyzer._find_outdated_info(
            "The workflow was introduced in 2021 and reviewed in 2024."
        )

        self.assertTrue(candidates)
        self.assertTrue(all("evaluate whether current evidence is needed" in item for item in candidates))
        self.assertTrue(all("likely outdated" not in item for item in candidates))
        self.assertEqual(
            analyzer._identify_strengths(
                [
                    {
                        "header": "History",
                        "content": "The workflow was introduced in 2021.",
                    }
                ]
            ),
            [],
        )

    def test_competitor_blueprint_requires_explicit_gap_qualification_when_ambiguous(self):
        gap = ContentGap(
            gap_type=GapType.MISSING_PERSPECTIVE,
            description="Dispatch decision guidance is missing",
            location="Dispatch workflow",
            competitor_url="https://example.com/one",
            priority=GapPriority.HIGH,
            opportunity="Evaluate the missing decision",
        )
        analyses = [
            CompetitorAnalysis(
                url=f"https://example.com/{index}",
                title=f"Competitor {index}",
                word_count=900,
                structure=[],
                strengths=[],
                gaps=[replace(gap, competitor_url=f"https://example.com/{index}")],
                outdated_items=[],
            )
            for index in range(3)
        ]

        unresolved = CompetitorGapAnalyzer().create_blueprint(analyses)
        self.assertEqual(
            [gap.description for gap in unresolved.qualification_required_gaps],
            [gap.description],
        )

        blueprint = CompetitorGapAnalyzer().create_blueprint(
            analyses,
            reader_critical_gaps=[],
            evidence_supported_gaps=[],
        )
        self.assertEqual(blueprint.must_fill_gaps, [])
        self.assertEqual(blueprint.qualification_required_gaps, [])

        with self.assertRaisesRegex(ValueError, "unknown gap"):
            CompetitorGapAnalyzer().create_blueprint(
                analyses,
                reader_critical_gaps=["Typo in gap description"],
                evidence_supported_gaps=[],
            )

    def test_competitor_artifacts_validate_inputs_and_render_deterministically(self):
        with self.assertRaisesRegex(ValueError, "word_count"):
            CompetitorAnalysis(
                url="https://example.com/one",
                title="One",
                word_count=True,
                structure=[],
                strengths=[],
                gaps=[],
                outdated_items=[],
            )
        with self.assertRaisesRegex(ValueError, "analyses"):
            CompetitorGapAnalyzer().create_blueprint(["not an analysis"])

        analyses = [
            CompetitorAnalysis(
                url="https://example.com/one",
                title="One",
                word_count=900,
                structure=[],
                strengths=[],
                gaps=[],
                outdated_items=["Reference to 2022", "Reference to 2020"],
            )
        ]
        blueprint = CompetitorGapAnalyzer().create_blueprint(analyses)

        self.assertEqual(
            blueprint.outdated_to_update,
            ["Reference to 2020", "Reference to 2022"],
        )

    def test_gap_report_does_not_truncate_recurring_structure_or_date_context(self):
        headings = [f"Recurring section {index}" for index in range(1, 9)]
        date_references = [f"Reference to {year}" for year in range(2014, 2024)]
        analyses = [
            CompetitorAnalysis(
                url=f"https://example.com/{index}",
                title=f"Competitor {index}",
                word_count=900,
                structure=headings,
                strengths=[],
                gaps=[],
                outdated_items=date_references,
            )
            for index in range(3)
        ]

        blueprint = CompetitorGapAnalyzer().create_blueprint(analyses)
        report = format_gap_report("field service scheduling", analyses, blueprint)

        for heading in headings:
            self.assertIn(heading.lower(), report.lower())
        for reference in date_references:
            self.assertIn(reference, report)

    def test_gap_report_preserves_recurring_candidates_that_need_qualification(self):
        gap = ContentGap(
            gap_type=GapType.MISSING_PERSPECTIVE,
            description="Dispatch decision guidance is missing",
            location="Dispatch workflow",
            competitor_url="https://example.com/one",
            priority=GapPriority.HIGH,
            opportunity="Evaluate the missing decision",
        )
        analyses = [
            CompetitorAnalysis(
                url=f"https://example.com/{index}",
                title=f"Competitor {index}",
                word_count=900,
                structure=[],
                strengths=[],
                gaps=[replace(gap, competitor_url=f"https://example.com/{index}")],
                outdated_items=[],
            )
            for index in range(3)
        ]
        blueprint = CompetitorGapAnalyzer().create_blueprint(analyses)

        report = format_gap_report("field service scheduling", analyses, blueprint)

        self.assertIn("### QUALIFICATION REQUIRED", report)
        self.assertIn("Dispatch decision guidance is missing", report)
        self.assertIn("reader importance and evidence", report)
        must_fill_block = report.split("### MUST-FILL GAPS", 1)[1].split(
            "### QUALIFICATION REQUIRED", 1
        )[0]
        self.assertNotIn("**Dispatch decision guidance is missing**", must_fill_block)

    def test_legacy_mini_story_flag_generates_optional_editorial_scene_guidance(self):
        prompt = format_writing_prompt(
            section_type=WriterSectionType.BODY_EXPLANATION,
            heading="Scheduling pressure",
            word_target=250,
            strategic_angle="Show the operational decision",
            unique_data=[],
            internal_links=[],
            has_mini_story=True,
            has_cta="",
        )

        self.assertIn("Optional Editorial Scene", prompt)
        self.assertIn("Unnamed workflow", prompt)
        self.assertIn("Named people or businesses require approved proof", prompt)
        self.assertNotIn("Optional Proof-Backed POV", prompt)

    def test_section_writer_uses_planned_targets_not_static_section_ranges(self):
        writer = SectionWriter()

        for section_type in WriterSectionType:
            guidelines = writer.get_writing_guidelines(section_type)
            requirements = guidelines.requirements
            if section_type == WriterSectionType.FAQ:
                requirements = [
                    requirement
                    for requirement in requirements
                    if "40-60 word answers" not in requirement
                ]

            self.assertFalse(
                any(re.search(r"\b\d+[-\u2013]\d+ words\b", item) for item in requirements),
                f"{section_type.value} still has a static word range: {requirements}",
            )

    def test_section_writer_specificity_guidance_requires_proof_safe_detail(self):
        writer = SectionWriter()
        vague_replacements = "\n".join(writer.VAGUE_WORDS.values())
        comparison_guidance = writer.get_writing_guidelines(
            WriterSectionType.BODY_COMPARISON
        )
        combined = "\n".join(
            comparison_guidance.requirements
            + comparison_guidance.dos
            + comparison_guidance.donts
            + comparison_guidance.quality_checks
        )

        self.assertIn("approved proof", vague_replacements)
        self.assertIn("concrete workflow detail", vague_replacements)
        self.assertNotRegex(
            vague_replacements,
            r"specific (?:number|count|percentage|frequency)|exact count|percentage of time",
        )
        self.assertIn("Approved proof supports any numeric comparison", combined)
        self.assertNotIn("Specific numbers are included", combined)

    def test_section_writer_only_adds_cta_when_the_plan_supplies_one(self):
        common = {
            "section_type": WriterSectionType.CONCLUSION,
            "heading": "Next steps",
            "word_target": 180,
            "strategic_angle": "Close the reader contract",
            "unique_data": [],
            "internal_links": [],
            "has_mini_story": False,
        }

        without_cta = format_writing_prompt(has_cta="", **common)
        with_cta = format_writing_prompt(has_cta="contextual product", **common)

        self.assertNotIn("CTA Required", without_cta)
        self.assertIn("CTA Required (contextual product)", with_cta)

    def test_section_writer_renders_thought_leadership_next_action_without_commercial_cta_language(self):
        prompt = format_writing_prompt(
            section_type=WriterSectionType.CONCLUSION,
            heading="What this means next",
            word_target=180,
            strategic_angle="Close with reflection and evidence",
            unique_data=[],
            internal_links=[],
            has_mini_story=False,
            has_cta="thought_leadership_next_action",
        )

        self.assertIn("Next Action Required (thought leadership next action)", prompt)
        self.assertIn("reflection, discussion, evidence resource, or other useful next action", prompt)
        self.assertNotIn("call-to-action", prompt)

    def test_conclusion_guidance_requires_an_intent_appropriate_next_action(self):
        writer = SectionWriter()
        guidelines = writer.get_writing_guidelines(WriterSectionType.CONCLUSION)
        checklist = writer.get_editing_checklist(WriterSectionType.CONCLUSION)
        combined = "\n".join(
            guidelines.requirements
            + guidelines.dos
            + guidelines.donts
            + guidelines.quality_checks
            + checklist.section_specific_checks
        )

        self.assertIn("intent-appropriate next action", combined)
        self.assertNotIn("Strong CTA", combined)
        self.assertNotIn("3-5 actionable takeaways", combined)
        self.assertNotIn("This week", combined)
        self.assertNotIn("This month", combined)
        self.assertNotIn("Reader knows exactly what to do next", combined)
        self.assertNotIn("specific data/examples", "\n".join(checklist.universal_checks))
        self.assertIn("approved proof-backed detail", "\n".join(checklist.universal_checks))

    def test_competitor_gap_analyzer_does_not_invent_a_conclusion_gap(self):
        analysis = CompetitorGapAnalyzer().analyze_content(
            "# Guide\n\n## Main section\n\nBody copy without a conclusion.",
            "https://example.com/article",
        )

        self.assertFalse(
            any("conclusion" in gap.description.lower() for gap in analysis.gaps)
        )

    def test_competitor_gap_analyzer_does_not_treat_word_count_as_section_quality(self):
        analyzer = CompetitorGapAnalyzer()
        short_section = {
            "level": 2,
            "header": "Scheduling rules",
            "content": "Short but useful.",
        }
        long_section = {
            "level": 2,
            "header": "Scheduling details",
            "content": "specific " * 401,
        }

        self.assertEqual(analyzer._find_thin_sections(short_section, "https://example.com"), [])
        self.assertNotIn(
            "Comprehensive coverage",
            "\n".join(analyzer._identify_strengths([long_section])),
        )


if __name__ == "__main__":
    unittest.main()
