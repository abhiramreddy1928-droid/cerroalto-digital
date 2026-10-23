import logging
from pathlib import Path

import re
import pandas as pd
import inngest
import inngest.fast_api
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from data_loader import (
    EMBED_DIM,
    load_employee_csv,
    embed_texts,
)

from vector_db import QdrantStorage, COLLECTION
from ollama_client import generate_answer


# ============================================================
# LOAD EMPLOYEE DATA FOR EXACT ANSWERS
# ============================================================

CSV_PATH = Path(__file__).parent / "Employee.csv"

employee_df = pd.read_csv(CSV_PATH)

print(f"Loaded {len(employee_df)} employee records.")


def answer_from_dataset(question: str) -> str | None:
    """
    Answer exact CSV count and record-listing questions.
    Return None when the question should be handled by RAG.
    """
    q = question.lower().strip()
    q = re.sub(r"[^\w\s]", " ", q)
    q = re.sub(r"\s+", " ", q)
    q = re.sub(r"\bemploye+s+\b", "employees", q)

    # Keep the assistant grounded: this CSV contains employee attributes only,
    # not company leadership, financial, or address information.
    if any(
        phrase in q
        for phrase in [
            "ceo",
            "chief executive",
            "annual revenue",
            "revenue",
            "office address",
            "company address",
        ]
    ):
        return (
            "I cannot answer that from the employee dataset. It contains "
            "employee records only, not CEO, revenue, or office-address data."
        )

    # Gender-distribution questions must use every employee row, not the
    # small set of records returned by semantic retrieval.
    if any(word in q for word in ["percentage", "percent", "proportion"]):
        total = len(employee_df)
        male_count = int(employee_df["Gender"].eq("Male").sum())
        female_count = int(employee_df["Gender"].eq("Female").sum())
        asks_for_female = bool(re.search(r"\bfemale\b", q))
        asks_for_male = bool(re.search(r"\bmale\b", q))

        if asks_for_female and asks_for_male:
            return (
                f"The company has {male_count:,} male employees "
                f"({male_count / total * 100:.1f}%) and {female_count:,} "
                f"female employees ({female_count / total * 100:.1f}%)."
            )
        if asks_for_male:
            return (
                f"There are {male_count:,} male employees, which is "
                f"{male_count / total * 100:.1f}% of all employees."
            )
        if asks_for_female:
            return (
                f"There are {female_count:,} female employees, which is "
                f"{female_count / total * 100:.1f}% of all employees."
            )

        for phrase, city in {
            "new delhi": "New Delhi",
            "bangalore": "Bangalore",
            "banglore": "Bangalore",
            "bengaluru": "Bangalore",
            "pune": "Pune",
        }.items():
            if re.search(rf"\b{re.escape(phrase)}\b", q):
                city_count = int(employee_df["City"].eq(city).sum())
                return (
                    f"There are {city_count:,} employees in {city}, which is "
                    f"{city_count / total * 100:.1f}% of all employees."
                )

    if any(
        phrase in q
        for phrase in [
            "relationship",
            "factors associated",
            "factors are associated",
            "why employees leave",
            "why do employees leave",
            "leave patterns",
        ]
    ) and any(phrase in q for phrase in ["leaving", "leave", "leaveornot"]):
        tier_rates = employee_df.groupby("PaymentTier")["LeaveOrNot"].mean().mul(100)
        city_rates = employee_df.groupby("City")["LeaveOrNot"].mean().mul(100)
        education_rates = employee_df.groupby("Education")["LeaveOrNot"].mean().mul(100)
        return (
            "Full-dataset leave-rate summary:\n"
            f"- Payment Tier {tier_rates.idxmax()} has the highest leave rate "
            f"({tier_rates.max():.1f}%), while Tier {tier_rates.idxmin()} has "
            f"the lowest ({tier_rates.min():.1f}%).\n"
            f"- {city_rates.idxmax()} has the highest city leave rate "
            f"({city_rates.max():.1f}%).\n"
            f"- {education_rates.idxmax()} employees have the highest education "
            f"group leave rate ({education_rates.max():.1f}%)."
        )

    wants_count = any(phrase in q for phrase in ["how many", "count", "number of"])
    wants_all_records = bool(
        re.search(
            r"\b(?:give|show|list|return)?\s*(?:me\s+)?all\s+"
            r"(?:the\s+)?(?:records?|employees?)\b",
            q,
        )
        or re.search(
            r"\b(?:give|show|list|return)\s+(?:me\s+)?(?:all|every|each)\b",
            q,
        )
    )
    filtered_df = employee_df.copy()
    applied_filters: list[str] = []

    # Exact values for categorical columns. Whole-word matching prevents
    # "male" from being incorrectly found inside "female".
    excluded_gender_match = re.search(
        r"\b(?:non|not|excluding|except(?:\s+for)?|other\s+than)\s+"
        r"(female|male)s?\b",
        q,
    )
    gender_match = re.search(r"\b(female|male)s?\b", q)
    if excluded_gender_match:
        gender = excluded_gender_match.group(1).title()
        filtered_df = filtered_df[filtered_df["Gender"].ne(gender)]
        applied_filters.append(f"excluding {gender.lower()}")
    elif gender_match:
        gender = gender_match.group(1).title()
        filtered_df = filtered_df[filtered_df["Gender"].eq(gender)]
        applied_filters.append(gender)

    education_match = re.search(r"\b(bachelor|bachelors|master|masters|phd)\b", q)
    if education_match:
        education = {
            "bachelor": "Bachelors",
            "bachelors": "Bachelors",
            "master": "Masters",
            "masters": "Masters",
            "phd": "PHD",
        }[education_match.group(1)]
        filtered_df = filtered_df[filtered_df["Education"].eq(education)]
        applied_filters.append(education)

    payment_tier_match = re.search(
        r"\b(?:payment\s+)?tier\s*(?:is\s*)?(\d+)\b",
        q,
    )
    if payment_tier_match:
        payment_tier = int(payment_tier_match.group(1))
        filtered_df = filtered_df[
            filtered_df["PaymentTier"].eq(payment_tier)
        ]
        applied_filters.append(f"payment tier {payment_tier}")

    for phrase, city in {
        "new delhi": "New Delhi",
        "bangalore": "Bangalore",
        "banglore": "Bangalore",
        "bengaluru": "Bangalore",
        "pune": "Pune",
    }.items():
        city_exclusion = re.search(
            rf"\b(?:excluding|except(?:\s+for)?|other\s+than|"
            rf"not\s+(?:from|in))\s+(?:the\s+)?{re.escape(phrase)}\b",
            q,
        )
        if city_exclusion:
            filtered_df = filtered_df[filtered_df["City"].ne(city)]
            applied_filters.append(f"excluding {city}")
            break
        if re.search(rf"\b{re.escape(phrase)}\b", q):
            filtered_df = filtered_df[filtered_df["City"].eq(city)]
            applied_filters.append(city)
            break

    if re.search(r"\b(?:never|not)\s+(?:been\s+)?benched\b", q):
        filtered_df = filtered_df[filtered_df["EverBenched"].eq("No")]
        applied_filters.append("never benched")
    elif re.search(r"\bever\s+(?:been\s+)?benched\b", q):
        filtered_df = filtered_df[filtered_df["EverBenched"].eq("Yes")]
        applied_filters.append("ever benched")

    excluded_joining_year_range = re.search(
        r"\b(?:did\s+not|not)\s+join(?:\s+in)?\s+between\s+(\d{4})\s+(?:to|and)\s+(\d{4})\b",
        q,
    )
    excluded_joining_year = re.search(
        r"\b(?:did\s+not|not)\s+join(?:\s+in)?\s+(\d{4})\b",
        q,
    )
    joining_year_range = re.search(
        r"\b(?:joined(?:\s+in)?|joining\s+year)\s+between\s+(\d{4})\s+(?:to|and)\s+(\d{4})\b",
        q,
    )
    joining_year_match = re.search(
        r"\b(?:joining\s+year|joined(?:\s+in)?)\s*(?:is\s*)?(\d{4})\b",
        q,
    )
    joining_year_after = re.search(
        r"\b(?:joining\s+year|joined(?:\s+in)?)\s+(?:is\s+)?(?:after|greater\s+than)\s+(\d{4})\b",
        q,
    )
    if excluded_joining_year_range:
        start_year, end_year = sorted(
            map(int, excluded_joining_year_range.groups())
        )
        filtered_df = filtered_df[
            ~filtered_df["JoiningYear"].between(start_year, end_year)
        ]
        applied_filters.append(
            f"joining years outside {start_year} through {end_year}"
        )
    elif excluded_joining_year:
        joining_year = int(excluded_joining_year.group(1))
        filtered_df = filtered_df[
            filtered_df["JoiningYear"].ne(joining_year)
        ]
        applied_filters.append(f"joining year other than {joining_year}")
    elif joining_year_range:
        start_year, end_year = sorted(map(int, joining_year_range.groups()))
        filtered_df = filtered_df[
            filtered_df["JoiningYear"].between(start_year, end_year)
        ]
        applied_filters.append(
            f"joining years {start_year} through {end_year}"
        )
    elif joining_year_after:
        joining_year = int(joining_year_after.group(1))
        filtered_df = filtered_df[
            filtered_df["JoiningYear"].gt(joining_year)
        ]
        applied_filters.append(f"joining year after {joining_year}")
    elif joining_year_match:
        joining_year = int(joining_year_match.group(1))
        filtered_df = filtered_df[
            filtered_df["JoiningYear"].eq(joining_year)
        ]
        applied_filters.append(f"joining year {joining_year}")

        # "no experience", "zero experience", "without any experience" -> 0 years
    no_experience_match = re.search(
        r"\b(?:no|zero|nil|without(?:\s+any)?)\s+"
        r"(?:(?:work|prior|domain)\s+)?"
        r"(?:years?\s+(?:of\s+)?)?experience\b",
        q,
    )

    experience_comparison = re.search(
        r"\b(?:more|greater)\s+than\s+(\d+)\s+years?\s+(?:of\s+)?"
        r"(?:current\s+domain\s+)?experience\b",
        q,
    )
    experience_match = re.search(
        r"\bexperience(?:\s+in\s+(?:their\s+)?current\s+domain)?\s+(?:(?:of|is)\s+)?(\d+)\b"
        r"|\b(\d+)\s+(?:years?\s+(?:of\s+)?(?:current\s+domain\s+)?)?experience\b",
        q,
    )

    years = None

    if experience_comparison:
        years = int(experience_comparison.group(1))
        filtered_df = filtered_df[
            filtered_df["ExperienceInCurrentDomain"].gt(years)
        ]
        applied_filters.append(f"more than {years} years of experience")
    elif no_experience_match:
        years = 0
    elif experience_match:
        years = int(experience_match.group(1) or experience_match.group(2))

    if years is not None and not experience_comparison:
        filtered_df = filtered_df[
            filtered_df["ExperienceInCurrentDomain"].eq(years)
        ]
        applied_filters.append(f"{years} years of experience")

    age_comparison = re.search(
        r"\bage\s*(?:is\s*)?(greater|more|older|above|over|less|fewer|younger|below|under)\s+(?:than\s+)?(\d+)\b",
        q,
    )
    age_threshold = re.search(
        r"\b(?:age|aged)\s*(?:is\s*)?(\d+)\s*"
        r"(or\s+above|and\s+above|or\s+greater|and\s+greater|or\s+more|and\s+more|"
        r"or\s+older|and\s+older|or\s+below|and\s+below|or\s+less|and\s+less|"
        r"or\s+fewer|and\s+fewer|or\s+younger|and\s+younger)\b",
        q,
    )
    relative_age_comparison = re.search(
        r"\b(older|younger|under|below)\s+(?:than\s+)?(\d+)\b",
        q,
    )
    exact_age = re.search(r"\b(?:age|aged)\s*(?:is\s*)?(\d+)\b", q)

    if age_comparison or relative_age_comparison:
        comparison, age_text = (age_comparison or relative_age_comparison).groups()
        age = int(age_text)
        if comparison in {"greater", "more", "older", "above", "over"}:
            filtered_df = filtered_df[filtered_df["Age"].gt(age)]
            applied_filters.append(f"age greater than {age}")
        else:
            filtered_df = filtered_df[filtered_df["Age"].lt(age)]
            applied_filters.append(f"age less than {age}")
    elif age_threshold:
        age = int(age_threshold.group(1))
        comparison = age_threshold.group(2)
        if any(word in comparison for word in ["above", "greater", "more", "older"]):
            filtered_df = filtered_df[filtered_df["Age"].ge(age)]
            applied_filters.append(f"age {age} or above")
        else:
            filtered_df = filtered_df[filtered_df["Age"].le(age)]
            applied_filters.append(f"age {age} or below")
    elif exact_age:
        age = int(exact_age.group(1))
        filtered_df = filtered_df[filtered_df["Age"].eq(age)]
        applied_filters.append(f"age {age}")

            # Leave status: LeaveOrNot is 1 for employees who left, 0 for those who stayed
    stayed_match = re.search(
        r"\b(?:stayed|remained|still\s+(?:working|employed)|"
        r"(?:did\s+not|didn\s+t|do\s+not|don\s+t|have\s+not|haven\s+t|not|never)"
        r"\s+(?:been\s+)?(?:leave|left|leaving|resign|resigned|quit))\b",
        q,
    )
    left_match = re.search(r"\b(?:left|leave|leaving|resigned|quit)\b", q)

    if stayed_match:
        filtered_df = filtered_df[filtered_df["LeaveOrNot"].eq(0)]
        applied_filters.append("did not leave")
    elif left_match:
        filtered_df = filtered_df[filtered_df["LeaveOrNot"].eq(1)]
        applied_filters.append("left the company")

    # Ranking and comparison questions belong to answer_analytics_question
    asks_for_analysis = bool(
        re.search(r"\b(?:highest|lowest|most|least|average|rate|compare|versus|vs)\b", q)
    )

    if wants_all_records and applied_filters:
        if filtered_df.empty:
            return "No employee records match those conditions."

        records = []
        for row_index, row in filtered_df.iterrows():
            details = ", ".join(f"{column}: {row[column]}" for column in employee_df.columns)
            records.append(f"Employee record {row_index + 1}: {details}")
        return f"Found {len(filtered_df):,} matching employee records:\n\n" + "\n".join(records)

    if wants_count and applied_filters and not asks_for_analysis:
        return f"There are {len(filtered_df):,} employees matching: {', '.join(applied_filters)}."

    is_unfiltered_total_request = not any(
        phrase in q
        for phrase in [
            "left",
            "leaving",
            "leave",
            "city",
            "bangalore",
            "banglore",
            "bengaluru",
            "pune",
            "new delhi",
            "education",
            "payment tier",
            "gender",
            "benched",
            "experience",
            "age",
            "joined",
            "joining",
        ]
    )
    if wants_count and is_unfiltered_total_request and any(
        pattern in q
        for pattern in ["how many employees", "total employees", "total number of employees", "employee count", "number of employees", "how many employee records"]
    ):
       return f"The company has {len(employee_df):,} employees."

    return None


