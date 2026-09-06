# SynapseSync

SynapseSync is an autonomous agentic pipeline designed to bridge the workflow between practicing Data Structures & Algorithms (DSA) or SQL problems with **Claude.ai** (acting as a Socratic mentor) and tracking progress in structured **Notion** workspaces. When solving problems, Claude generates a standardized `Notion Notes` summary block at the end of the session, and the conversation transcript is saved to Google Drive. SynapseSync automatically detects, ingests, normalizes, extracts (with Gemini LLM fallback), validates, and routes these problem entries into their appropriate Notion databases—differentiating first solves from revisions, discovering topic databases dynamically, enforcing strict schema contracts, and recording synchronization status idempotently.

---

## 1. Architecture Flow

The end-to-end automation workflow functions as follows:

```text
+-------------------------------------------------------------------------------+
|                                USER WORKFLOW                                  |
|  User solves DSA/SQL problem with Claude.ai (acting as Socratic mentor)       |
|  Claude produces standardized "<Problem> — Notion Notes" summary block        |
|  User exports conversation (.md) into synced Downloads / Google Drive folder   |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                       GOOGLE DRIVE STORAGE & TRANSPORT                        |
|  Google Drive folder serves as decoupled file transport layer                 |
|  Stores: "<ChatTitle>-<YYYY-MM-DD>.md" exports                                |
+---------------------------------------+---------------------------------------+
                                        |
                   Daily Cron Schedule (17:30 UTC)
                   or Manual Workflow Dispatch
                                        v
+-------------------------------------------------------------------------------+
|                    GITHUB ACTIONS RUNNER (Ubuntu Latest)                      |
|                                                                               |
|  1. INGESTION & FILTERING (src/drive/ingestion.py, src/classifier.py)        |
|     - Pre-filter: Check filename pattern "<Title>-<YYYY-MM-DD>.md"           |
|     - Compute SHA-256 content hash & check manifest.json                      |
|     - Verify genuine exporter header: "_Created: YYYY-MM-DDTHH:MM:SSZ_"       |
|     - Check domain signature: "— Notion Notes" block requirement              |
|                                                                               |
|  2. EXTRACTION & VALIDATION (src/extraction/)                                 |
|     - Cleaner: Strip export noise and UI placeholders                         |
|     - Splitter: Partition transcripts into problem segments & extract dates   |
|     - Parser: Fast regex parsing of standardized Notion Notes key-values      |
|     - Fallback: Gemini 1.5/3.6 Flash fallback for malformed/missing blocks    |
|     - Solved-Verification: Reject unsolved/abandoned attempts                 |
|     - Contract Validator: Enforce strict schema, types, & allowed options     |
|                                                                               |
|  3. AGENT DECISION LOOP (src/agent/core.py)                                   |
|     - Domain Routing:                                                         |
|         * SQL -> Single Tracker DB (NOTION_SQL_DB_ID)                         |
|         * DSA -> Live Dynamic Topic DB Discovery (NOTION_DSA_PARENT_PAGE_ID)  |
|     - Search & Conflict Guardrails (src/notion_tools/search.py):              |
|         * Bidirectional normalized fuzzy title search against live entries    |
|         * First Solve: Entry already exists? -> Flag "needs_review"           |
|         * Revision: No matching entry found? -> Flag "needs_review"           |
|                                                                               |
|  4. NOTION MUTATION ENGINE (src/notion_tools/mutations.py)                    |
|     - Resolves database_id -> data_source_id (Notion API 2025-09-03)          |
|     - First Solve: client.pages.create() with all fields                      |
|     - Revision: client.pages.update() with ONLY [Revision Date,               |
|       2nd Revision Needed, Notes]                                             |
|                                                                               |
|  5. STATE PERSISTENCE (src/orchestrate.py -> manifest.json)                   |
|     - Commit & push updated manifest.json to GitHub repository                |
+-------------------------------------------------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                              NOTION WORKSPACE                                 |
|   +------------------------------------+  +--------------------------------+  |
|   |          DSA Topic DBs             |  |        SQL Tracker DB          |  |
|   |  - Arrays                          |  |  Single database tracking      |  |
|   |  - Binary Trees                    |  |  all SQL problems, queries,    |  |
|   |  - LinkedList                      |  |  buckets, and revisions        |  |
|   |  - Sliding Window & Two Pointer... |  |                                |  |
|   +------------------------------------+  +--------------------------------+  |
+-------------------------------------------------------------------------------+
```

