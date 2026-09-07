import streamlit as st
from dashboard.views.pipeline import fetch_overview

def render():
    st.markdown("<h3 class='editorial-header'>Review Queue</h3>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:var(--text-secondary); font-size:0.95rem; margin-bottom:1.75rem; line-height:1.55;'>"
        "Items flagged by SynapseSync guardrails for manual inspection. "
        "These operations were safely halted before mutating Notion."
        "</p>", 
        unsafe_allow_html=True
    )
    
    overview = fetch_overview()
    manifest = overview.get("manifest", {})
    review_items = manifest.get("review_items", [])
    
    if not review_items:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">✓</div>
            <h3 style="color:var(--text-primary); font-family:var(--font-serif); margin-bottom:0.5rem; font-weight:600;">Queue Empty</h3>
            <p style="color:var(--text-muted);">No items currently require manual review.<br>The guardrails are clear and the pipeline is operating nominally.</p>
        </div>
        """, unsafe_allow_html=True)
        return
        
    # Summary metric row for the review queue
    col1, col2, col3 = st.columns(3)
    total_flagged = len(review_items)
    dsa_count = sum(1 for item in review_items if item.get("domain") == "DSA")
    sql_count = sum(1 for item in review_items if item.get("domain") == "SQL")
    
    with col1:
        st.metric("Total Flagged Items", total_flagged)
    with col2:
        st.metric("DSA Collisions", dsa_count)
    with col3:
        st.metric("SQL Collisions", sql_count)
        
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
        
    for item in review_items:
        domain = item.get("domain", "Unknown")
        segment_type = item.get("segment_type", "Unknown")
        problem_title = item.get("problem_title", "Unknown Problem")
        reason = item.get("reason", "Flagged for manual review by guardrails")
        
        file_id = item.get("file_id", "Unknown")
        short_file_id = file_id[:8] + "..." if len(file_id) > 8 else file_id
        segment_idx = item.get("segment_index", 1)
        
        title_display = problem_title if problem_title and problem_title != "Unknown Problem" else "Status: Review Required"
        
        st.markdown(f"""
        <div class="review-card">
            <div class="review-card-header">
                <h4 class="review-card-title">{title_display}</h4>
                <div>
                    <span class="badge badge-domain">{domain}</span>
                    <span class="badge badge-type">{segment_type}</span>
                </div>
            </div>
            <p class="review-card-reason"><strong>Halted Operation:</strong> {reason}</p>
            <div class="review-card-meta">
                <span>Ref: <code style="font-family:var(--font-mono); color:var(--text-secondary);">{short_file_id}</code></span>
                <span>Segment: <code style="font-family:var(--font-mono); color:var(--text-secondary);">{segment_idx}</code></span>
                <span>Domain: <code style="font-family:var(--font-mono); color:var(--text-secondary);">{domain}</code></span>
            </div>
        </div>
        """, unsafe_allow_html=True)
