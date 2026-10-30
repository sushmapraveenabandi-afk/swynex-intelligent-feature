"""
=============================================================================
VisualMind AI
=============================================================================
An intelligent, beginner-friendly Streamlit web application powered by the 
Google Gemini API (google-genai SDK). It analyzes pasted text, automatically 
detects whether it represents an article, a process, or a comparison, and 
dynamically renders:
  - Article    -> Executive Summary & Key Points
  - Process    -> Interactive Mermaid Flowchart & Step-by-Step Breakdown
  - Comparison -> Markdown Comparison Table & Trade-off Insights

Key Features:
  1. Robust Error Handling: Automatic 503 retries with exponential backoff,
     and friendly actionable explanations for 429 (quota), 404 (model),
     invalid API key, and empty/very short text.
  2. Evaluation Benchmark Suite: An Evaluation tab running 8 labeled test
     cases (standard & tricky edge cases) using exactly 8 API calls to compute
     an overall accuracy score and predicted-vs-expected comparison.
=============================================================================
"""

import os
import json
import time
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Import the 8 labeled benchmark test cases and default model
from evaluation_cases import EVALUATION_CASES, DEFAULT_MODEL

# -----------------------------------------------------------------------------
# 1. Page Configuration & Environment Setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="VisualMind AI - Text Categorizer & Visualizer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables from .env file
load_dotenv()
env_api_key = os.getenv("GEMINI_API_KEY", "").strip()

# -----------------------------------------------------------------------------
# 2. Sample Datasets for 1-Click Testing
# -----------------------------------------------------------------------------
SAMPLES = {
    "article": {
        "label": "📰 Sample Article: Renewable Energy",
        "title": "The Global Transition to Renewable Energy",
        "text": (
            "Over the past decade, the global transition toward renewable energy has accelerated at an "
            "unprecedented pace. Driven by falling technology costs, supportive government policies, and "
            "urgent climate commitments, solar photovoltaics and onshore wind have become the cheapest "
            "sources of new electricity generation in most parts of the world. \n\n"
            "Modern power grids face the challenge of managing intermittent supply from renewables. "
            "To address this, utility-scale lithium-ion battery storage systems and long-duration storage "
            "technologies, such as pumped hydro and green hydrogen, are experiencing record investment. "
            "Furthermore, smart grids powered by artificial intelligence now forecast energy demand and "
            "reroute distribution in real-time, significantly reducing transmission losses.\n\n"
            "Despite this momentum, obstacles persist. Developing nations require significant capital "
            "investment to build modern transmission infrastructure, and regulatory hurdles frequently delay "
            "grid interconnection approvals. Nevertheless, experts agree that modernizing grid resilience and "
            "expanding decentralized solar installations will be decisive factors in achieving net-zero emissions by 2050."
        )
    },
    "process": {
        "label": "🔄 Sample Process: Web Browser Rendering",
        "title": "How a Web Browser Renders a Webpage",
        "text": (
            "When a user types a URL into a web browser and hits Enter, a multi-step sequence occurs to render "
            "the webpage. \n\n"
            "First, the browser performs a DNS Lookup to resolve the human-readable domain name into an IP address. "
            "Next, the browser establishes a TCP Connection with the destination server via a 3-way handshake, "
            "followed by a TLS handshake if the site uses HTTPS. Once the secure connection is ready, the browser "
            "sends an HTTP GET request to the server. \n\n"
            "The server processes the request and returns an HTTP response containing the HTML document. Upon receipt, "
            "the browser's rendering engine begins parsing the HTML bytes to construct the Document Object Model (DOM) tree. "
            "Concurrently, any linked CSS files are downloaded and parsed into the CSS Object Model (CSSOM) tree. \n\n"
            "The browser combines the DOM and CSSOM into a Render Tree, which calculates the visual layout and exact "
            "geometry of every visible element. Finally, in the Painting phase, pixels are rasterized onto the screen, "
            "displaying the fully loaded interactive webpage to the user."
        )
    },
    "comparison": {
        "label": "⚖️ Sample Comparison: SQL vs NoSQL",
        "title": "SQL vs NoSQL Databases: Architecture and Trade-offs",
        "text": (
            "Choosing the right database architecture is a pivotal decision in modern software engineering. "
            "Relational Databases (SQL) and Non-Relational Databases (NoSQL) offer fundamentally different approaches "
            "to data storage, consistency, and scalability.\n\n"
            "SQL databases (such as PostgreSQL, MySQL, and Oracle) store data in structured tables with predefined "
            "schemas, rows, and columns. They strictly adhere to ACID properties (Atomicity, Consistency, Isolation, "
            "Durability), guaranteeing transactional integrity. SQL databases scale vertically by upgrading hardware "
            "resources (CPU, RAM, SSD), which can become costly. They excel in applications requiring complex multi-table "
            "queries, financial transactions, and rigid data validation.\n\n"
            "In contrast, NoSQL databases (such as MongoDB, Cassandra, DynamoDB, and Redis) store unstructured or "
            "semi-structured data as documents, key-value pairs, wide-column stores, or graph nodes. They prioritize "
            "horizontal scaling by distributing data across clusters of commodity servers. Instead of strict ACID, "
            "many NoSQL systems adopt the BASE model (Basically Available, Soft-state, Eventual consistency) to maximize "
            "throughput and availability. NoSQL is ideal for real-time big data analytics, social networks, dynamic catalogs, "
            "and rapid prototyping where schemas evolve constantly."
        )
    }
}

