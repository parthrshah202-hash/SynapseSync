"""
Main entry point for the SynapseSync Dashboard.
"""

import os
import streamlit as st

# Must be the first Streamlit command
st.set_page_config(
    page_title="SynapseSync Pipeline",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Set up environment path to find our modules correctly if run from project root
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dashboard.views import pipeline, review

def load_css():
    """Injects custom CSS for the engineering console aesthetic."""
    css_path = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def main():
    load_css()
    
    # Custom Sidebar Navigation
    with st.sidebar:
        st.markdown(
            "<div style='margin-bottom: 1.85rem;'>"
            "<div style='color: var(--text-primary); font-family: var(--font-serif); font-size: 1.65rem; font-weight: 700; letter-spacing: -0.01em; line-height: 1.15;'>SYNAPSESYNC</div>"
            "<div style='color: var(--border-bronze-dark); font-family: var(--font-mono); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.16em; font-weight: 600; margin-top: 0.35rem;'>OBSERVABILITY</div>"
            "</div>",
            unsafe_allow_html=True
        )
        
        # Dropdown list for navigation (default: Pipeline)
        page = st.selectbox(
            "Navigation",
            options=["Pipeline", "Review Needed"],
            index=0,
            label_visibility="collapsed"
        )
        
        st.markdown(
            "<div class='sidebar-footer-container'>"
            "<span style='color: var(--text-muted); font-family: var(--font-mono); font-size: 0.75rem; letter-spacing: 0.05em;'>v1.0.0</span>"
            "</div>",
            unsafe_allow_html=True
        )
    
    # Route to the appropriate view
    if page == "Pipeline":
        pipeline.render()
    elif page == "Review Needed":
        review.render()

if __name__ == "__main__":
    main()