def answer_analytics_question(question: str) -> str | None:
    """
    Answer comparisons, leave-rate, ranking, and average questions
    using every row in Employee.csv.
    """

    q = question.lower().strip()
    q = re.sub(r"[^\w\s]", " ", q)
    q = re.sub(r"\s+", " ", q)

    left = employee_df[employee_df["LeaveOrNot"].eq(1)]
    stayed = employee_df[employee_df["LeaveOrNot"].eq(0)]

    # Compare female and male leave rates in each city.
    if (
        "leave rate" in q
        and "female" in q
        and "male" in q
        and "city" in q
    ):
        rates = (
            employee_df.groupby(["City", "Gender"])["LeaveOrNot"]
            .mean()
            .mul(100)
            .round(1)
        )

        highest_group = rates.idxmax()
        highest_rate = rates.max()

        lines = [
            f"{city}, {gender}: {rate:.1f}%"
            for (city, gender), rate in rates.items()
        ]

        return (
            "Leave rates by city and gender:\n"
            + "\n".join(lines)
            + f"\n\nHighest leave rate: {highest_group[1]} employees "
            + f"in {highest_group[0]} ({highest_rate:.1f}%)."
        )

    # Find the highest payment-tier leave rate among older employees.
    if (
        "payment tier" in q
        and "highest" in q
        and "leave rate" in q
        and ("30 or above" in q or "aged 30" in q)
    ):
        older_employees = employee_df[employee_df["Age"].ge(30)]

        rates = (
            older_employees.groupby("PaymentTier")["LeaveOrNot"]
            .mean()
            .mul(100)
            .round(1)
        )

        highest_tier = rates.idxmax()

        return (
            f"Among employees aged 30 or above, Payment Tier "
            f"{highest_tier} has the highest leave rate: "
            f"{rates[highest_tier]:.1f}%.\n\n"
            + "\n".join(
                f"Payment Tier {tier}: {rate:.1f}%"
                for tier, rate in rates.items()
            )
        )

    # Find the city + education combination with the most employees leaving.
    if (
        "city" in q
        and "education" in q
        and "highest" in q
        and any(word in q for word in ["left", "leaving", "leave"])
    ):
        grouped = left.groupby(["City", "Education"]).size()
        city, education = grouped.idxmax()
        count = grouped.max()

        return (
            f"The city-and-education combination with the highest "
            f"number of employees who left is {city} + {education}: "
            f"{count:,} employees."
        )

    # Compare employees who left with employees who stayed.
    if (
        "average age" in q
        and "employees who left" in q
        and "employees who stayed" in q
    ):
        return (
            "Comparison of employees who left and employees who stayed:\n"
            f"- Left: average age {left['Age'].mean():.1f}, "
            f"average current-domain experience "
            f"{left['ExperienceInCurrentDomain'].mean():.1f} years.\n"
            f"- Stayed: average age {stayed['Age'].mean():.1f}, "
            f"average current-domain experience "
            f"{stayed['ExperienceInCurrentDomain'].mean():.1f} years."
        )

    # Check whether higher payment tiers always mean a lower leave rate.
    if (
        "payment tier" in q
        and "lower chance of leaving" in q
    ):
        rates = (
            employee_df.groupby("PaymentTier")["LeaveOrNot"]
            .mean()
            .mul(100)
            .round(1)
        )

        return (
            "No. Higher payment tiers do not always have a lower "
            "leave rate.\n"
            + "\n".join(
                f"Payment Tier {tier}: {rate:.1f}%"
                for tier, rate in rates.items()
            )
        )

    return None


