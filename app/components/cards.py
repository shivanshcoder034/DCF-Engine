"""UI Card components for placeholders, status notices, and architectural overviews."""

from typing import List, Optional
import streamlit as st


def render_placeholder_card(
    title: str,
    phase: str,
    target_module: str,
    description: str,
    planned_capabilities: List[str],
    prerequisites: Optional[List[str]] = None,
) -> None:
    """Render a structured placeholder card for upcoming development phases.

    Avoids fake interactive elements while clearly establishing the planned architectural scope.
    """
    st.subheader(title)

    st.info(
        f"**Development Status:** This section is scheduled for implementation in **{phase}**.\n\n"
        f"**Underlying Architecture Module:** `{target_module}`"
    )

    st.markdown("### Planned Scope & Capabilities")
    st.markdown(description)

    for item in planned_capabilities:
        st.markdown(f"- {item}")

    if prerequisites:
        st.markdown("---")
        st.markdown("### Prerequisites")
        for prereq in prerequisites:
            st.markdown(f"- ⏳ {prereq}")
