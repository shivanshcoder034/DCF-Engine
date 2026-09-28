"""UI badge and notification components for application status."""

import streamlit as st


def render_phase_badge(phase_text: str = "Phase 1 Foundation", status: str = "Active") -> None:
    """Render a clean, professional status badge in Streamlit."""
    badge_html = f"""
    <div style="
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background-color: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-radius: 6px;
        padding: 4px 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 0.82rem;
        font-weight: 600;
        color: #1E40AF;
        margin-bottom: 12px;
    ">
        <span style="
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #2563EB;
        "></span>
        <span>{phase_text}</span>
        <span style="color: #64748B; font-weight: 400;">|</span>
        <span style="color: #15803D; font-weight: 500;">{status}</span>
    </div>
    """
    st.markdown(badge_html, unsafe_allow_html=True)