# -----------------------------------------------------------------------------
# 3. Custom Application Exception & Error Formatter
# -----------------------------------------------------------------------------
class GeminiAppError(Exception):
    """Custom exception raised when an API error occurs, carrying a friendly message."""
    pass


def format_gemini_error(error: Exception, model_name: str = "") -> str:
    """
    Translates technical exceptions into human-friendly, actionable error messages:
      - 503: Service Unavailable / Server Overload (after automated retries fail)
      - 429: API Quota or Rate Limit reached
      - 404: Model not found or unsupported
      - 400/401/403: Invalid or unauthorized API key
      - Empty or very short text input
      - Network connectivity or JSON decode errors
    """
    code = getattr(error, 'code', None)
    status = str(getattr(error, 'status', '')).upper()
    msg = str(getattr(error, 'message', '') or str(error))
    err_lower = f"{code} {status} {msg} {type(error).__name__}".lower()

    # 1. 503 Service Unavailable / Overloaded
    if code == 503 or "503" in err_lower or "unavailable" in err_lower or "overloaded" in err_lower:
        return (
            "⚠️ Google Gemini Service Temporarily Unavailable (HTTP 503):\n\n"
            "Google's AI servers are currently overloaded or undergoing temporary maintenance. "
            "We automatically attempted 3 retries with exponential backoff, but the server is still busy. "
            "Please wait 30–60 seconds and try submitting again."
        )

    # 2. 429 Rate Limit / Quota Exceeded
    if code == 429 or "429" in err_lower or "resource_exhausted" in err_lower or "quota" in err_lower:
        return (
            "⚠️ Gemini API Quota Exceeded (HTTP 429):\n\n"
            "You have hit your API request rate limit or daily free-tier quota for this model. "
            "Google AI Studio enforces limits on requests per minute (RPM) and requests per day (RPD). "
            "Please pause for 60 seconds before trying again, or check your quota usage at "
            "https://aistudio.google.com/."
        )

    # 3. 404 Model Not Found
    if code == 404 or "404" in err_lower or "not_found" in err_lower or "model not found" in err_lower:
        return (
            f"⚠️ Model Not Found (HTTP 404):\n\n"
            f"The selected model '{model_name}' was not found or is unavailable for your account. "
            "Please verify that 'gemini-3.8-flash' is enabled in your Google AI Studio account."
        )

    # 4. Invalid or Unauthorized API Key
    if (
        "api_key_invalid" in err_lower
        or "api key not valid" in err_lower
        or "invalid api key" in err_lower
        or (code in (400, 401, 403) and ("permission_denied" in err_lower or "invalid_argument" in err_lower or "unauthorized" in err_lower or "forbidden" in err_lower or "key" in err_lower))
    ):
        return (
            "⚠️ Invalid or Unauthorized Gemini API Key:\n\n"
            "The Gemini API key provided is invalid, expired, or lacking permissions. "
            "Please verify that you copied the complete key from Google AI Studio "
            "(https://aistudio.google.com/) and paste it in the sidebar or update your `.env` file."
        )

    # 5. Network / DNS Connection Issues
    if "connecterror" in err_lower or "getaddrinfo" in err_lower or "network" in err_lower or "connection" in err_lower:
        return (
            "⚠️ Network Connection Error:\n\n"
            "Could not reach Google Gemini API servers. Please check your internet connection, "
            "verify that your firewall or proxy allows HTTPS traffic, and try again."
        )

    # 6. JSON Parse Errors
    if "jsondecodeerror" in err_lower or isinstance(error, json.JSONDecodeError):
        return (
            "⚠️ Response Parsing Error:\n\n"
            "The model returned text that could not be parsed into valid JSON structure. "
            "This can happen on rare occasions if output generation was cut short. "
            "Please try submitting the text again."
        )

    # Fallback Generic Message
    return f"⚠️ API Request Error ({code or type(error).__name__}): {msg}"


