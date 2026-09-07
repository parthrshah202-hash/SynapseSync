# SynapseSync

> An autonomous, agentic ETL and observability pipeline that ingests Socratic problem-solving transcripts from **Claude.ai**, extracts structured learning artifacts, enforces guardrails against collisions and schema drift, and files entries into multi-database **Notion** engineering trackers.

---

## 1. Overview

**SynapseSync** solves the friction of personal knowledge management for technical interview preparation. When practicing Data Structures & Algorithms (DSA) or SQL, the user pairs with **Claude.ai** acting as a strict Socratic mentor—refusing to give direct answers, giving iterative hints, and requiring the user to articulate optimal complexities and gotcha points. Upon completing a problem, Claude produces a standardized summary block (`<Problem> — Notion Notes`). The user exports the chat transcript (`.md`) into a synchronized folder. Rather than manually copying notes, formatting Notion columns, and locating specific topic databases, SynapseSync runs automatically via GitHub Actions: it ingests new transcripts from Google Drive, authenticates file provenance, extracts problem metadata using deterministic regex with an LLM fallback (Google Gemini), runs an agentic decision loop to resolve destinations and check for collisions, and writes cleanly formatted First Solves and Revisions into Notion.

---

## 2. Architecture & Data Flow

```text
+---------------------------------------------------------------------------------------+
|                                     LOCAL MACHINE                                     |
|  1. User solves problem via Socratic dialogue on claude.ai                            |
|  2. Claude outputs standardized "<Problem> — Notion Notes" summary block              |
|  3. User exports transcript (.md) to local folder synced with Google Drive            |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v (Background Sync)
+---------------------------------------------------------------------------------------+
|                                 GOOGLE DRIVE FOLDER                                   |
|  Decoupled file-transport layer: stores "<ChatTitle>-<YYYY-MM-DD>.md" exports         |
+-------------------------------------------+-------------------------------------------+
                                            |
                   Daily Cron Schedule (17:30 UTC)
                   or Manual Workflow Dispatch
                                            v
+---------------------------------------------------------------------------------------+
|                         GITHUB ACTIONS RUNNER (Ubuntu Latest)                         |
|                                                                                       |
|  [PHASE 1: INGESTION & FILTERING] (src/drive/ingestion.py, src/classifier.py)        |
|  - Drive API fetches files inside target folder (oauth2 refresh token flow)           |
|  - Pre-filter: Check filename pattern "<Title>-<YYYY-MM-DD>.md"                       |
|  - Calculate SHA-256 content hash & check manifest.json cache                         |
|  - Provenance Check: Verify Claude export signature in header lines                   |
|  - Domain Classifier: Verify mandatory "— Notion Notes" signature & domain signals    |
|                                                                                       |
|  [PHASE 2: EXTRACTION & VALIDATION] (src/extraction/)                                 |
|  - cleaner.py: Strip conversational preamble, disclaimers, and UI artifacts           |
|  - splitter.py: Partition multi-problem transcripts into discrete segments & dates    |
|  - parser.py: Fast deterministic regex parser extracting contract key-value pairs    |
|  - fallback.py: Google Gemini fallback for conversational / malformed blocks          |
|  - validator.py: Enforce required keys, field contracts, and domain types             |
|                                                                                       |
|  [PHASE 3: AGENT DECISION LOOP & GUARDRAILS] (src/agent/core.py)                      |
|  - Domain Routing:                                                                    |
|      * SQL: Routes to single tracker database (NOTION_SQL_DB_ID)                      |
|      * DSA: Recursively queries NOTION_DSA_PARENT_PAGE_ID to discover live topic DBs   |
|  - Search & Conflict Guardrails (src/notion_tools/search.py):                         |
|      * Normalized fuzzy bidirectional title search against target database            |
|      * Sequel Guard: Blocks "Reverse Linked List" matching "Reverse Linked List II"   |
|      * First Solve: If entry already exists -> Halt, flag "needs_review"              |
|      * Revision: If entry does not exist -> Halt, flag "needs_review"                 |
|      * Multi-Topic Collision: Revision matches across >1 topic DB -> Flag review      |
|                                                                                       |
|  [PHASE 4: NOTION MUTATION ENGINE] (src/notion_tools/mutations.py)                    |
|  - Resolve Notion API 2025-09-03: database_id -> data_source_id                       |
|  - First Solve: client.pages.create() with all fields mapped to live schema types     |
|  - Revision: client.pages.update() strictly isolated to [Revision Date,               |
|    2nd Revision Needed, Notes] (protects canonical title and initial notes)           |
|                                                                                       |
|  [PHASE 5: STATE PERSISTENCE] (src/orchestrate.py -> manifest.json)                   |
|  - Update manifest status (success, needs_review, skipped_unclassified)               |
|  - Commit & push updated manifest.json back to GitHub via github-actions[bot]         |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
|                                   NOTION WORKSPACE                                    |
|   +---------------------------------------+  +-------------------------------------+  |
|   |         DSA Topic Databases           |  |          SQL Tracker DB             |  |
|   |  - Arrays                             |  |  Single database tracking all SQL   |  |
|   |  - Binary Trees                       |  |  problems, query solutions,         |  |
|   |  - LinkedList                         |  |  buckets, notes, and revisions      |  |
|   |  - Sliding Window & Two Pointer...    |  |                                     |  |
|   +---------------------------------------+  +-------------------------------------+  |
+---------------------------------------------------------------------------------------+
```

