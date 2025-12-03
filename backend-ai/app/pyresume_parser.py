import json
from datetime import datetime
import math
from dateutil import parser as dateparser
import re

try:
    # The PyPI package `leverparser` exposes the module `pyresume`.
    # Import the runtime symbol from the actual top-level module.
    from pyresume import ResumeParser
except Exception as exc:  # pragma: no cover - runtime dependency
    _lever_import_exc = exc

    def parse_resume_file(file_bytes: bytes, _import_exc=_lever_import_exc) -> dict:
        raise ImportError(
            "Missing dependency 'leverparser' (provides module 'pyresume'). "
            "Install it with: `pip install leverparser` and restart the server. "
            "Original error: %s" % (_import_exc,)
        ) from _import_exc
else:
    # Initialize parser as singleton to reuse across calls
    parser = ResumeParser()

    def parse_resume_file(file_bytes: bytes, filename: str | None = None) -> dict:
        try:
            text = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            text = ""

        # If the input looks like a PDF or DOCX, extract text using a
        # dedicated extractor before handing to the resume parser. This
        # reduces garbage coming from binary PDF streams.
        try:
            import io
            import re
            _fn = (filename or "").lower()

            def _clean_text(s: str) -> str:
                if not s:
                    return ""
                # remove null bytes and long runs of control chars
                s = s.replace("\x00", " ")
                s = re.sub(r"[\r\t]+", " ", s)
                # collapse multiple newlines/spaces
                s = re.sub(r"\n{3,}", "\n\n", s)
                s = re.sub(r"[ ]{2,}", " ", s)
                return s.strip()

            # Heuristics for PDF
            is_pdf = _fn.endswith(".pdf") or file_bytes[:4] == b"%PDF"
            if is_pdf:
                try:
                    import pdfplumber

                    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                        pages = [p.extract_text() or "" for p in pdf.pages]
                    text = "\n\n".join(pages)
                    text = _clean_text(text)
                except Exception:
                    # Fall back to the original decode if pdfplumber fails
                    pass

            # Heuristics for DOCX (PK zip header + `.docx` extension)
            elif _fn.endswith(".docx") or file_bytes[:2] == b"PK":
                try:
                    from io import BytesIO
                    from docx import Document

                    doc = Document(BytesIO(file_bytes))
                    paras = [p.text for p in doc.paragraphs]
                    text = "\n\n".join(paras)
                    text = _clean_text(text)
                except Exception:
                    # Fall back to decode if python-docx fails
                    pass

        except Exception:
            # keep original text on any unexpected failure during extraction
            pass

        # Parse using leverparser/pyresume's parse_text API (handles raw text)
        resume_result = parser.parse_text(text)

        # Convert to dict or extract fields you need
        name = getattr(resume_result.contact_info, "name", None)
        email = getattr(resume_result.contact_info, "email", None)
        phone = getattr(resume_result.contact_info, "phone", None)
        location = getattr(resume_result.contact_info, "location", None)
        summary_text = getattr(resume_result, "summary", "")
        skills = [getattr(skill, "name", None) for skill in getattr(resume_result, "skills", [])]

        # Helper: parse date strings or date objects into datetime
        def _parse_date(d):
            if not d:
                return None
            if isinstance(d, (datetime,)):
                return d
            try:
                # some date objects may be 'date' not datetime
                return dateparser.parse(str(d))
            except Exception:
                return None

        # Build experience entries with computed durations
        experience_entries = []
        total_experience_days = 0
        for Job in getattr(resume_result, "experience", []):
            title = getattr(Job, "title", None)
            company = getattr(Job, "company", None)
            start_raw = getattr(Job, "start_date", None)
            end_raw = getattr(Job, "end_date", None)
            description = getattr(Job, "description", None)
            location_job = getattr(Job, "location", None)

            start_dt = _parse_date(start_raw)
            end_dt = _parse_date(end_raw) or datetime.utcnow()

            duration_days = None
            duration_years = None
            duration_str = None
            if start_dt and end_dt:
                try:
                    duration = end_dt - start_dt
                    duration_days = max(0, duration.days)
                    duration_years = duration_days / 365.25
                    # human friendly duration e.g., '2y 3m'
                    yrs = int(duration_days // 365)
                    months = int((duration_days % 365) // 30)
                    if yrs > 0:
                        duration_str = f"{yrs}y{(' ' + str(months) + 'm') if months>0 else ''}"
                    elif months > 0:
                        duration_str = f"{months}m"
                    else:
                        duration_str = f"{max(1, int(duration_days))}d"
                except Exception:
                    duration_days = None

            if duration_days:
                total_experience_days += duration_days

            experience_entries.append({
                "title": title,
                "position": title,
                "company": company,
                "start_date": start_raw,
                "end_date": end_raw,
                "location": location_job,
                "description": description,
                "duration_days": duration_days,
                "duration_years": duration_years,
                "duration_str": duration_str,
            })

        # Compute total experience in years (rounded down) and present as 'X+ years'
        total_years = total_experience_days / 365.25 if total_experience_days > 0 else 0
        total_years_rounded = int(math.floor(total_years))
        total_experience_summary = (f"{total_years_rounded}+ years" if total_years_rounded > 0 else "<1 year")

        # Derive headline / primary title: prefer contact_info.title, most recent experience title, or keywords from summary/skills
        primary_title = None
        primary_title = getattr(resume_result.contact_info, "title", None) or primary_title
        if not primary_title and experience_entries:
            # pick most recent entry with start date or first entry
            def _entry_sort_key(e):
                sd = _parse_date(e.get("start_date"))
                return sd or datetime.min

            try:
                most_recent = sorted(getattr(resume_result, "experience", []), key=lambda j: _parse_date(getattr(j, "start_date", None)) or datetime.min, reverse=True)[0]
                primary_title = getattr(most_recent, "title", None) or primary_title
            except Exception:
                primary_title = primary_title

        # Keyword heuristics for headline from skills/summary
        headline = primary_title or (summary_text.split("\n")[0] if summary_text else None)
        if not headline:
            text_pool = " ".join(filter(None, [summary_text, " ".join(filter(None, skills))]))
            text_pool_low = (text_pool or "").lower()
            if re.search(r"full[ -]?stack|frontend|backend", text_pool_low):
                headline = "Full Stack Developer"
            elif re.search(r"machine ?learning|ml|deep learning|ai|artificial intelligence|data scientist", text_pool_low):
                headline = "AI / ML Engineer"
            elif re.search(r"data engineer|etl|spark|hadoop", text_pool_low):
                headline = "Data Engineer"
            elif re.search(r"devops|site reliability|sre|ci/cd", text_pool_low):
                headline = "DevOps Engineer"
            elif re.search(r"mobile|android|ios", text_pool_low):
                headline = "Mobile Developer"

        # Fallback location from experience if contact_info missing
        if not location:
            for e in experience_entries:
                if e.get("location"):
                    location = e.get("location")
                    break

        result = {
            "name": name,
            "email": email,
            "phone": phone,
            "headline": headline,
            "primary_title": primary_title,
            "total_experience": total_experience_summary,
            "total_experience_years": total_years,
            "location": location,
            "summary": summary_text,
            "skills": skills,
            "experience": experience_entries,
            "education": [
                {
                    "degree": getattr(Edu, "degree", None),
                    "institution": getattr(Edu, "institution", None),
                    "start_date": getattr(Edu, "start_date", None),
                    "end_date": getattr(Edu, "end_date", None),
                }
                for Edu in getattr(resume_result, "education", [])
            ],
        }

        # Print the parsed result so calling code (or logs) can inspect it
        try:
            print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
        except Exception:
            # Fallback to plain print if JSON serialization fails
            print(result)

        return result