---

## 2. Repository & Folder Structure

The repository is structured into modular layers separation of concerns:

```text
SynapseSync/
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Continuous integration workflow running pytest on pushes/PRs
│       └── process-transcripts.yml    # Daily cron workflow executing ingestion and Notion sync
├── src/
│   ├── classifier.py                  # Validates export filenames, authenticates Claude signatures, & classifies domain
│   ├── orchestrate.py                 # Pipeline entrypoint managing batch runs, manifest states, & git tracking
│   ├── agent/
│   │   ├── __init__.py                # Package export for the agentic core
│   │   └── core.py                    # Decision engine coordinating discovery, searching, validation, & mutations
│   ├── drive/
│   │   ├── __init__.py                # Package export for Google Drive services
│   │   └── ingestion.py               # Drive API client, media downloader, SHA-256 hashing, & file fetching
│   ├── extraction/
│   │   ├── __init__.py                # Package export for transcript extraction pipeline
│   │   ├── cleaner.py                 # Strips export UI artifacts, disclaimer footers, and noise
│   │   ├── contracts.py               # Field contracts, required keys, type definitions, and topic aliases
│   │   ├── extractor.py               # 7-step extraction orchestrator combining parser, fallback, and validation
│   │   ├── fallback.py                # Gemini LLM fallback handling malformed blocks or conversational extractions
│   │   ├── parser.py                  # Deterministic regex parser for standardized Notion Notes markdown blocks
│   │   ├── splitter.py                # Splits multi-problem transcripts into discrete problem segments
│   │   └── validator.py               # Validates parsed payloads against strict field contracts and allowed values
│   └── notion_tools/
│       ├── __init__.py                # Package export for Notion API helpers
│       ├── discovery.py               # Discovers DSA topic databases dynamically under parent page
│       ├── helpers.py                 # Notion client factory and database_id -> data_source_id resolver
│       ├── mutations.py               # Builds Notion API properties payloads and performs page creations/updates
│       ├── schema.py                  # Fetches and caches live property schemas from data sources
│       └── search.py                  # Fuzzy bidirectional title search and sequel-collision prevention
├── tests/
│   ├── fixtures/                      # Real and synthetic markdown transcript exports for testing
│   ├── scratch_db.py                  # Utility scratchpad for verifying title matching edge cases
│   ├── smoke_drive.py                 # Smoke test verifying Google Drive OAuth credentials & folder access
│   ├── smoke_gemini.py                # Smoke test verifying Gemini API connectivity
│   ├── smoke_notion.py                # Smoke test inspecting live Notion DSA parent page & SQL schema
│   ├── test_agent.py                  # Integration test validating end-to-end agent decision flow in dry-run
│   ├── test_classifier.py             # Unit tests for filename verification, genuine signatures, and domain classification
│   ├── test_extraction.py             # Unit tests for parsing, splitting, contracts, and Gemini fallback
│   ├── test_orchestration.py          # Integration tests for orchestration runs and manifest status transitions
│   └── test_search.py                 # Unit tests for title normalization, sequel collisions, and fuzzy search
├── .env.example                       # Template documenting required environment variables
├── manifest.json                      # State tracking database recording synced files, hashes, and review flags
├── pyproject.toml                     # Python package metadata and tool configurations
└── requirements.txt                   # Production and testing Python dependencies
```