---

## 3. Repository & Folder Structure

```text
SynapseSync/
├── .github/
│   └── workflows/
│       ├── ci.yml                          # Continuous integration workflow running pytest on push/PR
│       └── process-transcripts.yml         # Scheduled cron workflow executing ingestion and Notion sync
├── dashboard/
│   ├── app.py                              # Streamlit observability web application with sidebar navigation
│   ├── loader.py                           # Parses manifest.json into summary metrics and review queues
│   ├── style.css                           # Tactile paper elevation theme, equalized cards, and sidebar styling
│   └── views/
│       ├── pipeline.py                     # SVG-animated 4-layer pipeline architecture topology view
│       └── review.py                       # Review Queue UI for inspecting guardrail-flagged operations
├── src/
│   ├── classifier.py                       # Filename regex, export signature checks, and domain classification
│   ├── orchestrate.py                      # Main entrypoint managing batch execution, manifest updates, and git commit
│   ├── agent/
│   │   ├── __init__.py                     # Package export for the agentic core
│   │   └── core.py                         # Decision engine handling routing, dynamic discovery, search, and guardrails
│   ├── drive/
│   │   ├── __init__.py                     # Package export for Google Drive ingestion
│   │   └── ingestion.py                    # Drive API OAuth client, file listing, media download, and SHA-256 hashing
│   ├── extraction/
│   │   ├── __init__.py                     # Package export for extraction pipeline
│   │   ├── cleaner.py                      # Cleans conversation headers, UI noise, and markdown disclaimers
│   │   ├── contracts.py                    # Schema field definitions, canonical topics, and contract schemas
│   │   ├── extractor.py                    # 7-step extraction coordinator (clean -> split -> parse -> fallback -> validate)
│   │   ├── fallback.py                     # Google Gemini LLM fallback for conversational or malformed blocks
│   │   ├── parser.py                       # Deterministic regex parser for standardized Notion Notes markdown
│   │   ├── splitter.py                     # Partitions multi-problem exports into discrete segments and dates
│   │   └── validator.py                    # Validates parsed payloads against domain-specific field contracts
│   └── notion_tools/
│       ├── __init__.py                     # Package export for Notion API tools
│       ├── discovery.py                    # Recursively discovers child topic databases under DSA parent page
│       ├── helpers.py                      # Notion client factory and database_id -> data_source_id resolver
│       ├── mutations.py                    # Builds property payloads and executes pages.create and pages.update
│       ├── schema.py                       # Fetches and caches live property schemas and select/status options
│       └── search.py                       # Fuzzy bidirectional title search and sequel collision guard
├── tests/
│   ├── fixtures/                           # Sample markdown exports and synthetic transcripts for testing
│   ├── scratch_db.py                       # Standalone evaluation script for verifying fuzzy title match edge cases
│   ├── smoke_drive.py                      # Live verification script for Google Drive OAuth and folder access
│   ├── smoke_gemini.py                     # Live verification script for Google Gemini API key and prompt completion
│   ├── smoke_notion.py                     # Live verification script for Notion parent page and database schemas
│   ├── test_agent.py                       # Tests for agent decision loop, routing, and guardrail alerts
│   ├── test_classifier.py                  # Tests for export filename validation, signatures, and domain checks
│   ├── test_dashboard_loader.py            # Tests for dashboard manifest parser and overview metrics
│   ├── test_extraction.py                  # Tests for cleaning, splitting, regex parsing, and schema contracts
│   ├── test_orchestration.py               # Tests for batch orchestration, manifest transitions, and retry logic
│   └── test_search.py                      # Tests for title normalization, sequel collision prevention, and fuzzy search
├── .env.example                            # Template for environment variables and API credentials
├── .gitignore                              # Git ignore rules for environments, secrets, and temp caches
├── manifest.json                           # State database tracking processed file IDs, hashes, and review items
├── pyproject.toml                          # Project configuration and pytest execution flags
└── requirements.txt                        # Production and testing Python dependencies
```

