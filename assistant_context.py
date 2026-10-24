"""
assistant_context.py
Authoritative Context & Boundary Rules for the CerroAlto Knowledge Assistant.

Grounded strictly in the connected Employee.csv dataset (4,653 records across
Bangalore, New Delhi, and Pune) without hallucinating unavailable corporate lore.
"""

import re
from typing import Optional, Tuple


# ============================================================
# CHATBOT IDENTITY & CAPABILITIES
# ============================================================

BOT_NAME = "CerroAlto Knowledge Assistant"
ORGANIZATION_NAME = "CerroAlto Digital"
TOTAL_RECORDS = 4653
OFFICE_HUBS = ["Bangalore", "New Delhi", "Pune"]


def get_capabilities_response() -> str:
    """
    Returns a comprehensive, beautifully structured overview of what the
    assistant can help with.
    """
    return (
        f"I am the **{BOT_NAME}**, an enterprise AI assistant connected to "
        f"**{ORGANIZATION_NAME}'s** workforce knowledge base ({TOTAL_RECORDS:,} employee records "
        f"across Bangalore, New Delhi, and Pune).\n\n"
        f"Here is what I can help you with:\n\n"
        f"👥 **Workforce Demographics & Headcounts**\n"
        f"• Total employees and city-wise counts (Bangalore, New Delhi, Pune)\n"
        f"• Gender diversity breakdown and proportions\n"
        f"• Education levels (Bachelors, Masters, PhD distributions)\n\n"
        f"💼 **Experience & Career Metrics**\n"
        f"• Payment tiers (Tier 1, Tier 2, Tier 3 counts and averages)\n"
        f"• Years of experience in current domain and joining year trends\n"
        f"• Employee age groups and distribution\n\n"
        f"📊 **Workforce Analytics**\n"
        f"• Bench statistics (benched vs. active employees by city or tier)\n"
        f"• Leave and retention patterns across demographics\n\n"
        f"💡 **Sample Questions You Can Ask:**\n"
        f'• *"How many employees are in Bangalore?"*\n'
        f'• *"What percentage of employees are female?"*\n'
        f'• *"How many employees are in payment tier 1?"*\n'
        f'• *"Show benched employees in Pune"*\n'
        f'• *"What is the breakdown of employees by education level?"*'
    )


def get_company_overview_response() -> str:
    """
    Explains the organization strictly in terms of the connected system.
    """
    return (
        f"**{ORGANIZATION_NAME}** is the enterprise represented by this assistant.\n\n"
        f"This knowledge system currently integrates our verified workforce dataset "
        f"covering **{TOTAL_RECORDS:,} professionals** across three primary operational hubs:\n"
        f"• **Bangalore** (Major technology & engineering workforce)\n"
        f"• **New Delhi** (Operations & corporate solutions center)\n"
        f"• **Pune** (Product & engineering talent center)\n\n"
        f"*Note: This assistant connects to internal employee and workforce data. "
        f"Corporate records such as commercial contracts, executive boards, or external "
        f"financials are not part of this dataset.*"
    )


def get_unavailable_company_data_response(query_topic: str) -> str:
    """
    Transparently clarifies that broader corporate info is not in the knowledge base.
    """
    return (
        f"I cannot provide {query_topic} for {ORGANIZATION_NAME}. "
        f"My knowledge base is specifically connected to our internal workforce dataset "
        f"({TOTAL_RECORDS:,} employee records across demographics, payment tiers, experience, "
        f"and locations). General corporate records such as executive leadership, company history, "
        f"or commercial revenue are not maintained in this system."
    )


def get_out_of_scope_response() -> str:
    """
    Polite decline for off-topic, external queries (sports, trivia, general world info).
    """
    return (
        f"I am specifically designed as the **{BOT_NAME}**. "
        f"I can only assist with questions regarding {ORGANIZATION_NAME} and our "
        f"connected workforce dataset.\n\n"
        f"Please ask a question related to:\n"
        f"• Employee counts, demographics, or office hubs (Bangalore, New Delhi, Pune)\n"
        f"• Education levels, experience, or payment tiers\n"
        f"• Bench rates or workforce analytics"
    )