---

## 3. Key Architectural Decisions

### Decoupled File Transport via Google Drive
GitHub Actions runs in an ephemeral cloud container with no access to the user's local disk. Rather than requiring open network tunnels, SSH daemons, or custom file upload servers, Google Drive acts as a secure, decoupled staging area. The user saves or syncs transcript files into a monitored Google Drive folder (e.g., via Google Drive for Desktop), which the pipeline queries over OAuth 2.0.

### Filename + Content Dual-Check for Transcript Authentication
A simple regex check on filename (`<Title>-<YYYY-MM-DD>.md`) was initially found to match unrelated markdown files that coincidentally had date suffixes (e.g., general chat logs, meeting summaries). The pipeline enforces a two-tier gate:
1. **Filename Regex**: Pre-filters candidate files (`r"^.*-\d{4}-\d{2}-\d{2}\.md$"`).
2. **Content Signature**: Inspects the first 5 lines of the file for the authentic Claude Exporter timestamp header: `^_Created:\s*\d{4}-\d{2}-\d{2}T.*Z_$`.
3. **Notion Notes Signature**: Confirms that a `[-—–]\s*Notion\s*Notes` block actually exists before attempting domain classification.

### Dynamic Multi-Database Discovery for DSA vs. Single SQL Database
In the user's Notion workspace, SQL problems reside in a single flat database (`NOTION_SQL_DB_ID`). However, DSA problems are organized into separate topic databases (e.g., *Arrays*, *Binary Trees*, *LinkedList*, *Sliding Window and Two Pointer*) nested under a single parent page (`NOTION_DSA_PARENT_PAGE_ID`).
- Rather than hardcoding 15+ database IDs in `.env` (which breaks whenever a database is moved, recreated, or renamed), `discover_dsa_topics()` queries the parent page's block children live via the Notion API.
- It traverses both direct child databases (`child_database`) and databases nested inside child pages (`child_page`), normalizing titles to match curriculum topics automatically.

### Notion API Version `2025-09-03` (`database_id` vs. `data_source_id`)
In Notion's `2025-09-03` API release, Notion decoupled database containers from their underlying data representations to support views and multi-source structures. Under this architecture:
- A `database_id` represents the visual container.
- Querying schemas (`data_sources.retrieve`), filtering items (`data_sources.query`), and creating child pages (`pages.create` with `parent: {"type": "data_source_id", "data_source_id": ...}`) **strictly require** the `data_source_id`.
- The helper `resolve_data_source_id()` retrieves the database container and resolves `db["data_sources"][0]["id"]` for all subsequent operations.

### Pass-Through "Bucket" vs. Strict Validation for "Difficulty" / "Revision Needed"
- **Bucket Values**: The curriculum has dynamic, evolving bucket names (e.g., *"1. Two Pointer Fundamentals"*, *"4. Path Finding & Tree Views"*). These are treated as pass-through rich-text / select values, trusting the user's curriculum definitions without code alterations.
- **Difficulty & Revision Needed**: These map to fixed Notion select/status properties (`Low`, `Mid`, `High`, `Easy`, `Medium`, `Hard`). These are strictly validated against live schema options in Notion (`validate_strict_field()`). Any hallucinated or mismatched option immediately fails before corrupting Notion metadata.

### Bidirectional Fuzzy Matching & The Sequel-Collision Guard
Exact string matching fails because problem titles differ across platforms (e.g., Claude writes *"Parts Assembly — Unfinished Parts"*, while Notion stores *"Unfinished Parts"*, or Claude notes *"Reverse Linked List (LC 206)"* while Notion has *"206. Reverse Linked List"*).
- `normalize_title()` strips LeetCode tags (`LC 206`), leading numbering (`206.`), punctuation, and multiple spaces.
- However, naive substring containment (`if shorter in longer`) introduced a critical flaw: **problem sequels** (e.g., *"Reverse Linked List"* matched *"Reverse Linked List II"*, or *"Word Break"* matched *"Word Break II"*).
- **The Sequel Guard**: If one normalized title is a substring of the other, the remainder is analyzed. If the remainder contains numbers (`2`) or sequel tokens (`i`, `ii`, `iii`, `iv`, `part`, `version`), the substring match is rejected.

