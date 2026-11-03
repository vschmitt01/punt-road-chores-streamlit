import os
import smtplib
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(page_title="PUNT RD chores", page_icon="🧹", layout="centered")

TIMEZONE = ZoneInfo("Australia/Melbourne")

ANCHOR_DATE = date(2026, 10, 5)   # Monday of Week 3
ANCHOR_WEEK = 3

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL

CHORES = {
    1: {"Kitchen": "Keith",   "Laundry": "Abbey",   "Dining Room": "Victor",
        "Dungeon": "Paul",    "Halls and stairways": "Claudia", "Bathroom": "Claudia"},
    2: {"Kitchen": "Claudia", "Laundry": "Keith",   "Dining Room": "Abbey",
        "Dungeon": "Victor",  "Halls and stairways": "Paul",    "Bathroom": "Paul"},
    3: {"Kitchen": "Paul",    "Laundry": "Claudia", "Dining Room": "Keith",
        "Dungeon": "Abbey",   "Halls and stairways": "Victor",  "Bathroom": "Victor"},
    4: {"Kitchen": "Victor",  "Laundry": "Paul",    "Dining Room": "Claudia",
        "Dungeon": "Keith",   "Halls and stairways": "Abbey",   "Bathroom": "Abbey"},
}

PEOPLE = ["Keith", "Abbey", "Victor", "Paul", "Claudia"]


# ============================================================
# SECRETS (never hardcode credentials in the file)
# ============================================================
# Create .streamlit/secrets.toml next to this file:
#
#   SENDER_EMAIL = "you@gmail.com"
#   SENDER_PASSWORD = "xxxx xxxx xxxx xxxx"     # Gmail App Password
#
#   [members]
#   Keith = "keith@example.com"
#   Abbey = "abbey@example.com"
#   Victor = "victor@example.com"
#   Paul = "paul@example.com"
#   Claudia = "claudia@example.com"

def get_secret(key, default=""):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, default)


def get_members():
    try:
        return dict(st.secrets["members"])
    except Exception:
        return {}


SENDER_EMAIL = get_secret("SENDER_EMAIL")
SENDER_PASSWORD = get_secret("SENDER_PASSWORD")
MEMBERS = get_members()


# ============================================================
# WEEK LOGIC
# ============================================================

def week_start(d):
    return d - timedelta(days=d.weekday())


def get_week_number(d):
    weeks_elapsed = (week_start(d) - ANCHOR_DATE).days // 7
    return ((ANCHOR_WEEK - 1 + weeks_elapsed) % 4) + 1


def week_label(d):
    monday = week_start(d)
    return f"Mon {monday.day} {monday:%b}"


def build_message(week_number, label):
    lines = [f"🧹 PUNT RD chores - Week {week_number} ({label})", ""]
    lines += [f"{chore}: {person}" for chore, person in CHORES[week_number].items()]
    lines += ["", "Have a good week!"]
    return "\n".join(lines)


# ============================================================
# EMAIL
# ============================================================

def send_email(recipients, week_number, label):
    msg = EmailMessage()
    msg["Subject"] = f"PUNT RD chores - Week {week_number} ({label})"
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(recipients)
    msg.set_content(build_message(week_number, label))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)


# ============================================================
# UI
# ============================================================

today = datetime.now(TIMEZONE).date()

st.title("🧹 PUNT RD chores")

with st.sidebar:
    st.header("Week")
    picked = st.date_input("Show the week containing", value=today)
    if st.button("Back to today"):
        st.rerun()

week = get_week_number(picked)
label = week_label(picked)
is_current = week_start(picked) == week_start(today)

tab_week, tab_rotation, tab_email = st.tabs(["This week", "Full rotation", "Send email"])

# ---------- Tab 1: the week's roster ----------
with tab_week:
    st.subheader(f"Week {week} ({label})" + ("  ·  current week" if is_current else ""))

    roster = pd.DataFrame(
        {"Chore": list(CHORES[week].keys()), "Who": list(CHORES[week].values())}
    )
    st.dataframe(roster, hide_index=True, use_container_width=True)

    st.markdown("**Who does what**")
    who = st.selectbox("Pick a person", PEOPLE, index=PEOPLE.index("Victor"))
    mine = [chore for chore, person in CHORES[week].items() if person == who]
    if mine:
        st.success(f"{who}: " + ", ".join(mine))
    else:
        st.info(f"{who} has no chores this week.")

# ---------- Tab 2: the 4-week rotation ----------
with tab_rotation:
    st.subheader("4-week rotation")
    rotation = pd.DataFrame(
        {f"Week {w}": CHORES[w] for w in sorted(CHORES)}
    )
    rotation.index.name = "Chore"

    def highlight_current(col):
        if col.name == f"Week {week}":
            return ["background-color: #fff3bf; color: #000"] * len(col)
        return [""] * len(col)

    st.dataframe(rotation.style.apply(highlight_current), use_container_width=True)
    st.caption(
        f"Week 3 starts on {ANCHOR_DATE:%A %d %B %Y}; the cycle then repeats every 4 weeks."
    )

# ---------- Tab 3: email ----------
with tab_email:
    st.subheader("Send the roster by email")

    if not SENDER_EMAIL or not SENDER_PASSWORD:
        st.warning(
            "Email isn't configured. Add SENDER_EMAIL and SENDER_PASSWORD "
            "(a Gmail App Password) to `.streamlit/secrets.toml`."
        )
    elif not MEMBERS:
        st.warning("No recipients found. Add a `[members]` table to `.streamlit/secrets.toml`.")
    else:
        chosen = st.multiselect("Recipients", list(MEMBERS.keys()), default=list(MEMBERS.keys()))

        st.markdown(f"**Preview**: Week {week} ({label})")
        st.code(build_message(week, label), language=None)

        if not is_current:
            st.info("You're previewing a week other than the current one. This email will contain that week's roster.")

        confirm = st.checkbox("I want to send this email now")

        if st.button("Send email", type="primary", disabled=not (chosen and confirm)):
            recipients = [MEMBERS[name] for name in chosen]
            try:
                with st.spinner("Sending..."):
                    send_email(recipients, week, label)
                st.success("Email sent to: " + ", ".join(chosen))
            except smtplib.SMTPAuthenticationError:
                st.error("Login failed. Check the Gmail App Password (not your normal password).")
            except Exception as e:
                st.error(f"Could not send the email: {e}")
