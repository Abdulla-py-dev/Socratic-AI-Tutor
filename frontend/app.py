import datetime
import hashlib
import html
import secrets
import textwrap

import streamlit as st


# =====================================================================
# 1. PAGE CONFIGURATION
# =====================================================================
st.set_page_config(
    page_title="Socratic AI Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_html(content: str) -> None:
    """Render HTML after removing indentation that Markdown treats as code."""
    st.markdown(textwrap.dedent(content).strip(), unsafe_allow_html=True)


def add_activity(icon: str, title: str) -> None:
    st.session_state.recent_activities.insert(
        0,
        {
            "icon": icon,
            "title": title,
            "time": datetime.datetime.now().strftime("%b %d, %I:%M %p"),
        },
    )
    st.session_state.recent_activities = st.session_state.recent_activities[:8]


def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"{salt.hex()}:{digest.hex()}"


def password_matches(stored_hash: str, password: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def set_signed_in_user(email: str, user: dict) -> None:
    st.session_state.authenticated = True
    st.session_state.user_email = email
    st.session_state.user_name = user.get("name", "Student")
    st.session_state.user_school = user.get("school", "")
    st.session_state.user_level = user.get("level", "Undergraduate")
    st.session_state.user_field = user.get("field", "")
    st.session_state.current_page = "Dashboard"


def get_mascot_svg() -> str:
    return """
    <svg width="210" height="170" viewBox="0 0 210 170" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Friendly AI learning mascot">
      <defs>
        <radialGradient id="mascotShadow" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#38BDF8" stop-opacity=".35"/><stop offset="1" stop-color="#071C38" stop-opacity="0"/></radialGradient>
        <linearGradient id="mascotBody" x1="45" y1="32" x2="160" y2="130" gradientUnits="userSpaceOnUse"><stop stop-color="#fff"/><stop offset=".58" stop-color="#E2E8F0"/><stop offset="1" stop-color="#94A3B8"/></linearGradient>
        <linearGradient id="mascotVisor" x1="58" y1="48" x2="150" y2="100" gradientUnits="userSpaceOnUse"><stop stop-color="#0F172A"/><stop offset="1" stop-color="#1E3A5F"/></linearGradient>
        <linearGradient id="mascotEye" x1="75" y1="65" x2="132" y2="84" gradientUnits="userSpaceOnUse"><stop stop-color="#7DD3FC"/><stop offset="1" stop-color="#0284C7"/></linearGradient>
      </defs>
      <ellipse cx="105" cy="154" rx="70" ry="12" fill="url(#mascotShadow)"/>
      <path d="M105 34V18" stroke="#CBD5E1" stroke-width="4" stroke-linecap="round"/><circle cx="105" cy="13" r="8" fill="#38BDF8"/><circle cx="105" cy="13" r="14" fill="#38BDF8" fill-opacity=".2"/>
      <rect x="36" y="60" width="12" height="24" rx="6" fill="#38BDF8"/><rect x="162" y="60" width="12" height="24" rx="6" fill="#38BDF8"/>
      <rect x="46" y="34" width="118" height="84" rx="34" fill="url(#mascotBody)"/><path d="M67 40Q105 35 143 40" stroke="white" stroke-width="3" stroke-linecap="round"/>
      <rect x="58" y="48" width="94" height="52" rx="18" fill="url(#mascotVisor)"/>
      <ellipse cx="84" cy="74" rx="10" ry="11" fill="url(#mascotEye)"/><circle cx="81" cy="70" r="3.5" fill="white"/><ellipse cx="126" cy="74" rx="10" ry="11" fill="url(#mascotEye)"/><circle cx="123" cy="70" r="3.5" fill="white"/>
      <path d="M99 85Q105 90 111 85" stroke="#38BDF8" stroke-width="2.5" stroke-linecap="round"/>
      <path d="M178 31L181 38L188 40L182 45L184 52L177 48L171 51L174 44L168 41L175 38Z" fill="#FBBF24"/><circle cx="29" cy="43" r="4" fill="#38BDF8"/><circle cx="27" cy="94" r="5" fill="#FB7185"/>
      <path d="M92 120H118L113 138H97L92 120Z" fill="#2563EB"/><circle cx="105" cy="129" r="2.5" fill="white"/>
    </svg>
    """


def get_donut_chart_svg(correct: int, incorrect: int) -> str:
    total = max(0, correct) + max(0, incorrect)
    circumference = 2 * 3.141592653589793 * 45
    correct_length = circumference * correct / total if total else 0
    incorrect_length = circumference * incorrect / total if total else 0
    percent = round(correct * 100 / total) if total else 0
    correct_dash = f'{correct_length:.2f} {circumference - correct_length:.2f}'
    incorrect_dash = f'{incorrect_length:.2f} {circumference - incorrect_length:.2f}'
    return f"""
    <svg width="150" height="150" viewBox="0 0 120 120" role="img" aria-label="Accuracy {percent} percent">
      <circle cx="60" cy="60" r="45" fill="none" stroke="#E2E8F0" stroke-width="14"/>
      <circle cx="60" cy="60" r="45" fill="none" stroke="#22C55E" stroke-width="14" stroke-dasharray="{correct_dash}" stroke-dashoffset="0" stroke-linecap="round" transform="rotate(-90 60 60)"/>
      <circle cx="60" cy="60" r="45" fill="none" stroke="#EF4444" stroke-width="14" stroke-dasharray="{incorrect_dash}" stroke-dashoffset="-{correct_length:.2f}" stroke-linecap="round" transform="rotate(-90 60 60)"/>
      <text x="60" y="58" text-anchor="middle" font-size="22" font-weight="800" fill="#0F172A">{percent}%</text>
      <text x="60" y="74" text-anchor="middle" font-size="9" font-weight="600" fill="#64748B" letter-spacing=".05em">ACCURACY</text>
    </svg>
    """


# =====================================================================
# 2. SESSION STATE: clean defaults, no sample activity/progress
# =====================================================================
_DEFAULTS = {
    "authenticated": False,
    "user_name": "",
    "user_email": "",
    "user_school": "",
    "user_level": "Undergraduate",
    "user_field": "",
    "users_db": {},
    "current_page": "Dashboard",
    "chat_messages": [],
    "uploaded_docs": [],
    "recent_activities": [],
    "correct_answers": 0,
    "incorrect_answers": 0,
    "notifications": [],
    "show_notifications": False,
}
for _key, _value in _DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _value.copy() if isinstance(_value, (dict, list)) else _value
if "signup_step" not in st.session_state:
    st.session_state.signup_step = 1


# =====================================================================
# 3. INTERNAL PAGE STATE
# Page changes use Streamlit widgets rather than URL links so the authenticated
# session is not discarded by a browser navigation.
# =====================================================================


# =====================================================================
# 4. GLOBAL THEME
# =====================================================================
if not st.session_state.authenticated:
    render_html("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
      * { font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif; }
      .stApp { background: #F8FAFD; }
      [data-testid="stSidebar"] { display: none !important; }
      [data-testid="stHeader"] { background: transparent; }
      .block-container { max-width: 500px !important; margin: 0 auto !important; padding: 2rem 1.25rem 2.5rem !important; }
      [data-testid="stTabs"] [role="tablist"] { justify-content: center; gap: 1rem; }
      [data-testid="stForm"] { background: #fff; border: 1px solid #E2E8F0; border-radius: 20px; padding: 24px; box-shadow: 0 10px 30px -5px rgba(15,23,42,.06); }
      [data-testid="stTextInput"] label, [data-testid="stSelectbox"] label { color: #334155; font-weight: 600; }
      [data-testid="stFormSubmitButton"] button { border-radius: 11px; min-height: 44px; font-weight: 700; }
      .auth-head { text-align: center; margin: 0 auto 1.3rem; }
      .auth-logo { display: inline-flex; align-items: center; justify-content: center; width: 58px; height: 58px; border-radius: 17px; background: linear-gradient(135deg,#071C38,#2563EB); color: #fff; font-size: 27px; box-shadow: 0 8px 20px rgba(7,28,56,.2); }
      .auth-title { color: #0F172A; font-size: 1.8rem; font-weight: 800; letter-spacing: -.03em; margin: .65rem 0 .15rem; }
      .auth-sub { color: #64748B; margin: 0; font-size: .93rem; }
      @media(max-width:640px) { .block-container { padding: 1.25rem .8rem 2rem !important; } [data-testid="stForm"] { padding: 18px; } }
    </style>
    """)
else:
    render_html("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
      * { font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif; box-sizing: border-box; }
      .stApp { background: #F8FAFD; color: #0F172A; }
      .block-container { padding-top: 4.25rem !important; padding-bottom: 2rem !important; padding-left: 2rem !important; padding-right: 2rem !important; max-width: 1440px !important; }
      section[data-testid="stSidebar"] { background: linear-gradient(180deg,#061933 0%,#082247 100%) !important; border-right: 1px solid rgba(255,255,255,.08) !important; }
      section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #CBD5E1; }
      .brand-box { display:flex; align-items:center; gap:12px; padding:8px 4px 20px; border-bottom:1px solid rgba(255,255,255,.1); margin-bottom:22px; }
      .brand-icon-wrapper { width:44px; height:44px; border-radius:13px; background:linear-gradient(135deg,#2563EB,#38BDF8); display:flex; align-items:center; justify-content:center; box-shadow:0 4px 14px rgba(37,99,235,.35); flex-shrink:0; }
      .brand-name { color:#fff; font-size:1.12rem; font-weight:800; letter-spacing:-.02em; line-height:1.15; }
      .brand-tag { color:#38BDF8; font-size:.68rem; font-weight:700; text-transform:uppercase; letter-spacing:.08em; }
      section[data-testid="stSidebar"] .stButton > button { width:100%; text-align:left; justify-content:flex-start; padding:.68rem 1rem; border-radius:10px; border:1px solid transparent; background:transparent; color:#CBD5E1; font-size:.94rem; font-weight:600; margin:2px 0; }
      section[data-testid="stSidebar"] .stButton > button:hover { background:rgba(255,255,255,.08); color:#fff; border-color:transparent; }
      section[data-testid="stSidebar"] .stButton > button[kind="primary"] { background:rgba(255,255,255,.15); color:#fff; border-left:4px solid #38BDF8; }
      section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover { background:rgba(255,255,255,.18); }
      header[data-testid="stHeader"] { background: transparent !important; }
      .header-text-block { display:flex; flex-direction:column; justify-content:center; }
      .greeting-main { font-size:1.85rem; font-weight:800; color:#0F172A; letter-spacing:-.03em; margin:0; line-height:1.2; }
      .greeting-sub { font-size:.95rem; color:#64748B; font-weight:500; margin:.35rem 0 0; line-height:1.3; }
      .top-nav-icons-bar { display:flex; align-items:center; justify-content:flex-end; gap:12px; min-height:48px; }
      .st-key-header_notifications, .st-key-header_profile { display:flex !important; align-items:center !important; justify-content:center !important; }
      .st-key-header_notifications button, .st-key-header_profile button {
        width: 44px !important;
        height: 44px !important;
        min-width: 44px !important;
        min-height: 44px !important;
        max-width: 44px !important;
        max-height: 44px !important;
        border-radius: 50% !important;
        padding: 0 !important;
        margin: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.15s ease !important;
      }
      .st-key-header_notifications button {
        position: relative !important;
        background: #FFFFFF !important;
        border: 1.5px solid #E2E8F0 !important;
        color: #475569 !important;
        box-shadow: 0 2px 6px rgba(15,23,42,0.05) !important;
      }
      .st-key-header_notifications button:hover {
        background: #F8FAFC !important;
        border-color: #CBD5E1 !important;
        color: #0F172A !important;
        transform: translateY(-1px);
      }
      .notif-has-badge .st-key-header_notifications button::after,
      .has-notif-dot button::after {
        content: '' !important;
        position: absolute !important;
        top: 7px !important;
        right: 8px !important;
        width: 8px !important;
        height: 8px !important;
        background-color: #EF4444 !important;
        border: 1.5px solid #FFFFFF !important;
        border-radius: 50% !important;
      }
      .st-key-header_profile button {
        background: #EFF6FF !important;
        border: 1.5px solid #DBEAFE !important;
        color: #2563EB !important;
        box-shadow: 0 2px 6px rgba(37,99,235,0.1) !important;
      }
      .st-key-header_profile button:hover {
        background: #DBEAFE !important;
        border-color: #BFDBFE !important;
        color: #1D4ED8 !important;
        transform: translateY(-1px);
      }
      .st-key-header_notifications button span[data-testid="stIconMaterial"],
      .st-key-header_profile button span[data-testid="stIconMaterial"] {
        font-size: 22px !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
      }
      .st-key-header_notifications button p,
      .st-key-header_profile button p {
        display: none !important;
        margin: 0 !important;
        padding: 0 !important;
      }
      .hero-banner-card { background:linear-gradient(135deg,#071C38 0%,#0F3569 55%,#184D93 100%); border-radius:20px; padding:26px 34px; color:#fff; display:flex; align-items:center; justify-content:space-between; gap:20px; box-shadow:0 10px 28px -6px rgba(7,28,56,.24); border:1px solid rgba(255,255,255,.12); margin:16px 0 20px; overflow:hidden; min-height:220px; }
      .hero-left { max-width:62%; }
      .hero-title { font-size:1.8rem; font-weight:800; letter-spacing:-.02em; margin:0 0 8px; color:#fff; }
      .hero-desc { font-size:.98rem; color:#D1DEEF; line-height:1.5; margin:0 0 18px; }
      .hero-btn { display:inline-block; background:#fff; color:#0F172A !important; font-size:.92rem; font-weight:700; padding:10px 20px; border-radius:11px; text-decoration:none !important; box-shadow:0 4px 14px rgba(0,0,0,.15); }
      .hero-right { display:flex; align-items:center; justify-content:center; flex-shrink:0; }
      .action-card-link { text-decoration:none !important; display:block; }
      .st-key-btn_start_learning button { background:#fff !important; color:#0F172A !important; border:0 !important; border-radius:11px !important; font-weight:700 !important; box-shadow:0 4px 14px rgba(0,0,0,.15) !important; }
      .st-key-btn_upload_card button, .st-key-btn_tutor_card button, .st-key-btn_progress_card button { height:84px; white-space:pre-line; text-align:left; justify-content:flex-start; border-radius:16px; border:1px solid #E8EEF5; background:#fff; color:#0F172A; font-weight:700; box-shadow:0 4px 14px rgba(15,23,42,.03); }
      .st-key-btn_upload_card button:hover, .st-key-btn_tutor_card button:hover, .st-key-btn_progress_card button:hover { border-color:#CBD5E1; background:#F8FAFC; color:#0F172A; }
      /* header button styles merged above */
      .action-card-box { background:#fff; border-radius:16px; border:1px solid #E8EEF5; padding:17px 18px; display:flex; align-items:center; gap:14px; box-shadow:0 4px 14px rgba(15,23,42,.03); min-height:84px; }
      .action-icon-badge { width:48px; height:48px; border-radius:12px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
      .action-icon-badge.pdf { background:#FEE2E2; } .action-icon-badge.tutor { background:#DBEAFE; } .action-icon-badge.progress { background:#DCFCE7; }
      .action-title { font-size:1.02rem; font-weight:700; color:#0F172A; margin:0; }
      .action-sub { font-size:.84rem; color:#64748B; font-weight:500; margin:3px 0 0; }
      .dashboard-panel-box { background:#fff; border-radius:20px; border:1px solid #E8EEF5; padding:22px 24px; box-shadow:0 4px 20px -2px rgba(15,23,42,.04); margin:18px 0 12px; min-height:250px; }
      .dashboard-panel-header { font-size:1.2rem; font-weight:800; color:#0F172A; margin:0 0 18px; letter-spacing:-.01em; }
      .progress-box-content { display:flex; align-items:center; gap:28px; min-height:150px; }
      .progress-chart-wrapper { flex-shrink:0; display:flex; align-items:center; justify-content:center; }
      .progress-legend-wrapper { display:flex; flex-direction:column; gap:14px; }
      .legend-item { display:flex; align-items:center; gap:10px; font-size:.93rem; font-weight:600; color:#334155; }
      .legend-dot { width:11px; height:11px; border-radius:50%; display:inline-block; }
      .legend-dot.green { background:#22C55E; } .legend-dot.red { background:#EF4444; }
      .activity-list-wrapper { display:flex; flex-direction:column; gap:9px; }
      .activity-item-row { display:flex; align-items:center; gap:12px; padding:10px 12px; background:#F8FAFC; border-radius:12px; border:1px solid #EEF2F6; }
      .activity-item-icon { width:40px; height:40px; border-radius:10px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
      .activity-item-details { flex:1; min-width:0; }
      .activity-item-title { font-size:.92rem; font-weight:700; color:#1E293B; margin:0; overflow-wrap:anywhere; }
      .activity-item-time { font-size:.78rem; color:#94A3B8; font-weight:500; margin:3px 0 0; }
      .activity-empty-state { text-align:center; padding:28px 14px; color:#64748B; background:#F8FAFC; border-radius:12px; }
      .empty-title { font-size:1rem; font-weight:700; margin:0 0 5px; color:#475569; }
      .empty-sub { font-size:.85rem; margin:0; }
      [data-testid="stForm"] { background:#fff; border:1px solid #E8EEF5; border-radius:16px; padding:18px; }
      @media(max-width:800px) { .block-container { padding-left:1rem !important; padding-right:1rem !important; } .hero-banner-card { padding:22px; } .hero-left { max-width:100%; } .hero-right svg { width:145px; height:auto; } }
      @media(max-width:560px) { .hero-right { display:none; } .progress-box-content { flex-wrap:wrap; gap:12px; } .top-nav-icons-bar { gap:8px; } }
    </style>
    """)


# =====================================================================
# 5. LOGIN AND TWO-STEP REGISTRATION
# =====================================================================
if not st.session_state.authenticated:
    render_html("""
    <div class="auth-head">
      <div class="auth-logo">🎓</div>
      <h1 class="auth-title">Socratic AI Tutor</h1>
      <p class="auth-sub">Your AI learning companion for smarter study</p>
    </div>
    """)

    login_tab, signup_tab = st.tabs(["Sign in", "Create account"])
    with login_tab:
        with st.form("login_form"):
            login_email = st.text_input("Email address", placeholder="name@example.com")
            login_password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit_login = st.form_submit_button("Sign in to dashboard", use_container_width=True)
        if submit_login:
            clean_email = login_email.strip().lower()
            user = st.session_state.users_db.get(clean_email)
            if user and password_matches(user.get("password_hash", ""), login_password):
                set_signed_in_user(clean_email, user)
                st.rerun()
            else:
                st.error("Email or password is incorrect. Create an account first if you are new.")

    with signup_tab:
        step = st.session_state.signup_step
        st.progress(0.5 if step == 1 else 1.0, text=f"Step {step} of 2 · " + ("Academic details" if step == 1 else "Security"))
        if step == 1:
            st.markdown("### Academic details")
            with st.form("signup_academic_form"):
                st.text_input("Full name", placeholder="Enter your name", key="signup_name")
                st.text_input("Email address", placeholder="name@example.com", key="signup_email")
                st.text_input("Academic institution", placeholder="Enter your academy or institution", key="signup_school")
                st.selectbox("Academic level", ["High School", "Undergraduate", "Post-Graduate", "Professional Learner"], key="signup_level")
                st.text_input("Field of study", placeholder="e.g. Computer Science", key="signup_field")
                continue_signup = st.form_submit_button("Continue to security", use_container_width=True)
            if continue_signup:
                clean_email = st.session_state.signup_email.strip().lower()
                if not st.session_state.signup_name.strip():
                    st.error("Please enter your name.")
                elif "@" not in clean_email or "." not in clean_email.split("@")[-1]:
                    st.error("Please enter a valid email address.")
                elif clean_email in st.session_state.users_db:
                    st.error("An account with this email already exists. Sign in instead.")
                else:
                    st.session_state.signup_step = 2
                    st.rerun()
        else:
            st.markdown("### Account security")
            st.caption("Choose a password to protect your account.")
            with st.form("signup_security_form"):
                st.text_input("New password", type="password", placeholder="At least 6 characters", key="signup_password")
                st.text_input("Confirm password", type="password", placeholder="Re-enter your password", key="signup_confirm_password")
                create_account = st.form_submit_button("Create account", use_container_width=True)
            back_col, _ = st.columns([1, 3])
            with back_col:
                if st.button("← Back to academic details", key="signup_back"):
                    st.session_state.signup_step = 1
                    st.rerun()
            if create_account:
                password = st.session_state.signup_password
                confirm = st.session_state.signup_confirm_password
                if len(password) < 6:
                    st.error("Use a password with at least 6 characters.")
                elif password != confirm:
                    st.error("Passwords do not match. Please re-enter them.")
                else:
                    clean_email = st.session_state.signup_email.strip().lower()
                    user = {
                        "name": st.session_state.signup_name.strip(),
                        "school": st.session_state.signup_school.strip(),
                        "level": st.session_state.signup_level,
                        "field": st.session_state.signup_field.strip(),
                        "password_hash": password_hash(password),
                    }
                    st.session_state.users_db[clean_email] = user
                    st.session_state.correct_answers = 0
                    st.session_state.incorrect_answers = 0
                    st.session_state.recent_activities = []
                    st.session_state.uploaded_docs = []
                    st.session_state.notifications = []
                    st.session_state.chat_messages = []
                    st.session_state.signup_step = 1
                    set_signed_in_user(clean_email, user)
                    st.rerun()
    st.stop()


# =====================================================================
# 6. SIDEBAR NAVIGATION
# =====================================================================
with st.sidebar:
    render_html("""
    <div class="brand-box">
      <div class="brand-icon-wrapper">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/>
        </svg>
      </div>
      <div><div class="brand-name">Socratic AI</div><div class="brand-tag">Tutor dashboard</div></div>
    </div>
    """)

    nav_items = ["Dashboard", "AI Tutor", "Study Materials", "My Progress", "Profile"]
    for page_name in nav_items:
        button_type = "primary" if st.session_state.current_page == page_name else "secondary"
        if st.button(page_name, key=f"nav_{page_name}", type=button_type, use_container_width=True):
            st.session_state.current_page = page_name
            st.rerun()

    st.markdown("<div style='height:3rem'></div>", unsafe_allow_html=True)
    if st.button("Log out", key="btn_logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.current_page = "Dashboard"
        st.session_state.show_notifications = False
        st.rerun()


# =====================================================================
# 7. HEADER AND NOTIFICATIONS (ALIGNED TITLE & CIRCULAR ACTION ICONS)
# =====================================================================
try:
    header_left, header_right = st.columns([6, 1.2], vertical_alignment="center")
except TypeError:
    header_left, header_right = st.columns([6, 1.2])

display_name = st.session_state.user_name or "Student"

if st.session_state.current_page == "Dashboard":
    page_title = f"Welcome, {html.escape(display_name)}!"
    page_sub = "Your AI learning companion for smarter study."
elif st.session_state.current_page == "AI Tutor":
    page_title = "Socratic AI Tutor"
    page_sub = "Ask questions, get hints, and understand concepts step by step."
elif st.session_state.current_page == "Study Materials":
    page_title = "Study Materials"
    page_sub = "Upload textbooks and review your documents."
elif st.session_state.current_page == "My Progress":
    page_title = "My Progress"
    page_sub = "Track your learning milestones, accuracy, and study activity."
else:
    page_title = "Student Profile"
    page_sub = "View and manage your academic details."

with header_left:
    render_html(f"""
    <div class="header-text-block">
      <h1 class="greeting-main">{page_title}</h1>
      <p class="greeting-sub">{page_sub}</p>
    </div>
    """)

has_unread = any(n.get("unread", False) for n in st.session_state.notifications)
if has_unread:
    render_html("<style>.st-key-header_notifications button::after { content:'' !important; position:absolute !important; top:7px !important; right:8px !important; width:8px !important; height:8px !important; background-color:#EF4444 !important; border:1.5px solid #FFFFFF !important; border-radius:50% !important; }</style>")

with header_right:
    try:
        col_notif, col_profile = header_right.columns([1, 1], gap="small", vertical_alignment="center")
    except TypeError:
        col_notif, col_profile = header_right.columns([1, 1])

    with col_notif:
        if st.button("", icon=":material/notifications:", key="header_notifications", help="Notifications"):
            st.session_state.show_notifications = not st.session_state.show_notifications
            st.rerun()
    with col_profile:
        if st.button("", icon=":material/account_circle:", key="header_profile", help="Open profile"):
            st.session_state.current_page = "Profile"
            st.rerun()

if st.session_state.show_notifications:
    with st.container(border=True):
        st.subheader("Notifications")
        if st.session_state.notifications:
            for item in st.session_state.notifications:
                st.write(f"{'• ' if item.get('unread') else ''}{item['title']} · {item['time']}")
            if st.button("Mark all as read", key="mark_read"):
                for item in st.session_state.notifications:
                    item["unread"] = False
                st.session_state.show_notifications = False
                st.rerun()
        else:
            st.caption("You have no notifications yet.")


# =====================================================================
# 8. DASHBOARD
# =====================================================================
if st.session_state.current_page == "Dashboard":
    mascot_svg = get_mascot_svg()
    render_html(f"""
    <div class="hero-banner-card">
      <div class="hero-left"><h2 class="hero-title">Learn with AI Tutor</h2>
        <p class="hero-desc">Ask questions, get hints and understand concepts step by step.</p>
      </div><div class="hero-right">{mascot_svg}</div>
    </div>
    """)
    if st.button("Start learning", icon=":material/arrow_forward:", key="btn_start_learning"):
        st.session_state.current_page = "AI Tutor"
        st.rerun()

    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        if st.button("Upload PDF\nAdd your textbook", icon=":material/upload_file:", key="btn_upload_card", use_container_width=True, help="Open study materials"):
            st.session_state.current_page = "Study Materials"
            st.rerun()
    with action_col2:
        if st.button("AI Tutor\nLearn with guided questions", icon=":material/chat:", key="btn_tutor_card", use_container_width=True, help="Open AI Tutor"):
            st.session_state.current_page = "AI Tutor"
            st.rerun()
    with action_col3:
        if st.button("My Progress\nTrack your learning", icon=":material/monitoring:", key="btn_progress_card", use_container_width=True, help="Open your progress"):
            st.session_state.current_page = "My Progress"
            st.rerun()

    progress_col, activity_col = st.columns(2)
    with progress_col:
        correct = st.session_state.correct_answers
        incorrect = st.session_state.incorrect_answers
        donut_svg = get_donut_chart_svg(correct, incorrect)
        render_html(f"""
        <div class="dashboard-panel-box"><h3 class="dashboard-panel-header">My Learning Progress</h3>
          <div class="progress-box-content"><div class="progress-chart-wrapper">{donut_svg}</div>
            <div class="progress-legend-wrapper">
              <div class="legend-item"><span class="legend-dot green"></span><span>{correct} Correct Answers</span></div>
              <div class="legend-item"><span class="legend-dot red"></span><span>{incorrect} Incorrect Answers</span></div>
            </div>
          </div>
        </div>
        """)

    with activity_col:
        if st.session_state.recent_activities:
            activity_html = ""
            for activity in st.session_state.recent_activities:
                is_book = activity.get("icon") == "book"
                bg = "#E0E7FF" if is_book else "#E0F2FE"
                fg = "#4338CA" if is_book else "#0284C7"
                icon = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>') if is_book else ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>')
                title = html.escape(activity.get("title", "Activity"))
                when = html.escape(activity.get("time", ""))
                activity_html += f'<div class="activity-item-row"><div class="activity-item-icon" style="background:{bg};color:{fg};">{icon}</div><div class="activity-item-details"><p class="activity-item-title">{title}</p><p class="activity-item-time">{when}</p></div></div>'
        else:
            activity_html = '<div class="activity-empty-state"><p class="empty-title">No recent activity yet</p><p class="empty-sub">Your study activity will appear here when you chat with the tutor or add a document.</p></div>'
        render_html(f"""
        <div class="dashboard-panel-box"><h3 class="dashboard-panel-header">Recent Activity</h3>
          <div class="activity-list-wrapper">{activity_html}</div>
        </div>
        """)


# =====================================================================
# 9. AI TUTOR
# =====================================================================
elif st.session_state.current_page == "AI Tutor":
    with st.container(border=True):
        if not st.session_state.chat_messages:
            st.info("Start by asking a question about something you’re studying.")
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        prompt = st.chat_input("Ask a question about your studies…")
        if prompt:
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            response = (
                f"Let's reason through **{prompt}** together. What do you already know about it, "
                "and which part feels least clear?"
            )
            st.session_state.chat_messages.append({"role": "assistant", "content": response})
            add_activity("chat", f"AI Tutor chat: {prompt[:42]}")
            st.rerun()


# =====================================================================
# 10. STUDY MATERIALS
# =====================================================================
elif st.session_state.current_page == "Study Materials":
    with st.container(border=True):
        uploaded_file = st.file_uploader("Choose a PDF or text file", type=["pdf", "txt", "docx"], key="study_upload")
        if uploaded_file is not None and st.button("Add to my materials", key="add_material"):
            file_record = {
                "name": uploaded_file.name,
                "size": f"{uploaded_file.size / (1024 * 1024):.1f} MB",
                "uploaded_at": datetime.datetime.now().strftime("%b %d, %I:%M %p"),
            }
            if not any(doc.get("name") == uploaded_file.name for doc in st.session_state.uploaded_docs):
                st.session_state.uploaded_docs.insert(0, file_record)
                add_activity("book", f"Added study material: {uploaded_file.name[:40]}")
                st.session_state.notifications.insert(0, {
                    "title": f"Added {uploaded_file.name}",
                    "time": "Just now",
                    "unread": True,
                })
            st.success("Added to your materials for this session.")

        st.markdown("### Your documents")
        if st.session_state.uploaded_docs:
            for doc in st.session_state.uploaded_docs:
                safe_name = html.escape(doc["name"])
                render_html(f"""
                <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;background:#F8FAFC;border:1px solid #EEF2F6;border-radius:12px;margin-bottom:8px;">
                  <div><strong style="color:#1E293B;">{safe_name}</strong><div style="color:#64748B;font-size:.82rem;">{html.escape(doc['size'])} · Added {html.escape(doc['uploaded_at'])}</div></div>
                  <span style="color:#2563EB;font-size:.82rem;font-weight:700;">In this session</span>
                </div>
                """)
        else:
            st.info("No study materials added yet.")


# =====================================================================
# 11. MY PROGRESS
# =====================================================================
elif st.session_state.current_page == "My Progress":
    correct = st.session_state.correct_answers
    incorrect = st.session_state.incorrect_answers
    total = correct + incorrect
    accuracy = round(correct * 100 / total) if total else 0
    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Accuracy", f"{accuracy}%")
    metric2.metric("Correct answers", correct)
    metric3.metric("Incorrect answers", incorrect)
    with st.container(border=True):
        st.markdown("### Learning activity")
        if not st.session_state.recent_activities:
            st.info("No progress recorded yet. Your activity will appear after you use the tutor or add study materials.")
        else:
            for item in st.session_state.recent_activities:
                st.write(f"• {item['title']} · {item['time']}")


# =====================================================================
# 12. PROFILE
# =====================================================================
elif st.session_state.current_page == "Profile":
    with st.form("profile_edit_form"):
        profile_name = st.text_input("Full name", value=st.session_state.user_name)
        st.text_input("Email address", value=st.session_state.user_email, disabled=True)
        profile_school = st.text_input("Academic institution", value=st.session_state.user_school)
        levels = ["High School", "Undergraduate", "Post-Graduate", "Professional Learner"]
        current_level = st.session_state.user_level
        level_index = levels.index(current_level) if current_level in levels else 1
        profile_level = st.selectbox("Academic level", levels, index=level_index)
        profile_field = st.text_input("Field of study", value=st.session_state.user_field)
        save_profile = st.form_submit_button("Save changes", use_container_width=True)
    if save_profile:
        st.session_state.user_name = profile_name.strip()
        st.session_state.user_school = profile_school.strip()
        st.session_state.user_level = profile_level
        st.session_state.user_field = profile_field.strip()
        email = st.session_state.user_email
        if email in st.session_state.users_db:
            st.session_state.users_db[email].update({
                "name": st.session_state.user_name,
                "school": st.session_state.user_school,
                "level": profile_level,
                "field": st.session_state.user_field,
            })
        st.success("Profile updated.")
        st.rerun()