### Hard-Enforced Revision Property Isolation (`append_revision`)
When logging a revision, the pipeline updates an existing page via `pages.update`. To guarantee that a revision cannot accidentally overwrite or blank out first-solve data (such as the canonical title, optimal solution, or gotchas), `build_properties_payload()` enforces a strict allowlist:
```python
REVISION_ALLOWED_PROPERTIES = {"Revision Date", "2nd Revision Needed", "Notes"}
```
Any other key in the payload is discarded when `is_revision=True`.

### Guardrails for Ambiguous Routing
The agent never guesses silently when data is ambiguous:
- **First Solve Collision**: If a First Solve is attempted but an existing problem entry is discovered, it is marked `needs_review` to prevent duplicate rows.
- **Missing Revision Target**: If a Revision is attempted but no matching problem exists in the database, it is marked `needs_review` (you cannot revise what was never logged).
- **Multi-Topic Revision Collision**: If a revision without an explicit topic matches problems in multiple DSA databases, it flags `needs_review`.

### Manifest States and Re-run Lifecycle
The `manifest.json` tracks each processed file by Google Drive `file_id` and SHA-256 `content_hash`:
- **`success`**: File processed and synced to Notion. On future runs with an identical content hash, it is skipped (`stats["skipped"]`). If the user edits the file in Drive, the hash changes, triggering a re-run.
- **`needs_review`**: File had an ambiguous routing situation or schema mismatch. The exact payloads and reasons are preserved in `manifest.json["processed"][file_id]["payloads"]`. It will not perform destructive partial writes.
- **`skipped_unclassified`**: File is an authentic export but lacks the Notion Notes block or domain signals.
- **`failed`**: Transient network or API errors. The file is **not** written to the manifest, allowing it to automatically retry on the subsequent scheduled run.

---

## 4. Bugs Found and Fixed During Development

Building this pipeline uncovered several real-world edge cases:

1. **Notion API `2025-09-03` Parent Shape Migration Bug**
   - *Symptom*: Creating pages in Notion failed with invalid parent errors despite passing a valid `database_id`.
   - *Root Cause*: Under API version `2025-09-03`, passing `{"parent": {"database_id": ...}}` is deprecated. Page creation requires the data source shape: `{"parent": {"type": "data_source_id", "data_source_id": resolved_id}}`.
   - *Fix*: Implemented `resolve_data_source_id()` to extract `data_sources[0]["id"]` from the database metadata and updated `create_problem_entry()` accordingly.

2. **Title-Matching Sequel Collision Bug (Duplicate SQL & LeetCode Entries)**
   - *Symptom*: A revision for *"Reverse Linked List"* matched an existing entry for *"Reverse Linked List II"*, and titles with common prefixes caused false matches.
   - *Root Cause*: Substring matching (`n1 in n2`) treated any title containing the base string as a match.
   - *Fix*: Created a tokenized remainder check in `is_fuzzy_match()`. If the remainder between the longer and shorter normalized title contains digits or sequel keywords (`ii`, `part`, `version`), the fuzzy match is rejected.

3. **Title Overwrite in `append_revision`**
   - *Symptom*: When appending revision notes to an existing problem, the payload builder included the `Problem` key, causing `pages.update` to replace the canonical title in Notion with whatever title variant Claude outputted.
   - *Root Cause*: `build_properties_payload()` mapped all contract fields present in the dictionary.
   - *Fix*: Hard-coded `REVISION_ALLOWED_PROPERTIES` to strictly permit only `Revision Date`, `2nd Revision Needed`, and `Notes` during revisions.

