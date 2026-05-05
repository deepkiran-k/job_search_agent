"""
views/auth_view.py
Mandatory login / signup screen for JobOrbit AI.

Rendered by app.py BEFORE any other content when the user
is not authenticated (st.session_state.user_id is None).
"""
import streamlit as st

from utils.auth import authenticate_user, create_user


def render() -> None:
    """Render the centred auth card with Login / Sign Up tabs."""
    # ── Outer layout — centred narrow column ─────────────────────────────────
    _, col, _ = st.columns([1, 1.6, 1])

    with col:
        # ── Logo / wordmark ──────────────────────────────────────────────────
        st.markdown("""
        <div style="text-align:center;padding:2.5rem 0 1.5rem;">
          <div style="display:inline-flex;align-items:center;gap:10px;margin-bottom:0.5rem;">
            <div style="width:12px;height:12px;border-radius:50%;background:#16A34A;
                        box-shadow:0 0 14px rgba(22,197,94,0.6);flex-shrink:0;"></div>
            <span style="font-size:1.5rem;font-weight:800;color:#EAFAEF;
                         letter-spacing:-0.02em;">JobOrbit AI</span>
          </div>
          <div style="font-size:0.88rem;color:#8A9E92;margin-top:0.25rem;">
            Sign in to save your search & analysis history
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Auth card ────────────────────────────────────────────────────────
        st.markdown("""
        <div style="background:#121814;border:1px solid #26332A;border-radius:14px;
                    padding:2rem 2rem 1.5rem;">
        """, unsafe_allow_html=True)

        login_tab, signup_tab = st.tabs(["🔑 Log In", "✨ Sign Up"])

        # ── LOGIN ─────────────────────────────────────────────────────────────
        with login_tab:
            with st.form("login_form"):
                email    = st.text_input("Email", placeholder="you@example.com",
                                         key="login_email")
                password = st.text_input("Password", type="password",
                                         placeholder="••••••••", key="login_pw")
                submitted = st.form_submit_button(
                    "Log In →", type="primary", use_container_width=True,
                )

            if submitted:
                if not email.strip() or not password:
                    st.error("Please enter your email and password.")
                else:
                    user = authenticate_user(email, password)
                    if user:
                        st.session_state["user_id"]    = user["id"]
                        st.session_state["user_email"] = user["email"]
                        st.rerun()
                    else:
                        st.error("❌ Incorrect email or password.")

        # ── SIGN UP ───────────────────────────────────────────────────────────
        with signup_tab:
            with st.form("signup_form"):
                su_email    = st.text_input("Email", placeholder="you@example.com",
                                            key="su_email")
                su_pw       = st.text_input("Password", type="password",
                                            placeholder="At least 6 characters",
                                            key="su_pw")
                su_pw2      = st.text_input("Confirm Password", type="password",
                                            placeholder="Repeat password",
                                            key="su_pw2")
                su_submitted = st.form_submit_button(
                    "Create Account →", type="primary", use_container_width=True,
                )

            if su_submitted:
                if not su_email.strip():
                    st.error("Please enter your email address.")
                elif len(su_pw) < 6:
                    st.error("Password must be at least 6 characters.")
                elif su_pw != su_pw2:
                    st.error("Passwords do not match.")
                else:
                    user = create_user(su_email, su_pw)
                    if user:
                        st.session_state["user_id"]    = user["id"]
                        st.session_state["user_email"] = user["email"]
                        st.toast("🎉 Account created! Welcome to JobOrbit AI.")
                        st.rerun()
                    else:
                        st.error("⚠️ That email is already registered. Please log in instead.")

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Footer ────────────────────────────────────────────────────────────
        st.markdown("""
        <div style="text-align:center;font-size:0.7rem;color:#607267;margin-top:1.25rem;">
          Your data is stored locally and never shared.
        </div>
        """, unsafe_allow_html=True)
