import streamlit as st
import os
import json
from datetime import datetime
import streamlit.components.v1 as components

from dashboard import loader

@st.cache_data(ttl=60)
def fetch_overview():
    """
    Fetches the pipeline overview from the manifest.
    Uses caching to prevent constant disk reads.
    Does not hit Notion API to keep the dashboard snappy and avoid rate limits.
    """
    manifest_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
        "manifest.json"
    )
    return loader.get_pipeline_overview(manifest_path=manifest_path, include_notion_counts=False)

def format_date(iso_str):
    if not iso_str:
        return "Unknown"
    try:
        # Try to parse standard ISO format
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except ValueError:
        return iso_str

def render_pipeline_svg(status):
    """
    Renders the custom 4-layer SVG pipeline visualization.
    Implements tactile paper elevation with metallic bronze/antique gold micro-borders,
    golden particle animations, and clean technical typography.
    """
    is_warning = status != "operational"
    guardrail_stroke = "#B45309" if is_warning else "#15803D"
    guardrail_icon = "!" if is_warning else "✓"
    guardrail_fill = "rgba(180, 83, 9, 0.04)" if is_warning else "rgba(21, 128, 61, 0.04)"

    svg = f"""<!DOCTYPE html>
<html>
<head>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;1,600&family=Plus+Jakarta+Sans:wght@500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');
    
    body {{ 
        margin: 0; 
        background-color: #FAF8F5; 
        overflow: hidden; 
        display: flex; 
        justify-content: center; 
        align-items: flex-start; 
    }}
    .pipeline-container {{ display: flex; justify-content: center; width: 100%; }}
    .tooltip-group .svg-tooltip {{ opacity: 0; pointer-events: none; transition: opacity 0.25s ease; }}
    .tooltip-group:hover .svg-tooltip {{ opacity: 1; }}
    
    .tt-bg {{ 
        fill: #FFFFFF; 
        stroke: #C2A674; 
        stroke-width: 1.2; 
        rx: 6; 
        filter: drop-shadow(0 4px 14px rgba(50, 40, 26, 0.12)); 
    }}
    .tt-text {{ 
        fill: #2C2A29; 
        font-family: 'Plus Jakarta Sans', sans-serif; 
        font-size: 13px; 
        font-weight: 500; 
    }}
    .tt-text-accent {{ 
        fill: #9A7B3E; 
        font-family: 'Playfair Display', serif; 
        font-size: 14px; 
        font-weight: 600; 
    }}

    .interactive-node {{ cursor: pointer; transition: filter 0.25s ease; }}
    .interactive-node:hover {{ filter: drop-shadow(0 0 12px rgba(184, 151, 61, 0.35)); }}
    .data-particle {{ fill: #B8973D; filter: drop-shadow(0 0 5px rgba(184, 151, 61, 0.7)); }}
</style>
</head>
<body>
<div class="pipeline-container">
<svg width="100%" height="755" viewBox="0 0 880 755" xmlns="http://www.w3.org/2000/svg" style="max-width: 880px; overflow: visible;">
    <defs>
        <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L6,3 L0,6 z" fill="#B8A47E" />
        </marker>
        <marker id="arrow-gold" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L6,3 L0,6 z" fill="#B8973D" />
        </marker>
        <!-- Paths for particles -->
        <path id="p-path-1" d="M 540 80 L 540 127" fill="none" />
        <path id="p-path-2" d="M 540 180 L 540 232" fill="none" />
        <path id="p-path-3" d="M 430 324 L 467 324" fill="none" />
        <path id="p-path-4" d="M 595 324 L 632 324" fill="none" />
        <path id="p-path-5" d="M 540 385 L 540 437" fill="none" />
        <path id="p-path-6" d="M 540 605 L 540 657" fill="none" />
    </defs>

    <!-- ═══════════════ LAYER 1: INPUT ═══════════════ -->
    <text x="35" y="58" fill="#8C827A" font-family="'JetBrains Mono', monospace" font-size="11.5px" font-weight="600" letter-spacing="1.8px">LAYER 1 · INPUT</text>
    
    <rect x="460" y="35" width="160" height="45" rx="6" fill="#FFFFFF" stroke="#C2A674" stroke-width="1.25" filter="drop-shadow(0 1px 2px rgba(50,40,26,0.05)) drop-shadow(0 3px 8px rgba(50,40,26,0.04))" />
    <text x="540" y="58" fill="#1C1917" font-family="'Plus Jakarta Sans', sans-serif" font-size="14px" font-weight="700" letter-spacing="1px" text-anchor="middle" dominant-baseline="middle">CLAUDE</text>
    
    <line x1="540" y1="80" x2="540" y2="129" stroke="#B8A47E" stroke-width="2.2" fill="none" marker-end="url(#arrow)" />
    
    <rect x="435" y="135" width="210" height="45" rx="6" fill="#FFFFFF" stroke="#C2A674" stroke-width="1.25" filter="drop-shadow(0 1px 2px rgba(50,40,26,0.05)) drop-shadow(0 3px 8px rgba(50,40,26,0.04))" />
    <text x="540" y="158" fill="#1C1917" font-family="'Plus Jakarta Sans', sans-serif" font-size="14px" font-weight="700" letter-spacing="1px" text-anchor="middle" dominant-baseline="middle">GOOGLE DRIVE</text>

    <line x1="540" y1="180" x2="540" y2="234" stroke="#B8A47E" stroke-width="2.2" fill="none" marker-end="url(#arrow)" />

    <!-- ═══════════════ LAYER 2: SYNAPSESYNC (HERO) ═══════════════ -->
    <text x="35" y="270" fill="#8C827A" font-family="'JetBrains Mono', monospace" font-size="11.5px" font-weight="600" letter-spacing="1.8px">LAYER 2 · SYNAPSESYNC</text>
    
    <g class="tooltip-group interactive-node">
        <rect x="250" y="240" width="580" height="145" rx="10" fill="#FFFFFF" stroke="#B8973D" stroke-width="1.6" stroke-dasharray="6 4" filter="drop-shadow(0 2px 4px rgba(50,40,26,0.03)) drop-shadow(0 8px 24px rgba(50,40,26,0.05))" />
        <text x="540" y="270" fill="#8F7126" font-family="'Plus Jakarta Sans', sans-serif" font-size="14.5px" font-weight="700" letter-spacing="2px" text-anchor="middle" dominant-baseline="middle">PIPELINE ENGINE</text>
        <g class="svg-tooltip">
            <rect x="410" y="162" width="260" height="68" class="tt-bg" />
            <text x="426" y="184" class="tt-text"><tspan class="tt-text-accent">Idempotent Execution</tspan></text>
            <text x="426" y="202" class="tt-text">Uses SHA-256 content hashing</text>
            <text x="426" y="218" class="tt-text">to avoid redundant processing.</text>
        </g>
    </g>
    
    <!-- Internal Engine Nodes: Tactile Raised Ivory Cards -->
    <g class="tooltip-group interactive-node">
        <rect x="275" y="300" width="155" height="48" fill="#FAF8F5" stroke="#D5C4A1" stroke-width="1.2" rx="6" filter="drop-shadow(0 1px 3px rgba(50,40,26,0.04)) drop-shadow(0 3px 8px rgba(50,40,26,0.03))" />
        <text x="352" y="324" fill="#1C1917" font-family="'Plus Jakarta Sans', sans-serif" font-size="12px" font-weight="600" text-anchor="middle" dominant-baseline="middle">CLASSIFY &amp; EXTRACT</text>
        <g class="svg-tooltip">
            <rect x="220" y="224" width="260" height="68" class="tt-bg" />
            <text x="236" y="246" class="tt-text"><tspan class="tt-text-accent">Regex &amp; NLP Parsing</tspan></text>
            <text x="236" y="264" class="tt-text">Extracts metadata and problem blocks</text>
            <text x="236" y="280" class="tt-text">securely from plain text.</text>
        </g>
    </g>

    <line x1="430" y1="324" x2="469" y2="324" stroke="#B8973D" stroke-width="2.2" fill="none" marker-end="url(#arrow-gold)" />

    <g class="tooltip-group interactive-node">
        <rect x="475" y="300" width="120" height="48" fill="#FAF8F5" stroke="#D5C4A1" stroke-width="1.2" rx="6" filter="drop-shadow(0 1px 3px rgba(50,40,26,0.04)) drop-shadow(0 3px 8px rgba(50,40,26,0.03))" />
        <text x="535" y="324" fill="#1C1917" font-family="'Plus Jakarta Sans', sans-serif" font-size="12px" font-weight="600" text-anchor="middle" dominant-baseline="middle">VALIDATE</text>
        <g class="svg-tooltip">
            <rect x="410" y="224" width="260" height="68" class="tt-bg" />
            <text x="426" y="246" class="tt-text"><tspan class="tt-text-accent">Schema Enforcement</tspan></text>
            <text x="426" y="264" class="tt-text">Verifies extracted payload against</text>
            <text x="426" y="280" class="tt-text">Pydantic strict domain models.</text>
        </g>
    </g>

    <line x1="595" y1="324" x2="634" y2="324" stroke="#B8973D" stroke-width="2.2" fill="none" marker-end="url(#arrow-gold)" />

    <g class="tooltip-group interactive-node">
        <rect x="640" y="300" width="165" height="48" fill="#FAF8F5" stroke="#D5C4A1" stroke-width="1.2" rx="6" filter="drop-shadow(0 1px 3px rgba(50,40,26,0.04)) drop-shadow(0 3px 8px rgba(50,40,26,0.03))" />
        <text x="722" y="324" fill="#1C1917" font-family="'Plus Jakarta Sans', sans-serif" font-size="12px" font-weight="600" text-anchor="middle" dominant-baseline="middle">AGENT DECISION</text>
        <g class="svg-tooltip">
            <rect x="580" y="224" width="260" height="68" class="tt-bg" />
            <text x="596" y="246" class="tt-text"><tspan class="tt-text-accent">LLM Fallback &amp; Resolution</tspan></text>
            <text x="596" y="264" class="tt-text">Routes ambiguous cases to Gemini</text>
            <text x="596" y="280" class="tt-text">for autonomous classification.</text>
        </g>
    </g>

    <line x1="540" y1="385" x2="540" y2="439" stroke="#B8A47E" stroke-width="2.2" fill="none" marker-end="url(#arrow)" />

    <!-- ═══════════════ LAYER 3: SAFETY / GUARDRAILS ═══════════════ -->
    <text x="35" y="478" fill="#8C827A" font-family="'JetBrains Mono', monospace" font-size="11.5px" font-weight="600" letter-spacing="1.8px">LAYER 3 · SAFETY</text>

    <g class="tooltip-group interactive-node">
        <rect x="280" y="445" width="520" height="160" rx="8" stroke="{guardrail_stroke}" stroke-width="1.6" fill="{guardrail_fill}" filter="drop-shadow(0 2px 4px rgba(50,40,26,0.03)) drop-shadow(0 6px 18px rgba(50,40,26,0.04))" />
        <text x="540" y="478" fill="{guardrail_stroke}" font-family="'Plus Jakarta Sans', sans-serif" font-size="14.5px" font-weight="700" letter-spacing="1px" text-anchor="middle" dominant-baseline="middle">GUARDRAILS {guardrail_icon}</text>
        
        <!-- Guardrail Sub-checks -->
        <rect x="323" y="502" width="95" height="38" fill="#FFFFFF" stroke="#D5C4A1" stroke-width="1.2" rx="6" filter="drop-shadow(0 1px 3px rgba(50,40,26,0.04))" />
        <text x="370" y="523" fill="#2C2A29" font-family="'Plus Jakarta Sans', sans-serif" font-size="12px" font-weight="600" text-anchor="middle" dominant-baseline="middle">Contract</text>
        
        <rect x="436" y="502" width="85" height="38" fill="#FFFFFF" stroke="#D5C4A1" stroke-width="1.2" rx="6" filter="drop-shadow(0 1px 3px rgba(50,40,26,0.04))" />
        <text x="478" y="523" fill="#2C2A29" font-family="'Plus Jakarta Sans', sans-serif" font-size="12px" font-weight="600" text-anchor="middle" dominant-baseline="middle">Match</text>
        
        <rect x="539" y="502" width="95" height="38" fill="#FFFFFF" stroke="#D5C4A1" stroke-width="1.2" rx="6" filter="drop-shadow(0 1px 3px rgba(50,40,26,0.04))" />
        <text x="586" y="523" fill="#2C2A29" font-family="'Plus Jakarta Sans', sans-serif" font-size="12px" font-weight="600" text-anchor="middle" dominant-baseline="middle">Collision</text>
        
        <rect x="652" y="502" width="105" height="38" fill="#FFFFFF" stroke="#D5C4A1" stroke-width="1.2" rx="6" filter="drop-shadow(0 1px 3px rgba(50,40,26,0.04))" />
        <text x="704" y="523" fill="#2C2A29" font-family="'Plus Jakarta Sans', sans-serif" font-size="12px" font-weight="600" text-anchor="middle" dominant-baseline="middle">Safe Write</text>
        
        <text x="540" y="575" fill="{guardrail_stroke}" font-family="'Plus Jakarta Sans', sans-serif" font-size="12px" font-weight="500" text-anchor="middle">Halts ambiguous operations before mutation.</text>
        
        <g class="svg-tooltip">
            <rect x="410" y="368" width="260" height="68" class="tt-bg" />
            <text x="426" y="390" class="tt-text"><tspan class="tt-text-accent">Mutation Protection</tspan></text>
            <text x="426" y="408" class="tt-text">Ensures 100% confidence before</text>
            <text x="426" y="424" class="tt-text">dispatching write requests.</text>
        </g>
    </g>

    <line x1="540" y1="605" x2="540" y2="659" stroke="#B8A47E" stroke-width="2.2" fill="none" marker-end="url(#arrow)" />

    <!-- ═══════════════ LAYER 4: DESTINATION ═══════════════ -->
    <text x="35" y="686" fill="#8C827A" font-family="'JetBrains Mono', monospace" font-size="11.5px" font-weight="600" letter-spacing="1.8px">LAYER 4 · DESTINATION</text>

    <rect x="435" y="665" width="210" height="52" rx="6" fill="#FFFFFF" stroke="#C2A674" stroke-width="1.25" filter="drop-shadow(0 1px 2px rgba(50,40,26,0.05)) drop-shadow(0 3px 8px rgba(50,40,26,0.04))" />
    <text x="540" y="686" fill="#1C1917" font-family="'Plus Jakarta Sans', sans-serif" font-size="14px" font-weight="700" letter-spacing="1px" text-anchor="middle" dominant-baseline="middle">NOTION</text>
    <text x="540" y="704" fill="#8C827A" font-family="'JetBrains Mono', monospace" font-size="11px" text-anchor="middle">DSA / SQL</text>

    <!-- Animated Golden Particles -->
    <circle r="5" class="data-particle">
        <animateMotion dur="2s" repeatCount="indefinite" keyPoints="0;1" keyTimes="0;1"><mpath href="#p-path-1"/></animateMotion>
        <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.9;1" dur="2s" repeatCount="indefinite" />
    </circle>
    <circle r="5" class="data-particle">
        <animateMotion dur="3s" repeatCount="indefinite" keyPoints="0;1" keyTimes="0;1" begin="0.5s"><mpath href="#p-path-2"/></animateMotion>
        <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.9;1" dur="3s" repeatCount="indefinite" begin="0.5s" />
    </circle>
    <circle r="5" class="data-particle">
        <animateMotion dur="1.5s" repeatCount="indefinite" keyPoints="0;1" keyTimes="0;1" begin="1s"><mpath href="#p-path-3"/></animateMotion>
        <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.9;1" dur="1.5s" repeatCount="indefinite" begin="1s" />
    </circle>
    <circle r="5" class="data-particle">
        <animateMotion dur="1.5s" repeatCount="indefinite" keyPoints="0;1" keyTimes="0;1" begin="1.5s"><mpath href="#p-path-4"/></animateMotion>
        <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.9;1" dur="1.5s" repeatCount="indefinite" begin="1.5s" />
    </circle>
    <circle r="5" class="data-particle">
        <animateMotion dur="2s" repeatCount="indefinite" keyPoints="0;1" keyTimes="0;1" begin="2s"><mpath href="#p-path-5"/></animateMotion>
        <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.9;1" dur="2s" repeatCount="indefinite" begin="2s" />
    </circle>
    <!-- Condition particle: green if healthy, amber if warning -->
    <circle r="5" style="fill: {guardrail_stroke}; filter: drop-shadow(0 0 6px {guardrail_stroke});">
        <animateMotion dur="3s" repeatCount="indefinite" keyPoints="0;1" keyTimes="0;1" begin="2.5s"><mpath href="#p-path-6"/></animateMotion>
        <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.9;1" dur="3s" repeatCount="indefinite" begin="2.5s" />
    </circle>

</svg>
</div>
</body>
</html>"""
    components.html(svg, height=780, scrolling=False)