4. **False-Positive Classification on General Chat Exports**
   - *Symptom*: An unrelated conversation export about a product review was ingested and classified as SQL because it happened to contain the words "SELECT" and "FROM".
   - *Root Cause*: `classifier.py` checked regex keywords across the entire transcript text without verifying problem structure.
   - *Fix*: Added a strict requirement that transcripts must contain the signature `[-—–]\s*Notion\s*Notes` block before domain keyword matching is evaluated.

---

## 5. Setup & Configuration

### Prerequisites
1. **Google Cloud Console**:
   - Enable the Google Drive API.
   - Create an OAuth 2.0 Client ID (Desktop application).
   - Generate a Refresh Token with scope `https://www.googleapis.com/auth/drive.readonly`.
2. **Google Gemini API**:
   - Obtain an API key from Google AI Studio.
3. **Notion Integration**:
   - Create an internal integration token at [notion.so/my-integrations](https://www.notion.so/my-integrations).
   - Ensure the integration has read/write access and has been invited to your parent page and database.

### Environment Variables
Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Description |
| :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API key for fallback transcript extraction |
| `NOTION_TOKEN` | Internal Notion integration token (`secret_...`) |
| `NOTION_DSA_PARENT_PAGE_ID` | Notion Page ID containing child topic databases for DSA |
| `NOTION_SQL_DB_ID` | Notion Database ID for the SQL problem tracker |
| `GOOGLE_DRIVE_FOLDER_ID` | Google Drive folder ID where transcripts are uploaded |
| `GOOGLE_OAUTH_CLIENT_ID` | Google Cloud OAuth 2.0 Client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET`| Google Cloud OAuth 2.0 Client Secret |
| `GOOGLE_OAUTH_REFRESH_TOKEN`| Google OAuth 2.0 refresh token with Drive readonly scope |

### Notion Workspace Structure Expectations

```text
Notion Workspace
├── DSA Problem Tracker (Parent Page - NOTION_DSA_PARENT_PAGE_ID)
│   ├── Arrays (Child Database or Page containing Database)
│   ├── Binary Trees (Child Database)
│   ├── LinkedList (Child Database)
│   └── ... (Other DSA Topics)
└── SQL Problem Tracker (Database - NOTION_SQL_DB_ID)
```

#### Adapting to a Different Notion Structure
- **Flat DSA Database**: If all your DSA problems live in one database rather than per-topic databases, point `NOTION_DSA_PARENT_PAGE_ID` to that database ID and adjust `discover_dsa_topics()` in [discovery.py](file:///c:/SynapseSync/src/notion_tools/discovery.py) to return a map targeting that single data source ID.
- **Custom Property Names**: Property mappings are resolved dynamically via [mutations.py](file:///c:/SynapseSync/src/notion_tools/mutations.py). If your database uses "Pattern" instead of "Bucket", the mapper automatically detects property names containing the words "pattern" or "bucket".

---

## 6. Automation & Execution

### Running Locally

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate  # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify external connectivity with smoke tests
python -m tests.smoke_gemini
python -m tests.smoke_drive
python -m tests.smoke_notion

# 4. Run the test suite
pytest

# 5. Run the orchestration pipeline
python -m src.orchestrate
```

### GitHub Actions Scheduled Execution
The pipeline is automated via [.github/workflows/process-transcripts.yml](file:///c:/SynapseSync/.github/workflows/process-transcripts.yml):
- **Schedule**: Executes daily via cron at `17:30 UTC` (`30 17 * * *`).
- **Manual Trigger**: Can be dispatched on-demand via the GitHub Actions UI (`workflow_dispatch`).
- **Idempotence**: Files are tracked in `manifest.json`. If a run fails or encounters duplicates, the manifest flags them without creating duplicate Notion entries. If new entries are successfully synced, GitHub Actions commits and pushes the updated `manifest.json` back to the repository using `github-actions[bot]`.
