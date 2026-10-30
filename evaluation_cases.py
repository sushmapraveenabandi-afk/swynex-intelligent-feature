"""
=============================================================================
VisualMind AI - Evaluation Test Cases (Benchmark Suite)
=============================================================================
This module contains 8 carefully curated and labeled test texts used to
benchmark the categorization accuracy and robustness of VisualMind AI.

The suite includes:
  - Standard Article (informational prose)
  - Standard Process (step-by-step workflow)
  - Standard Comparison (side-by-side technology evaluation)
  - Tricky Mixed Cases (narrative + process, essay + comparison)
  - Narrative disguised workflow
  - Very short and ambiguous texts to test edge-case handling

Each test case provides:
  - id: Unique integer identifier (1 to 8)
  - name: Descriptive title for the benchmark case
  - text: The exact input text passed to the model
  - category_expected: Ground truth category ("article" | "process" | "comparison")
  - difficulty: "Standard" or specific tricky edge-case label
  - description: Summary of content and structure
  - why_tricky: Explanation of why this case tests model classification boundaries
=============================================================================
"""

DEFAULT_MODEL = "gemini-3.8-flash"

EVALUATION_CASES = [
    {
        "id": 1,
        "name": "Global Climate & Renewable Energy Transition",
        "category_expected": "article",
        "difficulty": "Standard Article",
        "description": "Informational expository prose explaining trends, cost declines, and grid challenges in renewable energy.",
        "why_tricky": "Baseline test. Contains facts and statistics without sequential time steps or side-by-side product comparisons.",
        "text": (
            "The worldwide expansion of renewable energy reached historic milestones over the past year. "
            "Driven by substantial cost reductions in photovoltaic cells and next-generation wind turbines, "
            "clean power generation has become more economical than fossil fuels across most emerging markets. "
            "Grid operators are increasingly deploying large-scale utility batteries to manage fluctuating "
            "solar output during peak evening hours. Although supply chain bottlenecks and permitting delays "
            "continue to slow progress in certain regions, international investments in decentralized power "
            "networks suggest that sustainable energy capacity will double before the decade concludes."
        )
    },
    {
        "id": 2,
        "name": "Automated Software CI/CD Pipeline",
        "category_expected": "process",
        "difficulty": "Standard Process",
        "description": "A clear chronological technical workflow describing code review to canary deployment.",
        "why_tricky": "Baseline test. Uses explicit sequence markers ('First', 'Next', 'Afterward', 'Then', 'Finally').",
        "text": (
            "When a software engineer finishes a feature branch and opens a Pull Request, an automated CI/CD pipeline triggers. "
            "First, the source code repository runs automated linter checks and unit tests to ensure code quality. "
            "Next, if all tests pass, the pipeline builds a self-contained container image using Docker. "
            "Afterward, the container image is pushed to the secure artifact registry. "
            "Then, the staging environment automatically pulls the new image and executes end-to-end integration tests. "
            "Finally, upon senior engineer approval, the deployment manager initiates a zero-downtime canary rollout to the production cluster."
        )
    },
    {
        "id": 3,
        "name": "Monolithic vs Microservices Architecture",
        "category_expected": "comparison",
        "difficulty": "Standard Comparison",
        "description": "Direct side-by-side contrast of software architectural patterns across criteria.",
        "why_tricky": "Baseline test. Explicitly compares two paradigms on scalability, debugging, and operational complexity.",
        "text": (
            "Selecting between a monolithic and a microservices software architecture fundamentally shapes an engineering team's "
            "velocity and scalability. A monolithic architecture packages all business logic, database connections, and background workers "
            "into a single executable codebase. This makes local debugging straightforward, simplifies transactional boundaries, and reduces "
            "initial deployment complexity, though large codebases can lead to slow deployments and high regression risks. "
            "Conversely, a microservices architecture splits capabilities into independently deployable, specialized services communicating "
            "over gRPC or HTTP APIs. While this allows autonomous team scaling and isolated technology choices, it introduces distributed "
            "systems overhead, complex network latency, and challenging data consistency requirements across services."
        )
    },
    {
        "id": 4,
        "name": "Specialty Espresso: Cultural History & Brewing Routine",
        "category_expected": "process",
        "difficulty": "Tricky: Mixed Article + Process",
        "description": "Opens with cultural history of Italian espresso, but transitions into a precise 4-step extraction procedure.",
        "why_tricky": "Blended intent. Tests whether the model prioritizes the actionable extraction procedure over the introductory historical narrative.",
        "text": (
            "Espresso culture originated in early 20th-century Italy, where industrial baristas revolutionized social gathering places "
            "by forcing pressurized water through finely ground coffee. Beyond this rich cultural heritage, pulling a modern specialty "
            "espresso requires strict technical precision. First, weigh exactly 18 grams of freshly roasted specialty coffee beans into a "
            "precision grinder. Next, distribute the ground coffee evenly across the portafilter basket using a WDT needle tool to eliminate "
            "micro-channels. Then, tamp the coffee bed evenly with roughly 25 pounds of pressure to ensure a flat, compressed surface. "
            "Finally, lock the portafilter into the espresso group head, activate the pump at 9 bars of pressure, and extract 36 grams of "
            "liquid espresso within an optimal window of 28 to 32 seconds."
        )
    },
    {
        "id": 5,
        "name": "Remote Work vs Return-to-Office Cultural Divide",
        "category_expected": "comparison",
        "difficulty": "Tricky: Mixed Article + Comparison",
        "description": "An essay-style analysis weighing the pros and cons of remote work versus in-office work.",
        "why_tricky": "No bullet points or explicit table. The comparison is embedded inside continuous journalistic essay prose.",
        "text": (
            "The debate over where knowledge workers should spend their working hours has transformed corporate culture worldwide. "
            "On one side, remote-first work offers employees flexible scheduling, zero commuting stress, and access to nationwide talent "
            "pools, while simultaneously lowering corporate commercial real estate expenditures. However, remote teams frequently report "
            "higher digital fatigue and weakened spontaneous collaboration. On the other side, in-office work fosters organic mentorship, "
            "deeper interpersonal trust, and rapid serendipitous problem-solving in shared physical spaces, but it imposes long daily "
            "commutes and rigid geographic constraints on hiring. As companies navigate post-pandemic policy, executive leadership must "
            "weigh worker autonomy against the benefits of physical proximity."
        )
    },
    {
        "id": 6,
        "name": "Sysadmin Incident Triage Protocol",
        "category_expected": "process",
        "difficulty": "Tricky: Narrative Story Protocol",
        "description": "An emergency troubleshooting sequence framed as a first-person on-call story without formal numbering.",
        "why_tricky": "Narrative framing ('Whenever our monitoring alerts page at 3 AM...') that tests whether the model extracts the underlying workflow.",
        "text": (
            "Whenever our production monitoring alerts page at 3 AM, our on-call protocol kicks in immediately. "
            "The first action is acknowledging the PagerDuty incident within five minutes to prevent escalation. "
            "Once acknowledged, the on-call engineer opens the live Datadog dashboard and checks CPU and memory saturation metrics. "
            "If saturation exceeds 90%, the engineer immediately drains inbound traffic from the impacted Kubernetes node cluster. "
            "Next, they inspect application logs to isolate recent error traces and determine if a bad deployment occurred. "
            "If so, they immediately execute the rollback script to restore the previous stable release. "
            "Finally, the engineer posts an update in the public status channel and schedules an internal post-mortem retrospective."
        )
    },
    {
        "id": 7,
        "name": "Terse Comparison: iOS vs Android",
        "category_expected": "comparison",
        "difficulty": "Tricky: Very Short Comparison",
        "description": "An extremely short comparative summary of two smartphone operating systems.",
        "why_tricky": "Very short (32 words). Lacks detailed criteria or structured headers; tests if brevity still yields correct classification.",
        "text": (
            "iOS is a closed, tightly controlled ecosystem offering seamless hardware integration and high privacy defaults. "
            "In contrast, Android is open-source, highly customizable, and available across diverse manufacturers and budget tiers."
        )
    },
    {
        "id": 8,
        "name": "Brief Insight: Daily Mindfulness Benefits",
        "category_expected": "article",
        "difficulty": "Tricky: Short Ambiguous / Borderline",
        "description": "A 37-word health summary mentioning an action that could be confused with a process step.",
        "why_tricky": "Brief text mentioning 'Sitting quietly... allows the brain to...' which sounds like a step, but the overarching intent is health science overview.",
        "text": (
            "Daily mindfulness meditation significantly reduces cortisol levels, improves cognitive focus, and supports cardiovascular health. "
            "Sitting quietly for ten minutes each morning allows the brain to regulate emotional reactions and build resilience against chronic workplace stress."
        )
    }
]


def get_all_cases() -> list:
    """Returns the list of all 8 benchmark evaluation cases."""
    return EVALUATION_CASES


def get_case_by_id(case_id: int) -> dict:
    """Finds and returns a specific evaluation case by its integer ID."""
    for case in EVALUATION_CASES:
        if case["id"] == case_id:
            return case
    return {}


if __name__ == "__main__":
    print(f"VisualMind AI Benchmark Suite loaded with {len(EVALUATION_CASES)} labeled test cases.")
    print(f"Default Model: {DEFAULT_MODEL}\n")
    for c in EVALUATION_CASES:
        print(f"[{c['id']}] {c['name']}")
        print(f"    Expected: {c['category_expected'].upper()} | Difficulty: {c['difficulty']}")
        print(f"    Preview: {c['text'][:80]}...\n")