# ============================================================
# INTENT DETECTION HELPERS
# ============================================================

def is_capabilities_or_help_query(q: str) -> bool:
    """
    Detects if the user is asking what the bot can do, requesting help,
    or asking about the bot's identity.
    """
    q_clean = q.lower().strip()
    q_norm = re.sub(r"[^\w\s]", " ", q_clean)
    q_norm = re.sub(r"\s+", " ", q_norm).strip()

    patterns = [
        r"\bwhat (?:can|do) you (?:do|help|assist|provide)\b",
        r"\bwhat (?:can|could) i ask\b",
        r"\bhow (?:can|do) you help\b",
        r"\bhow to use\b",
        r"\b(?:help|assist|capabilities|features|guide)\b",
        r"\bwho are you\b",
        r"\bwhat are you\b",
        r"\bwhat is your (?:purpose|role|name|job)\b",
        r"\btell me about yourself\b",
        r"\bwho made you\b",
        r"\bwhat kind of questions\b",
        r"\bwhat data (?:do you have|is available)\b",
        r"\bwhat (?:dataset|database) is connected\b",
    ]

    return any(re.search(pat, q_norm) for pat in patterns)


def is_company_overview_query(q: str) -> bool:
    """
    Detects questions asking what CerroAlto Digital is or where offices are.
    """
    q_norm = re.sub(r"[^\w\s]", " ", q.lower()).strip()

    patterns = [
        r"\bwhat is cerro\s*alto\b",
        r"\btell me about cerro\s*alto\b",
        r"\bwhat does (?:the company|cerro\s*alto) do\b",
        r"\bwhere are (?:the|our|company) (?:offices|locations|hubs)\b",
        r"\bwhich cities (?:do we|does cerro\s*alto) (?:operate|have offices)\b",
        r"\babout (?:the )?company\b",
        r"\bcompany overview\b",
    ]

    return any(re.search(pat, q_norm) for pat in patterns)


def is_unavailable_corporate_query(q: str) -> Optional[str]:
    """
    Detects questions about corporate lore that is NOT in the dataset,
    such as CEO, revenue, company founding, or office address.
    """
    q_norm = re.sub(r"[^\w\s]", " ", q.lower()).strip()

    if any(p in q_norm for p in ["ceo", "chief executive", "founder", "founded by", "leadership", "chairman", "board of directors"]):
        return "executive leadership or founder information"
    if any(p in q_norm for p in ["revenue", "annual revenue", "turnover", "profit", "valuation", "financial results"]):
        return "company revenue or financial data"
    if any(p in q_norm for p in ["history", "when was (?:the company|cerro)", "founded in", "founding date"]):
        return "company founding history"
    if any(p in q_norm for p in ["office address", "street address", "headquarters address", "where is the headquarters"]):
        return "physical street address or headquarters details"
    if any(p in q_norm for p in ["products", "what do you sell", "clients", "customers"]):
        return "commercial product catalogs or client lists"

    return None


def is_out_of_scope_query(q: str) -> bool:
    """
    Detects questions that are completely unrelated to CerroAlto or its data
    (e.g., world trivia, sports, cooking recipes, external movie questions).
    """
    q_norm = re.sub(r"[^\w\s]", " ", q.lower()).strip()

    # If the question explicitly mentions employee, dataset, cerroalto, or our cities, it is NOT out of scope
    if any(k in q_norm for k in ["employee", "employees", "staff", "workforce", "cerroalto", "cerro", "tier",
                                 "bangalore", "pune", "delhi", "benched", "salary", "dataset"]):
        return False

    out_of_scope_triggers = [
        r"\b(?:weather|recipe|cooking|cake|pizza|movie|song|actor|actress|football|fifa|world cup|cricket|tennis|basketball)\b",
        r"\b(?:president|prime minister|capital of|how to cook|write a poem|write a song|game|joke)\b",
        r"\b(?:python script to hack|who won the)\b",
        r"\b(?:bitcoin|cryptocurrency|astrology|horoscope)\b",
    ]

    return any(re.search(pat, q_norm) for pat in out_of_scope_triggers)