def is_employee_dataset_question(question: str) -> bool:
    """Return True when a question concerns fields in Employee.csv.

    RAG retrieves a small sample of records, so it must never be used for
    counts, percentages, filters, rankings, or other dataset calculations.
    """
    q = question.lower()
    dataset_terms = [
        "employee",
        "employees",
        "gender",
        "male",
        "female",
        "city",
        "bangalore",
        "banglore",
        "bengaluru",
        "pune",
        "new delhi",
        "education",
        "bachelor",
        "master",
        "phd",
        "payment tier",
        "age",
        "benched",
        "experience",
        "joining year",
        "joined",
        "leave",
        "leaveornot",
        "percentage",
        "percent",
        "average",
        "highest",
        "lowest",
        "how many",
        "number of",
        "count",
        "list",
    ]
    return any(re.search(rf"\b{re.escape(term)}", q) for term in dataset_terms)


# ============================================================
# INNGEST CLIENT
# ============================================================

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
)


# ============================================================
# 1. EMPLOYEE CSV INGESTION
# ============================================================

@inngest_client.create_function(
    fn_id="RAG: Ingest Employee CSV",
    trigger=inngest.TriggerEvent(
        event="rag/ingest_employee_csv"
    ),
)
async def rag_ingest_employee_csv(ctx: inngest.Context):

    csv_path = Path(__file__).parent / "Employee.csv"

    texts = await ctx.step.run(
        "load-employee-csv",
        lambda: load_employee_csv(str(csv_path)),
    )

    total_records = len(texts)

    # Process 100 employees at a time
    batch_size = 100

    records_stored = 0

    for start in range(0, total_records, batch_size):

        end = min(start + batch_size, total_records)

        batch_number = (start // batch_size) + 1

        batch_texts = texts[start:end]

        def process_batch(
            batch_texts=batch_texts,
            start=start,
            end=end,
        ):

            # Generate LOCAL embeddings
            vectors = embed_texts(
                batch_texts,
                task_type="RETRIEVAL_DOCUMENT",
            )

            ids = list(range(start + 1, end + 1))

            payloads = []

            for text, employee_id in zip(batch_texts, ids):
                payloads.append(
                    {
                        "text": text,
                        "source": "Employee.csv",
                        "employee_id": employee_id,
                    }
                )

            store = QdrantStorage()

            store.upsert(
                ids=ids,
                vectors=vectors,
                payloads=payloads,
            )

            return len(ids)

        stored = await ctx.step.run(
            f"embed-and-store-batch-{batch_number}",
            process_batch,
        )

        records_stored += stored

    return {
        "status": "success",
        "records_loaded": total_records,
        "records_stored": records_stored,
        "collection": COLLECTION,
        "embedding_dimension": EMBED_DIM,
    }


# ============================================================
# 2. QUERY EMPLOYEE DATA (Inngest)
# ============================================================

@inngest_client.create_function(
    fn_id="RAG: Query Employee Data",
    trigger=inngest.TriggerEvent(
        event="rag/query_employee_data"
    ),
)
async def rag_query_employee_data(ctx: inngest.Context):

    question = str(ctx.event.data.get("question", "")).strip()

    if not question:
        return {
            "status": "error",
            "message": "Question is required.",
        }

    try:
        top_k = int(ctx.event.data.get("top_k", 5))
    except (TypeError, ValueError):
        top_k = 4653

    top_k = max(1, min(top_k, 20))

    def search_employee_data():

        query_vector = embed_texts(
            [question],
            task_type="RETRIEVAL_QUERY",
        )[0]

        store = QdrantStorage()

        results = store.search(
            query_vector=query_vector,
            top_k=top_k,
        )

        return {
            "contexts": list(results.get("contexts", [])),
            "sources": list(results.get("sources", [])),
        }

    found = await ctx.step.run(
        "embed-and-search",
        search_employee_data,
    )

    contexts = found["contexts"]
    sources = found["sources"]

    if not contexts:
        return {
            "status": "success",
            "question": question,
            "answer": "The information is not available.",
            "contexts": [],
            "sources": [],
            "context_block": "",
            "num_contexts": 0,
        }

    context_block = "\n\n".join(contexts)

    answer = await ctx.step.run(
        "generate-answer",
        lambda: generate_answer(question, context_block),
    )

    return {
        "status": "success",
        "question": question,
        "answer": answer,
        "contexts": contexts,
        "sources": sources,
        "context_block": context_block,
        "num_contexts": len(contexts),
    }


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI()


# Allow the frontend to call the API from any origin
# (file://, VS Code Live Server on port 5500, or this server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def root():

    return {
        "status": "ok",
        "message": "RAG Employee Assistant API is running",
    }


@app.get("/health")
def health():

    return {
        "status": "ok",
        "message": "RAG Employee Assistant API is running",
    }


# ============================================================
# CHAT ENDPOINT FOR THE FRONTEND
# ============================================================

class AskRequest(BaseModel):
    question: str
    top_k: int = 5



@app.post("/api/ask")
async def ask(req: AskRequest):
    try:
        # 1. Read and validate the question FIRST
        question = req.question.strip()

        if not question:
            raise HTTPException(
                status_code=400,
                detail="Question is required.",
            )

        logging.info("Received question: %s", question)

        # 2. Answer exact dataset questions directly from the CSV
        direct_answer = answer_from_dataset(question)
        if direct_answer is not None:
            return {
                "answer": direct_answer,
                "contexts": [],
                "sources": ["Employee.csv"],
                "total_records": len(employee_df),
                "answer_type": "direct_dataset_query",
            }

        # 3. Answer comparison and aggregation questions from the full CSV
        analytics_answer = answer_analytics_question(question)

        if analytics_answer is not None:
            return {
                "answer": analytics_answer,
                "contexts": [],
                "sources": ["Employee.csv"],
                "total_records": len(employee_df),
                "answer_type": "direct_dataset_analysis",
            }

        # 4. Do not let RAG guess from a small sample of employee rows.
        # A question about Employee.csv that is not yet supported should be
        # clarified instead of receiving an incorrect answer.
        if is_employee_dataset_question(question):
            return {
                "answer": (
                    "I could not safely interpret that employee-data question "
                    "from the full dataset, so I have not guessed. Please "
                    "rephrase it using fields such as city, gender, education, "
                    "age, payment tier, joining year, experience, benched, "
                    "or leave status."
                ),
                "contexts": [],
                "sources": ["Employee.csv"],
                "total_records": len(employee_df),
                "answer_type": "dataset_question_needs_clarification",
            }

        # 5. Use RAG only for unstructured, non-dataset questions.
        top_k = max(1, min(req.top_k, 20))

        query_vector = embed_texts(
            [question],
            task_type="RETRIEVAL_QUERY",
        )[0]

        found = QdrantStorage().search(
            query_vector=query_vector,
            top_k=top_k,
        )

        contexts = list(found.get("contexts", []))
        sources = list(found.get("sources", []))

        if not contexts:
            return {
                "answer": "The information is not available.",
                "contexts": [],
                "sources": [],
            }

        # 4. Generate the answer using your existing Ollama client
        answer = await run_in_threadpool(
            generate_answer,
            question,
            "\n\n".join(contexts),
        )

        return {
            "answer": answer,
            "contexts": contexts,
            "sources": sources,
            "answer_type": "rag",
        }

    except HTTPException:
        # Preserve intentional HTTP errors
        raise

    except Exception:
        # Print the complete traceback in the Uvicorn terminal
        logging.exception("Error inside /api/ask")

        raise HTTPException(
            status_code=500,
            detail="Internal server error. Check the backend terminal.",
        )



# ============================================================
# SERVE THE FRONTEND AT http://127.0.0.1:8000/app/
# ============================================================

_here = Path(__file__).parent

for _candidate in (_here / "frontend", _here.parent / "frontend"):
    if _candidate.exists():
        app.mount(
            "/app",
            StaticFiles(directory=str(_candidate), html=True),
            name="frontend",
        )
        break


# ============================================================
# INNGEST ENDPOINT
# ============================================================

inngest.fast_api.serve(
    app,
    inngest_client,
    [
        rag_ingest_employee_csv,
        rag_query_employee_data,
    ],
)