def render():
    st.markdown("<h3 class='editorial-header'>Pipeline Topology</h3>", unsafe_allow_html=True)
    
    # Fetch Data
    overview = fetch_overview()
    status = overview.get("status", "operational")
    is_operational = status == "operational"
    
    # Status Banner
    status_class = "status-operational" if is_operational else "status-warning"
    status_text = "SYSTEM OPERATIONAL" if is_operational else "ATTENTION NEEDED: ITEMS IN REVIEW QUEUE"
    
    st.markdown(f"""
    <div class="system-status">
        <div class="status-indicator {status_class}"></div>
        <strong>{status_text}</strong>
        <span style="margin-left:auto; color:var(--text-muted);">
            Last Synced: {format_date(overview.get("last_synced_at"))}
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    # Central Visualization
    render_pipeline_svg(status)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Metrics: Equalized tactile cards with matching heights
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Total Operations",
            value=overview.get("total_manifest_processed", 0)
        )
        
    with col2:
        st.metric(
            label="Successful Syncs",
            value=overview.get("success_count", 0)
        )
        
    with col3:
        needs_review = overview.get("needs_review_count", 0)
        st.metric(
            label="Review Queue",
            value=needs_review,
            delta=f"{needs_review} items flagged by guardrails" if needs_review > 0 else "All clear",
            delta_color="inverse" if needs_review > 0 else "normal"
        )