def validate_input_text(text: str, min_chars: int = 20, min_words: int = 4) -> tuple[bool, str]:
    """
    Pre-validates user input text. Returns (is_valid, friendly_error_message).
    """
    stripped = text.strip() if text else ""
    if not stripped:
        return False, "⚠️ Text is empty: Please paste or type some text (or click one of the Quick Test Samples in the sidebar) before analyzing."

    words = stripped.split()
    if len(stripped) < min_chars or len(words) < min_words:
        return False, (
            f"⚠️ Text is very short ({len(stripped)} characters, {len(words)} words):\n\n"
            f"VisualMind AI requires at least a few descriptive sentences (minimum ~{min_chars} characters or {min_words}+ words) "
            "to reliably detect the structure (Article, Process, or Comparison) and synthesize meaningful visual outputs. "
            "Please add more context or detail to your input."
        )

    return True, ""

# -----------------------------------------------------------------------------
# 4. Helper: Mermaid Diagram Visualizer Component
# -----------------------------------------------------------------------------
def render_mermaid_chart(mermaid_code: str, height: int = 420):
    """
    Renders a Mermaid flowchart using Mermaid.js inside an isolated Streamlit HTML component.
    """
    clean_code = mermaid_code.strip()
    if clean_code.startswith("```mermaid"):
        clean_code = clean_code[10:]
    elif clean_code.startswith("```"):
        clean_code = clean_code[3:]
    if clean_code.endswith("```"):
        clean_code = clean_code[:-3]
    clean_code = clean_code.strip()

    safe_code = (
        clean_code.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    html_payload = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
        <script>
            mermaid.initialize({{
                startOnLoad: true,
                theme: 'default',
                securityLevel: 'loose',
                flowchart: {{
                    useMaxWidth: true,
                    htmlLabels: true,
                    curve: 'basis'
                }}
            }});
        </script>
        <style>
            body {{
                margin: 0;
                padding: 12px;
                background-color: transparent;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }}
            .mermaid-card {{
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 20px;
                display: flex;
                justify-content: center;
                align-items: center;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
                overflow-x: auto;
            }}
        </style>
    </head>
    <body>
        <div class="mermaid-card">
            <div class="mermaid">
{safe_code}
            </div>
        </div>
    </body>
    </html>
    """
    components.html(html_payload, height=height, scrolling=True)

# -----------------------------------------------------------------------------
# 5. Core Engine: Gemini API Analyzer with 503 Retries & Error Handling
# -----------------------------------------------------------------------------
def analyze_with_gemini(
    api_key: str,
    model_name: str = DEFAULT_MODEL,
    input_text: str = "",
    mode_override: str = "auto",
    max_retries: int = 3,
    allow_short: bool = False
) -> dict:
    """
    Calls Google Gemini using the official `google-genai` SDK to classify
    the input text and generate structured visual data in JSON format.

    Includes:
      - Exponential backoff retry on 503 Service Unavailable (up to max_retries).
      - Friendly, structured error handling for 429, 404, invalid keys, and network faults.
      - Optional allow_short flag for evaluation benchmark edge cases.
    """
    # 1. Input & Key Validation
    if not api_key or not api_key.strip():
        raise GeminiAppError(
            "⚠️ Missing API Key: Please provide a Gemini API Key in your `.env` file "
            "or enter one in the sidebar."
        )

    if not allow_short:
        is_valid, validation_msg = validate_input_text(input_text)
        if not is_valid:
            raise GeminiAppError(validation_msg)
    elif not input_text or not input_text.strip():
        raise GeminiAppError("⚠️ Empty Input: The provided input text is empty.")

    # 2. Client Initialization
    client = genai.Client(api_key=api_key.strip())

    system_instruction = (
        "You are VisualMind AI, an expert text classification and visual-synthesis assistant. "
        "Analyze the provided text and determine whether it best fits one of three categories:\n"
        "1. 'article'    : Informational, narrative, conceptual, or expository prose describing a topic.\n"
        "2. 'process'    : Sequential workflow, pipeline, step-by-step instructions, or lifecycle.\n"
        "3. 'comparison' : Evaluation, comparison, pros/cons, or benchmarking between two or more concepts, tools, or items.\n\n"
        "You must return ONLY a valid JSON object matching the exact schema specified."
    )

    prompt = f"""
Input Text to Analyze:
\"\"\"
{input_text}
\"\"\"

Requested Classification Mode: {mode_override}
(Note: If Requested Mode is not 'auto', enforce that specific category).

Schema requirements:
Return a JSON object with:
{{
  "category": "article" | "process" | "comparison",
  "category_display": "Article / Overview" | "Step-by-Step Process" | "Comparison & Trade-offs",
  "title": "A concise and meaningful title for the content",
  "category_reason": "A 1-2 sentence explanation of why this category fits the text best",

  // Populate IF category == "article":
  "article_data": {{
    "summary": "A cohesive 2 to 4 sentence executive summary of the content.",
    "key_points": [
      "Crucial takeaway or highlighted fact 1",
      "Crucial takeaway or highlighted fact 2",
      "Crucial takeaway or highlighted fact 3"
    ]
  }},

  // Populate IF category == "process":
  "process_data": {{
    "overview": "A brief 1-2 sentence summary of what this workflow achieves.",
    "mermaid_code": "flowchart TD\\n  A[Start / Trigger] --> B[Step 1]\\n  B --> C[Step 2]\\n  C --> D[End / Result]",
    "steps": [
      {{"step_number": 1, "title": "Step 1 Title", "description": "Short explanation of step 1"}},
      {{"step_number": 2, "title": "Step 2 Title", "description": "Short explanation of step 2"}}
    ]
  }},

  // Populate IF category == "comparison":
  "comparison_data": {{
    "overview": "A 1-2 sentence overview of the items being compared and key findings.",
    "entities_compared": ["Entity A", "Entity B"],
    "table_markdown": "| Criteria | Entity A | Entity B |\\n|---|---|---|\\n| Feature 1 | Details A | Details B |",
    "key_takeaways": [
      "Key difference or trade-off point 1",
      "Key difference or trade-off point 2"
    ]
  }}
}}

Guidelines for Mermaid:
- Always use 'flowchart TD' (top-down) or 'flowchart LR' (left-to-right).
- Wrap node text containing special characters inside double quotes like `A[\"Step with (parentheses)\"]`.
- Keep labels concise and visually readable.
"""

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.2,
        system_instruction=system_instruction
    )

    # 3. Call API with Exponential Backoff for HTTP 503
    backoff_delays = [1.5, 3.0]
    last_exception = None

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )
            raw_text = response.text.strip() if response.text else ""

            # Strip markdown block quotes if returned
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            return json.loads(raw_text)

        except Exception as e:
            last_exception = e
            code = getattr(e, 'code', None)
            status = str(getattr(e, 'status', '')).upper()
            err_lower = f"{code} {status} {str(e)}".lower()
            is_503 = (code == 503 or "503" in err_lower or "unavailable" in err_lower or "overloaded" in err_lower)

            # Retry on 503 up to max_retries
            if is_503 and attempt < max_retries - 1:
                delay = backoff_delays[attempt]
                time.sleep(delay)
                continue

            # Non-retryable error or retries exhausted: format friendly message and raise
            friendly_msg = format_gemini_error(e, model_name=model_name)
            raise GeminiAppError(friendly_msg) from e

    # Fallback if loop finishes unexpectedly
    friendly_msg = format_gemini_error(last_exception, model_name=model_name)
    raise GeminiAppError(friendly_msg)

# -----------------------------------------------------------------------------
# 6. UI Layout - Sidebar Configuration
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ VisualMind AI Settings")
    st.caption("Configure your API connection and generation parameters.")

    # API Key Handling
    st.markdown("#### 🔑 Gemini API Key")
    if env_api_key:
        masked_key = env_api_key[:6] + "..." + env_api_key[-4:] if len(env_api_key) > 10 else "***"
        st.success(f"Loaded from `.env` (`{masked_key}`)")
        active_api_key = env_api_key
        with st.expander("Override API Key"):
            user_override = st.text_input("Enter alternative key", type="password", key="override_key")
            if user_override.strip():
                active_api_key = user_override.strip()
    else:
        st.warning("No API key detected in `.env`.")
        active_api_key = st.text_input(
            "Paste your Gemini API Key:",
            type="password",
            placeholder="AIzaSy...",
            help="Get your free key at https://aistudio.google.com/"
        ).strip()

    st.markdown(
        "[👉 Get a free Gemini API Key](https://aistudio.google.com/)",
        unsafe_allow_html=True
    )
    st.divider()

    # Model Selection
    model_choice = st.selectbox(
        "🧠 Gemini Model:",
        options=["gemini-3.8-flash"],
        index=0,
        help="gemini-3.8-flash is the primary active, supported model."
    )

    # Classification Mode
    mode_selection = st.selectbox(
        "🎯 Processing Mode:",
        options=[
            ("auto", "⚡ Auto-Detect (AI Decides)"),
            ("article", "📰 Force Article (Summary & Points)"),
            ("process", "🔄 Force Process (Mermaid Flowchart)"),
            ("comparison", "⚖️ Force Comparison (Comparison Table)")
        ],
        format_func=lambda x: x[1],
        index=0
    )[0]

    st.divider()

    # Quick Samples
    st.markdown("#### 💡 Quick Test Samples")
    st.caption("Click any button to populate the text area instantly:")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("📰 Article", use_container_width=True):
            st.session_state["input_text"] = SAMPLES["article"]["text"]
    with col_btn2:
        if st.button("🔄 Process", use_container_width=True):
            st.session_state["input_text"] = SAMPLES["process"]["text"]

    if st.button("⚖️ Comparison", use_container_width=True):
        st.session_state["input_text"] = SAMPLES["comparison"]["text"]

    st.divider()
    st.markdown(
        "<small style='color: #64748b;'>Built with Streamlit & Google GenAI SDK</small>",
        unsafe_allow_html=True
    )

# -----------------------------------------------------------------------------
# 7. UI Layout - Main Application Canvas (Tabs)
# -----------------------------------------------------------------------------
st.title("🧠 VisualMind AI")
st.markdown(
    "**Turn unstructured text into structured visual insights.** VisualMind AI automatically classifies your input into an "
    "**Article**, a **Process**, or a **Comparison**, then dynamically produces an **Executive Summary**, an "
    "**Interactive Mermaid Flowchart**, or a **Markdown Comparison Table**."
)

tab_visualize, tab_eval = st.tabs([
    "✨ Analyze & Visualize",
    "🧪 Model Evaluation Benchmark (8 Test Cases)"
])

# =============================================================================
# TAB 1: Main Interactive Visualizer
# =============================================================================
with tab_visualize:
    # Text Area for Input
    if "input_text" not in st.session_state:
        st.session_state["input_text"] = ""

    user_text = st.text_area(
        label="Paste your text below:",
        value=st.session_state["input_text"],
        height=220,
        placeholder="Paste any article paragraph, workflow instructions, or comparison between technologies...",
        key="text_input_area"
    )

    # Metrics Bar
    char_count = len(user_text)
    word_count = len(user_text.split()) if user_text.strip() else 0

    col_m1, col_m2, col_m3, col_m4 = st.columns([1, 1, 1, 2])
    with col_m1:
        st.caption(f"📝 Words: **{word_count}**")
    with col_m2:
        st.caption(f"🔤 Characters: **{char_count}**")
    with col_m3:
        st.caption(f"⏱️ Read Time: **~{max(1, word_count // 150)} min**" if word_count > 0 else "⏱️ Read Time: 0 min")
    with col_m4:
        # Pre-check indicator
        if user_text.strip() and (char_count < 20 or word_count < 4):
            st.caption("⚠️ *Very short text: Consider adding more detail for best results.*")

    # Action Buttons
    col_act1, col_act2, _ = st.columns([2, 1, 4])
    with col_act1:
        analyze_clicked = st.button("🚀 Analyze & Visualize", type="primary", use_container_width=True)
    with col_act2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state["input_text"] = ""
            st.rerun()

    st.divider()

    # Processing & Results Presentation
    if analyze_clicked:
        if not active_api_key:
            st.error("⚠️ Please provide a Gemini API Key in the `.env` file or enter one in the sidebar to proceed.")
        else:
            # Pre-validation for empty / short text
            is_valid, validation_msg = validate_input_text(user_text)
            if not is_valid:
                st.warning(validation_msg)
            else:
                with st.spinner("🧠 VisualMind AI is analyzing structure and synthesizing visualizations..."):
                    try:
                        result = analyze_with_gemini(
                            api_key=active_api_key,
                            model_name=model_choice,
                            input_text=user_text,
                            mode_override=mode_selection
                        )
                        st.session_state["last_result"] = result
                    except GeminiAppError as e:
                        st.error(str(e))
                        st.info("💡 **Need help?** Check your API key at https://aistudio.google.com/ or try switching models in the sidebar.")
                    except Exception as e:
                        st.error(f"❌ Analysis failed: {str(e)}")
                        st.info("Tip: Double-check your API key validity, internet connection, and model availability.")

    # Render Results from Session State
    if "last_result" in st.session_state and st.session_state["last_result"]:
        res = st.session_state["last_result"]
        category = res.get("category", "article").lower()
        category_display = res.get("category_display", category.capitalize())
        title = res.get("title", "Analysis Result")
        reason = res.get("category_reason", "")

        badge_icons = {
            "article": "📰",
            "process": "🔄",
            "comparison": "⚖️"
        }
        icon = badge_icons.get(category, "📌")

        st.markdown(f"### {icon} {title}")

        # Classification Badge Callout
        col_b1, col_b2 = st.columns([1, 4])
        with col_b1:
            st.success(f"**Detected Type:**\n\n{icon} {category_display}")
        with col_b2:
            st.info(f"**Classification Context:**\n\n{reason}")

        st.write("")

        # Render Based on Category
        if category == "article":
            article_data = res.get("article_data", {})
            summary = article_data.get("summary", "No summary provided.")
            key_points = article_data.get("key_points", [])

            st.markdown("#### 📝 Executive Summary")
            st.info(summary)

            st.markdown("#### 🎯 Key Takeaways")
            for i, point in enumerate(key_points, 1):
                st.markdown(f"- **Point {i}:** {point}")

        elif category == "process":
            process_data = res.get("process_data", {})
            overview = process_data.get("overview", "")
            mermaid_code = process_data.get("mermaid_code", "")
            steps = process_data.get("steps", [])

            if overview:
                st.markdown("#### ℹ️ Process Overview")
                st.write(overview)

            st.markdown("#### 📊 Interactive Mermaid Flowchart")
            if mermaid_code:
                render_mermaid_chart(mermaid_code, height=450)
                
                with st.expander("🔍 View Mermaid Flowchart Code"):
                    st.code(mermaid_code, language="mermaid")
            else:
                st.warning("No Mermaid code was generated.")

            if steps:
                st.markdown("#### 📋 Step-by-Step Breakdown")
                for step in steps:
                    s_num = step.get("step_number", "•")
                    s_title = step.get("title", "Step")
                    s_desc = step.get("description", "")
                    st.markdown(f"**Step {s_num}: {s_title}**  \n{s_desc}")

        elif category == "comparison":
            comparison_data = res.get("comparison_data", {})
            overview = comparison_data.get("overview", "")
            table_markdown = comparison_data.get("table_markdown", "")
            takeaways = comparison_data.get("key_takeaways", [])

            if overview:
                st.markdown("#### ℹ️ Comparison Overview")
                st.write(overview)

            st.markdown("#### 📊 Comparison Table")
            if table_markdown:
                st.markdown(table_markdown)
            else:
                st.warning("No comparison table was generated.")

            if takeaways:
                st.markdown("#### 💡 Trade-off Insights & Takeaways")
                for item in takeaways:
                    st.markdown(f"- {item}")

        # Developer View
        with st.expander("🛠️ Developer View (Raw JSON Response)"):
            st.json(res)

# =============================================================================
# TAB 2: Model Evaluation Benchmark Suite (8 Labeled Test Cases)
# =============================================================================
with tab_eval:
    st.subheader("🧪 Automated Model Evaluation Benchmark")
    st.markdown(
        "Run an automated benchmark test across **8 labeled test cases** to evaluate VisualMind AI's categorization accuracy. "
        "The test suite covers standard articles, processes, and comparisons, plus tricky edge cases including "
        "mixed-intent narratives, embedded workflows, and very short texts. "
        "Each run executes **exactly 8 API calls** (1 per test case)."
    )

    # Preview of the Benchmark Suite
    with st.expander("📋 Inspect the 8 Benchmark Test Cases"):
        for case in EVALUATION_CASES:
            icon_map = {"article": "📰", "process": "🔄", "comparison": "⚖️"}
            exp_icon = icon_map.get(case["category_expected"], "📌")
            st.markdown(
                f"**Case #{case['id']}: {case['name']}**  \n"
                f"- **Expected Category:** `{exp_icon} {case['category_expected'].upper()}` | **Difficulty:** *{case['difficulty']}*  \n"
                f"- **Description:** {case['description']}  \n"
                f"- **Why Tricky:** {case['why_tricky']}  \n"
                f"- *Text Preview:* `{case['text'][:120]}...`"
            )
            st.divider()

    # Benchmark Control Bar
    col_eval_btn, col_eval_reset, _ = st.columns([2, 1, 3])
    with col_eval_btn:
        run_benchmark = st.button("▶️ Run Benchmark (8 API Calls)", type="primary", use_container_width=True)
    with col_eval_reset:
        if st.button("🔄 Reset Results", use_container_width=True):
            if "benchmark_results" in st.session_state:
                del st.session_state["benchmark_results"]
            st.rerun()

    # Execution Loop (Exactly 8 API Calls)
    if run_benchmark:
        if not active_api_key:
            st.error("⚠️ Please provide a Gemini API Key in `.env` or in the sidebar before running the benchmark.")
        else:
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            evaluated_records = []
            total_cases = len(EVALUATION_CASES)

            for i, case in enumerate(EVALUATION_CASES):
                case_id = case["id"]
                case_name = case["name"]
                expected = case["category_expected"].strip().lower()

                # Pause 15 seconds between API calls to respect free-tier rate limits
                if i > 0:
                    status_text.info("⏳ Waiting to avoid the free-tier rate limit...")
                    time.sleep(15)

                status_text.info(f"⏳ Running case {i + 1}/{total_cases}: **{case_name}** ({case['difficulty']})...")

                res = None
                last_err = None
                call_elapsed = 0.0

                # Execute with 1 retry on HTTP 429 after waiting 60 seconds
                for attempt in range(2):
                    start_time = time.time()
                    try:
                        res = analyze_with_gemini(
                            api_key=active_api_key,
                            model_name=model_choice,
                            input_text=case["text"],
                            mode_override="auto",
                            allow_short=True
                        )
                        call_elapsed = round(time.time() - start_time, 2)
                        last_err = None
                        break
                    except Exception as ex:
                        call_elapsed = round(time.time() - start_time, 2)
                        last_err = ex
                        is_429 = (
                            "429" in str(ex)
                            or "quota" in str(ex).lower()
                            or "resource_exhausted" in str(ex).lower()
                            or getattr(ex, "code", None) == 429
                            or (hasattr(ex, "__cause__") and getattr(ex.__cause__, "code", None) == 429)
                        )
                        if is_429 and attempt == 0:
                            status_text.info("⏳ Waiting to avoid the free-tier rate limit...")
                            time.sleep(60)
                            status_text.info(f"⏳ Retrying case {i + 1}/{total_cases}: **{case_name}** ({case['difficulty']})...")
                            continue
                        break

                if last_err is None and res is not None:
                    predicted = str(res.get("category", "")).strip().lower()
                    is_match = (predicted == expected)
                    reason = res.get("category_reason", "")
                    title = res.get("title", "")

                    evaluated_records.append({
                        "id": case_id,
                        "name": case_name,
                        "difficulty": case["difficulty"],
                        "expected": expected,
                        "predicted": predicted,
                        "is_match": is_match,
                        "elapsed_s": call_elapsed,
                        "title": title,
                        "reason": reason,
                        "error": None,
                        "text": case["text"]
                    })
                else:
                    evaluated_records.append({
                        "id": case_id,
                        "name": case_name,
                        "difficulty": case["difficulty"],
                        "expected": expected,
                        "predicted": "error",
                        "is_match": False,
                        "elapsed_s": call_elapsed,
                        "title": "Call Failed",
                        "reason": "",
                        "error": str(last_err),
                        "text": case["text"]
                    })

                progress_bar.progress((i + 1) / total_cases)

            status_text.empty()
            progress_bar.empty()

            # Store in session state to prevent re-execution on UI interactions
            st.session_state["benchmark_results"] = {
                "model": model_choice,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "records": evaluated_records
            }
            st.success("✅ Benchmark evaluation finished! Exactly 8 API calls executed.")

    # Display Benchmark Results
    if "benchmark_results" in st.session_state:
        bm = st.session_state["benchmark_results"]
        records = bm["records"]
        total = len(records)
        correct_count = sum(1 for r in records if r["is_match"])
        accuracy = (correct_count / total) * 100 if total > 0 else 0
        total_time = sum(r["elapsed_s"] for r in records)

        st.markdown(f"### 📊 Benchmark Results (`{bm['model']}`)")
        st.caption(f"Evaluated on {bm['timestamp']} | Total Execution Time: ~{total_time:.1f}s")

        # Top Metric Cards
        col_res1, col_res2, col_res3, col_res4 = st.columns(4)
        with col_res1:
            st.metric(
                label="🎯 Overall Accuracy",
                value=f"{accuracy:.1f}%",
                delta=f"{correct_count}/{total} Correct"
            )
        with col_res2:
            st.metric(
                label="📡 API Calls Used",
                value=f"{total} Calls",
                help="Strictly bounded to 1 API call per test case"
            )
        with col_res3:
            st.metric(
                label="✅ Correct Matches",
                value=f"{correct_count}"
            )
        with col_res4:
            st.metric(
                label="❌ Mismatches / Errors",
                value=f"{total - correct_count}"
            )

        # Visual Accuracy Progress Bar
        st.progress(accuracy / 100.0)

        # Predicted vs Expected Comparison Table
        st.markdown("#### 📋 Predicted vs Expected Breakdown")

        table_rows = []
        table_rows.append("| # | Test Case Name | Expected Type | Predicted Type | Match Status | Latency | Difficulty / Case Type |")
        table_rows.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

        for r in records:
            icon_exp = {"article": "📰", "process": "🔄", "comparison": "⚖️"}.get(r["expected"], "📌")
            icon_pred = {"article": "📰", "process": "🔄", "comparison": "⚖️"}.get(r["predicted"], "❓")
            status_icon = "✅ MATCH" if r["is_match"] else "❌ MISMATCH" if r["predicted"] != "error" else "⚠️ ERROR"
            table_rows.append(
                f"| **{r['id']}** | {r['name']} | `{icon_exp} {r['expected']}` | `{icon_pred} {r['predicted']}` | **{status_icon}** | {r['elapsed_s']}s | *{r['difficulty']}* |"
            )

        st.markdown("\n".join(table_rows))
        st.write("")

        # Deep-Dive Expanders for Each Case
        st.markdown("#### 🔍 Detailed Case Inspection")
        for r in records:
            status_badge = "✅ MATCH" if r["is_match"] else "❌ MISMATCH" if r["predicted"] != "error" else "⚠️ ERROR"
            expander_title = f"Case #{r['id']} [{status_badge}] : {r['name']} (Expected: {r['expected']} | Predicted: {r['predicted']})"
            
            with st.expander(expander_title):
                col_d1, col_d2 = st.columns([1, 1])
                with col_d1:
                    st.markdown(f"**Expected Category:** `{r['expected'].upper()}`")
                    st.markdown(f"**Predicted Category:** `{r['predicted'].upper()}`")
                    st.markdown(f"**Difficulty:** *{r['difficulty']}*")
                    st.markdown(f"**Response Latency:** `{r['elapsed_s']} seconds`")
                with col_d2:
                    if r["title"]:
                        st.markdown(f"**Synthesized Title:** *{r['title']}*")
                    if r["reason"]:
                        st.markdown(f"**Model Reasoning:** *\"{r['reason']}\"*")
                    if r["error"]:
                        st.error(f"Error Encountered: {r['error']}")

                st.markdown("**Input Text Evaluated:**")
                st.info(r["text"])