---

## 4. Key Architectural Decisions

### 1. Google Drive as Decoupled File Transport
* **Decision**: Use a dedicated Google Drive folder (synced to the user's local machine via Google Drive for Desktop) as the ingestion queue rather than a local file watcher, webhook, or direct upload.
* **Rationale**: The compute runner executes on GitHub Actions in the cloud, which cannot inspect the user's local filesystem. Google Drive provides a zero-maintenance, cross-platform cloud file transport. The user simply drops the export into their synced Downloads or Drive folder; the scheduled runner pulls it via Google Drive API v3 using an OAuth 2.0 refresh token.

### 2. Dual Filename + Content Provenance Check
* **Decision**: Enforce a two-tier gate before ingesting any file: regex filename validation (`<ChatTitle>-<YYYY-MM-DD>.md`) followed by inspecting the first 5 lines for the Claude Exporter signature (`_Created: YYYY-MM-DDTHH:MM:SSZ_`), and requiring the `[-—–]\s*Notion\s*Notes` block signature.
* **Rationale**: Early in development, an unrelated exported markdown file named with a date happened to contain SQL keywords (`SELECT`, `FROM`). Because the classifier initially relied on filename pattern and raw keyword searches, the unrelated chat was falsely classified as SQL. Requiring both the exporter header and the explicit Notion Notes signature completely eliminated false positives.

### 3. Dynamic Multi-Database Discovery for DSA
* **Decision**: Discover DSA topic databases dynamically via `client.blocks.children.list()` on `NOTION_DSA_PARENT_PAGE_ID` rather than hardcoding static database IDs in `.env` or code.
* **Rationale**: The user's actual Notion setup is organized pedagogically with **one database per topic** (e.g. `Arrays`, `Binary Trees`, `LinkedList`, `Heaps`) living under a central DSA page, rather than one giant flat table. Some databases are direct `child_database` blocks; others are nested inside `child_page` blocks. `discovery.py` crawls the parent hierarchy at runtime, normalizes topic names, and maps them to active data source IDs. If the user creates a new topic in Notion (e.g. `Tries` or `Dynamic Programming`), SynapseSync supports it immediately without code changes.

### 4. Mandatory `database_id` to `data_source_id` Resolution (Notion API `2025-09-03`)
* **Decision**: Pass all raw database IDs through `resolve_data_source_id()`, which queries `client.databases.retrieve(database_id=...)` and extracts `db["data_sources"][0]["id"]`.
* **Rationale**: Notion API version `2025-09-03` overhauled the underlying database architecture to support multi-source views. Under this version:
  - Querying databases via the old endpoint is superseded by querying data sources (`client.data_sources.query` or `data_sources/{id}/query`).
  - Creating pages inside databases using `{"parent": {"database_id": ...}}` is deprecated and rejected by the API. Page creation requires `{"parent": {"type": "data_source_id", "data_source_id": ...}}`.
  SynapseSync resolves this once per database, caching the result in memory.

### 5. Pass-Through Buckets vs. Strictly Validated Difficulties & Revisions
* **Decision**: Allow `Bucket` values to pass through without schema restrictions, while strictly validating `Difficulty`, `Revision Needed`, and `2nd Revision Needed` against live Notion schema options.
* **Rationale**: The "Bucket" represents the algorithmic sub-pattern or technique (e.g. *"Two Pointer"*, *"Prefix Sum"*, *"Self Join"*, *"Sliding Window Variable"*). The user continuously invents and refines these categories as their curriculum evolves; Notion select properties dynamically accept new values. In contrast, `Difficulty` (`Easy`, `Medium`, `Hard`) and `Revision Needed` (`Low`, `Mid`, `High`) control Kanban board columns, formula properties, and filtered review views. A typo in these fields would break database views, so they are strictly validated before write.

### 6. Fuzzy Bidirectional Title Search with the "Sequel Guard"
* **Decision**: Normalize titles by stripping LeetCode prefixes (`LC 206`, `206.`), punctuation, and whitespace, query candidates using word-based OR filters, and verify matches using bidirectional substring matching with a strict "Sequel Guard".
* **Rationale**: Claude might export a problem as `"206. Reverse Linked List"`, `"Reverse Linked List (LC 206)"`, or `"Parts Assembly — Unfinished Parts"`, while the database contains `"Reverse Linked List"` or `"Unfinished Parts"`. Simple exact matching failed repeatedly. However, naive substring matching (`n1 in n2`) introduced a dangerous bug: `"Reverse Linked List"` matched `"Reverse Linked List II"`. The **Sequel Guard** evaluates the remaining string after substring removal: if the remainder contains numeric digits (`2`) or sequel tokens (`i`, `ii`, `iii`, `iv`, `part`, `version`), the match is rejected.

### 7. Hard Property Isolation in `append_revision`
* **Decision**: Hard-code `REVISION_ALLOWED_PROPERTIES = {"Revision Date", "2nd Revision Needed", "Notes"}` in `build_properties_payload()`.
* **Rationale**: When updating an existing page for a revision, `pages.update` is called. If the payload builder included first-solve fields like `Problem` (title), `Date solved`, or `Optimal Approach`, any subtle differences in Claude's revision output would overwrite the user's original, carefully refined first-solve notes. Hard property isolation ensures that revisions can only ever update revision dates, flags, and revision remarks.

### 8. Fail-Safe Guardrails for Ambiguous Routing
* **Decision**: Whenever routing ambiguity is detected, halt execution on that problem and record status as `"needs_review"`.
* **Rationale**: The agent encounters three ambiguous scenarios:
  1. **First Solve Collision**: A First Solve is submitted, but the problem already exists in Notion. (Did the user intend a Revision? Or solve a sequel?)
  2. **Orphan Revision**: A Revision is submitted, but no matching problem exists anywhere in the database. (You cannot revise an unlogged problem.)
  3. **Multi-Topic Revision Collision**: A Revision lacks an explicit topic and matches problem titles in more than one DSA database.
  Rather than guessing and corrupting data or silently dropping information, the operation is halted, the exact payload and collision reason are saved to `manifest.json`, and the item is presented in the Streamlit Review Queue for manual inspection.

### 9. Four-State Manifest Lifecycle
* **Decision**: Track every processed file in `manifest.json` by its Google Drive `file_id` and SHA-256 `content_hash` across four explicit states:
  - **`success`**: File processed and synced to Notion. On future runs with the same content hash, it is skipped (`stats["skipped"]`). If the user edits the file in Drive, the content hash changes and triggers a re-run.
  - **`needs_review`**: File contains an ambiguous operation or schema mismatch. The full payload and error reason are persisted in `manifest.json`. It is skipped on subsequent runs until resolved, preventing duplicate error spam.
  - **`skipped_unclassified`**: File is an authentic Claude export but does not contain a Notion Notes block. It is recorded so the runner does not waste compute re-reading it on every run.
  - **`failed`**: Transient network failures, rate limits, or unexpected exceptions. The file is **omitted** from the manifest `processed` dictionary, ensuring it will be retried automatically on the next scheduled run.

---

## 5. Bugs Found and Fixed During Development

Building this pipeline against live cloud APIs uncovered critical real-world edge cases. Documenting them highlights the system's robustness:

### 1. Notion API Version Migration (`2025-09-03`) Parent Shape Bug
* **Symptom**: Page creation failed with Notion API HTTP 400 validation errors stating that `parent.database_id` was invalid or unrecognized, despite passing valid database IDs.
* **Root Cause**: The project was configured to use Notion API version `2025-09-03`. In this version, Notion decoupled databases from their underlying data sources. Passing `{"parent": {"database_id": ...}}` is no longer supported for page mutations.
* **Fix**: Built `resolve_data_source_id()` in `src/notion_tools/helpers.py`. The pipeline now calls `client.databases.retrieve()` to extract `data_sources[0]["id"]` and constructs page creation requests using `{"parent": {"type": "data_source_id", "data_source_id": resolved_id}}`.

### 2. SQL Tracker Title-Matching Collision Bug
* **Symptom**: Processing a transcript for the SQL problem *"Finding unfinished parts in assembly"* resulted in a duplicate page being created in the live SQL tracker, even though an entry titled *"Unfinished Parts"* already existed.
* **Root Cause**: The initial search query used exact title matching (`filter={"property": "Problem", "title": {"equals": ...}}`). Because Claude's transcript block titled the problem `"Parts Assembly — Unfinished Parts"`, the exact search failed, returned `None`, and treated the entry as a brand-new First Solve.
* **Fix**: Replaced exact matching in `src/notion_tools/search.py` with an initial query-expansion search (`contains` queries on significant words > 3 characters), followed by local normalized bidirectional containment checking. Added the `test_search_sql_parts_assembly` unit test to guarantee compatibility.

### 3. Title Overwrite Bug in `append_revision`
* **Symptom**: During dry-run inspection of revision payloads, the payload builder generated updates that included the `Problem` (title) property. If executed against Notion, this would overwrite canonical problem titles with whatever informal name variant Claude generated during a revision session.
* **Root Cause**: `build_properties_payload()` mapped all keys present in the extracted dictionary to schema properties without differentiating between first-solve creation and revision updates.
* **Fix**: Introduced `is_revision` branching in `src/notion_tools/mutations.py` and strictly filtered input data against `REVISION_ALLOWED_PROPERTIES = {"Revision Date", "2nd Revision Needed", "Notes"}` when `is_revision=True` or `contract_data["Type"] == "Revision"`.

### 4. False-Positive Classification on Unrelated Chat Exports
* **Symptom**: An unrelated chat export discussing a database architectural review was picked up by the ingestion loop and classified as a `SQL` problem, triggering extraction failures.
* **Root Cause**: The original `classifier.py` checked for the presence of the SQL keywords `SELECT` and `FROM` anywhere in the transcript. Because the user discussed database queries in a general engineering chat, regex matched the keywords.
* **Fix**: Added a strict prerequisite check in `classify_domain()`: the content **must** contain `re.search(r"(?i)[-—–]\s*Notion\s*Notes", content)`. Without this signature block, classification immediately returns `None`, classifying the file as `skipped_unclassified`.

---

## 6. Setup Instructions

### Prerequisites & Accounts

1. **Google Cloud Console**:
   - Create a project and enable the **Google Drive API**.
   - Configure the **OAuth Consent Screen** (External or Internal).
   - Create an **OAuth 2.0 Client ID** (Application type: *Desktop application*).
   - Generate a Refresh Token with the scope `https://www.googleapis.com/auth/drive.readonly` (using the `google-auth-oauthlib` CLI or OAuth Playground).
2. **Google AI Studio**:
   - Generate a **Google Gemini API Key** for transcript fallback extraction.
3. **Notion Developer Integration**:
   - Create an internal integration token at [notion.so/profile/integrations](https://www.notion.so/profile/integrations).
   - Copy the secret key (`secret_...`).
   - In Notion, share your **DSA Parent Page** and your **SQL Database** with the integration (via `...` -> *Connections* -> *Connect to <Integration Name>*).

---

### Environment Variables

Copy `.env.example` to `.env` and populate your credentials:

```bash
cp .env.example .env
```

| Variable | Description | Example / Source |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API key for fallback extraction | `AIzaSy...` (from Google AI Studio) |
| `NOTION_TOKEN` | Internal Notion Integration secret token | `secret_...` (from Notion integrations) |
| `NOTION_DSA_PARENT_PAGE_ID` | Notion Page ID containing child topic databases | 32-char hex string from parent page URL |
| `NOTION_SQL_DB_ID` | Notion Database ID for the SQL tracker | 32-char hex string from SQL database URL |
| `GOOGLE_DRIVE_FOLDER_ID` | Google Drive folder ID containing `.md` exports | Alpha-numeric ID from Google Drive URL |
| `GOOGLE_OAUTH_CLIENT_ID` | Google Cloud OAuth 2.0 Client ID | `...apps.googleusercontent.com` |
| `GOOGLE_OAUTH_CLIENT_SECRET`| Google Cloud OAuth 2.0 Client Secret | Client secret string from GCP |
| `GOOGLE_OAUTH_REFRESH_TOKEN`| OAuth 2.0 refresh token with `drive.readonly` | Long-lived refresh token string |

---

### Notion Workspace Structure Expectations

SynapseSync natively expects the following workspace layout:

```text
Notion Workspace
├── DSA Problem Tracker (Parent Page — NOTION_DSA_PARENT_PAGE_ID)
│   ├── Arrays (Child Database or Page containing Database)
│   ├── Binary Search (Child Database)
│   ├── Binary Trees (Child Database)
│   ├── Bit Manipulation (Child Database)
│   ├── Greedy Algorithm (Child Database)
│   ├── Heaps (Child Database)
│   ├── LinkedList (Child Database)
│   ├── Recursion (Child Database)
│   ├── Sliding Window and Two Pointer (Child Database)
│   ├── Sorting (Child Database)
│   └── Stack & Queue (Child Database)
└── SQL Problem Tracker (Database — NOTION_SQL_DB_ID)
```

#### Database Schema Properties Expected

* **DSA Topic Databases**:
  - `Problem` (*title*): The problem name
  - `Date solved` (*date*): Date of first solve
  - `Bucket` or `Pattern / Bucket` (*select* or *multi_select*): Technique / sub-pattern
  - `Brute-Force` (*rich_text*): Initial brute force approach
  - `Optimal Approach` (*rich_text*): Optimal algorithm & complexities
  - `Gotcha-Point` (*rich_text*): Critical edge case or insight
  - `My Mistake` (*rich_text*): Notes on initial failure/misconception
  - `Revision Needed` (*select* or *status*): `Low`, `Mid`, or `High`
  - `Revision Date` (*date*): Date of most recent revision
  - `2nd Revision Needed` (*select* or *status*): `Low`, `Mid`, or `High`
  - `Notes` (*rich_text*): Revision notes / reflections

* **SQL Tracker Database**:
  - `Problem` (*title*): The problem name
  - `Date solved` (*date*): Date of first solve
  - `Bucket` (*select* or *multi_select*): SQL pattern (e.g. *Window Functions*, *Self Join*)
  - `Difficulty` (*select* or *status*): `Easy`, `Medium`, or `Hard`
  - `Query` (*rich_text*): The final SQL query solution
  - `Notes` (*rich_text*): Learning points or notes
  - `Revision Needed` (*select* or *status*): `Low`, `Mid`, or `High`
  - `Revision Date` (*date*): Date of most recent revision
  - `2nd Revision Needed` (*select* or *status*): `Low`, `Mid`, or `High`

#### Adapting to a Different Notion Structure
- **Single Flat DSA Database**: If you prefer one single DSA database instead of per-topic databases, set `NOTION_DSA_PARENT_PAGE_ID` to your database ID and update `discover_dsa_topics()` in `src/notion_tools/discovery.py` to return `{ "default": resolve_data_source_id(client, parent_page_id) }`.
- **Custom Field Names**: `src/notion_tools/mutations.py` includes dynamic property resolution (`map_contract_key_to_schema_prop`). If your Notion database uses `"Pattern"` instead of `"Bucket"`, or `"2nd Revision?"` instead of `"2nd Revision Needed"`, the dynamic mapper will automatically bind to the correct property without configuration changes.

---

## 7. Automation & Execution

### Local Development

```bash
# 1. Create and activate Python virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate  # Linux / macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Validate credentials using live smoke tests
python -m tests.smoke_gemini
python -m tests.smoke_drive
python -m tests.smoke_notion

# 4. Run automated test suite
pytest tests/ -q

# 5. Run the orchestration pipeline locally (dry run)
python -c "from src.orchestrate import run_orchestration; run_orchestration(dry_run=True)"

# 6. Launch the Streamlit Observability Dashboard
streamlit run dashboard/app.py
```

---

### GitHub Actions Scheduled Automation

The pipeline runs automatically via [.github/workflows/process-transcripts.yml](file:///c:/SynapseSync/.github/workflows/process-transcripts.yml):

* **Cron Trigger**: Scheduled daily at `17:30 UTC` (`cron: "30 17 * * *"`).
* **Manual Trigger**: Can be dispatched on demand via GitHub's Web UI using the `Run workflow` button (`workflow_dispatch`).
* **Concurrency Control**: Enforces `group: process-transcripts` with `cancel-in-progress: false` to ensure two runs never execute simultaneously or race to mutate Notion.
* **Automated Git Persistence**: If files are processed, GitHub Actions stages `manifest.json`, checks if changes exist, and commits the updated state back to the repository using `github-actions[bot]`.

---

## 8. Observability & Review Dashboard

SynapseSync includes an interactive engineering console built with **Streamlit** (`dashboard/app.py`):

* **Pipeline Topology**: An SVG-animated visualization of the 4 architectural layers (`Claude/Drive` -> `Engine` -> `Guardrails` -> `Notion`), interactive hover tooltips explaining engineering mechanics, and real-time operational status.
* **Equalized Metric Cards**: Real-time counts of total processed operations, successful writes, and flagged review items.
* **Review Queue View**: A dedicated console to inspect operations flagged by guardrails. Review cards display the halted problem name, domain badge, collision rationale (e.g. duplicate First Solve or orphan Revision), and technical metadata.
* **Theme**: Styled with a luxury editorial aesthetic (*Tactile Paper Elevation*, ivory cards `#FFFFFF`, antique bronze micro-borders `#DFD3BC`, and *Playfair Display* typography).
