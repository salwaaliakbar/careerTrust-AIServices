# import json
# import math
# import re
# from datetime import datetime
# from dateutil import parser as dateparser

# # -------------------------------------------------------------------
# # Dependency handling
# # -------------------------------------------------------------------
# try:
#     from pyresume import ResumeParser
# except Exception as exc:  # pragma: no cover
#     _lever_import_exc = exc

#     def parse_resume_file(file_bytes: bytes, *_args, **_kwargs) -> dict:
#         raise ImportError(
#             "Missing dependency 'leverparser' (provides module 'pyresume'). "
#             "Install it with: `pip install leverparser`. "
#             f"Original error: {_lever_import_exc}"
#         ) from _lever_import_exc
# else:
#     parser = ResumeParser()

# # -------------------------------------------------------------------
# # Helpers
# # -------------------------------------------------------------------
# def _clean_text(text: str) -> str:
#     if not text:
#         return ""
#     text = text.replace("\x00", " ")
#     text = re.sub(r"[\r\t]+", " ", text)
#     text = re.sub(r"\n{3,}", "\n\n", text)
#     text = re.sub(r"[ ]{2,}", " ", text)
#     return text.strip()


# def _parse_date(value):
#     if not value:
#         return None
#     if isinstance(value, datetime):
#         return value
#     try:
#         return dateparser.parse(str(value))
#     except Exception:
#         return None


# def _extract_text(file_bytes: bytes, filename: str | None) -> str:
#     try:
#         text = file_bytes.decode("utf-8", errors="ignore")
#     except Exception:
#         text = ""

#     filename = (filename or "").lower()

#     try:
#         import io

#         # PDF
#         if filename.endswith(".pdf") or file_bytes[:4] == b"%PDF":
#             try:
#                 import pdfplumber

#                 with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
#                     pages = [page.extract_text() or "" for page in pdf.pages]
#                 return _clean_text("\n\n".join(pages))
#             except Exception:
#                 return text

#         # DOCX
#         if filename.endswith(".docx") or file_bytes[:2] == b"PK":
#             try:
#                 from io import BytesIO
#                 from docx import Document

#                 doc = Document(BytesIO(file_bytes))
#                 paragraphs = [p.text for p in doc.paragraphs]
#                 return _clean_text("\n\n".join(paragraphs))
#             except Exception:
#                 return text

#     except Exception:
#         pass

#     return _clean_text(text)


# # -------------------------------------------------------------------
# # Main parser
# # -------------------------------------------------------------------
# def parse_resume_file(file_bytes: bytes, fullName: str | None = None, email: str | None = None, filename: str | None = None) -> dict:
#     text = _extract_text(file_bytes, filename)
#     print("Extracted text:", text)
#     resume = parser.parse_text(text)

#     print("Parsed resume object:", resume)

#     contact = resume.contact_info

#     if(fullName != getattr(contact, "name", None) and fullName is not None):
#         return "Sorry! our system can't autofill the profile because name doesn't match with your account. It may not be your resume."

#     if(email != getattr(contact, "email", None) and email is not None):
#         return "Sorry! our system can't autofill the profile because email doesn't match with your account. It may not be your resume." 

#     name = getattr(contact, "name", None)
#     email = getattr(contact, "email", None)
#     phone = getattr(contact, "phone", None)
#     location = getattr(contact, "location", None)
#     summary = getattr(resume, "summary", "")
#     skills = [getattr(s, "name", None) for s in getattr(resume, "skills", [])]

#     # ---------------------------------------------------------------
#     # Experience processing
#     # ---------------------------------------------------------------
#     experience_entries = []
#     total_days = 0

#     for job in getattr(resume, "experience", []):
#         start_dt = _parse_date(getattr(job, "start_date", None))
#         end_dt = _parse_date(getattr(job, "end_date", None)) or datetime.utcnow()

#         duration_days = duration_years = duration_str = None

#         if start_dt and end_dt:
#             delta_days = max(0, (end_dt - start_dt).days)
#             duration_days = delta_days
#             duration_years = delta_days / 365.25

#             years = delta_days // 365
#             months = (delta_days % 365) // 30

#             if years > 0:
#                 duration_str = f"{years}y{f' {months}m' if months else ''}"
#             elif months > 0:
#                 duration_str = f"{months}m"
#             else:
#                 duration_str = f"{max(1, delta_days)}d"

#             total_days += delta_days

#         experience_entries.append({
#             "title": getattr(job, "title", None),
#             "position": getattr(job, "title", None),
#             "company": getattr(job, "company", None),
#             "start_date": getattr(job, "start_date", None),
#             "end_date": getattr(job, "end_date", None),
#             "location": getattr(job, "location", None),
#             "description": getattr(job, "description", None),
#             "duration_days": duration_days,
#             "duration_years": duration_years,
#             "duration_str": duration_str,
#         })

#     total_years = total_days / 365.25 if total_days else 0
#     total_experience = (
#         f"{int(math.floor(total_years))}+ years"
#         if total_years >= 1 else "<1 year"
#     )

#     # ---------------------------------------------------------------
#     # Headline inference
#     # ---------------------------------------------------------------
#     primary_title = getattr(contact, "title", None)

#     if not primary_title and experience_entries:
#         try:
#             most_recent = sorted(
#                 resume.experience,
#                 key=lambda j: _parse_date(getattr(j, "start_date", None)) or datetime.min,
#                 reverse=True
#             )[0]
#             primary_title = getattr(most_recent, "title", None)
#         except Exception:
#             pass

#     headline = primary_title or (summary.split("\n")[0] if summary else None)

#     if not headline:
#         pool = " ".join(filter(None, [summary, " ".join(filter(None, skills))])).lower()

#         if re.search(r"full[ -]?stack|frontend|backend", pool):
#             headline = "Full Stack Developer"
#         elif re.search(r"machine ?learning|ml|deep learning|ai|data scientist", pool):
#             headline = "AI / ML Engineer"
#         elif re.search(r"data engineer|etl|spark|hadoop", pool):
#             headline = "Data Engineer"
#         elif re.search(r"devops|sre|ci/cd", pool):
#             headline = "DevOps Engineer"
#         elif re.search(r"mobile|android|ios", pool):
#             headline = "Mobile Developer"

#     # ---------------------------------------------------------------
#     # Location fallback
#     # ---------------------------------------------------------------
#     if not location:
#         for exp in experience_entries:
#             if exp.get("location"):
#                 location = exp["location"]
#                 break

#     result = {
#         "name": name,
#         "email": email,
#         "phone": phone,
#         "headline": headline,
#         "primary_title": primary_title,
#         "total_experience": total_experience,
#         "total_experience_years": total_years,
#         "location": location,
#         "summary": summary,
#         "skills": skills,
#         "experience": experience_entries,
#         "education": [
#             {
#                 "degree": getattr(e, "degree", None),
#                 "institution": getattr(e, "institution", None),
#                 "start_date": getattr(e, "start_date", None),
#                 "end_date": getattr(e, "end_date", None),
#             }
#             for e in getattr(resume, "education", [])
#         ],
#     }

#     try:
#         print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
#     except Exception:
#         print(result)

#     return result


import json
import math
import re
from datetime import datetime
from dateutil import parser as dateparser

import spacy
from spacy.matcher import PhraseMatcher

# ---------------------------
# Load spaCy transformer model
# ---------------------------
nlp = spacy.load("en_core_web_trf")

# ---------------------------
# Regex helpers
# ---------------------------
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"\+?\d[\d\-\s]{7,}\d")

# ---------------------------
# Skill matcher (extend with more skills as needed)
# ---------------------------
SKILLS_LIST = [
    "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "php", "go", "rust",
    "sql", "nosql", "mongodb", "postgresql", "mysql", "redis",
    "machine learning", "deep learning", "ai", "artificial intelligence",
    "nlp", "natural language processing", "computer vision",
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "jenkins",
    "react", "angular", "vue", "node.js", "express", "django", "flask", "spring",
    "git", "agile", "scrum", "devops", "ci/cd", "terraform", "ansible"
]

skill_matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
skill_patterns = [nlp.make_doc(skill) for skill in SKILLS_LIST]
skill_matcher.add("SKILL", skill_patterns)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[\r\t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    return text.strip()


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return dateparser.parse(str(value))
    except Exception:
        return None


def _extract_text(file_bytes: bytes, filename: str | None) -> str:
    try:
        text = file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        text = ""

    filename = (filename or "").lower()

    try:
        import io

        # PDF
        if filename.endswith(".pdf") or file_bytes[:4] == b"%PDF":
            try:
                import pdfplumber

                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    pages = [page.extract_text() or "" for page in pdf.pages]
                return _clean_text("\n\n".join(pages))
            except Exception:
                return text

        # DOCX
        if filename.endswith(".docx") or file_bytes[:2] == b"PK":
            try:
                from io import BytesIO
                from docx import Document

                doc = Document(BytesIO(file_bytes))
                paragraphs = [p.text for p in doc.paragraphs]
                return _clean_text("\n\n".join(paragraphs))
            except Exception:
                return text

    except Exception:
        pass

    return _clean_text(text)


# -------------------------------------------------------------------
# Main parser using spaCy NER
# -------------------------------------------------------------------
def parse_resume_file(file_bytes: bytes, fullName: str | None = None, email: str | None = None, filename: str | None = None) -> dict:
    text = _extract_text(file_bytes, filename)
    print("Extracted text:", text)  # Print first 500 chars
    
    # Process with spaCy
    doc = nlp(text)
    
    # -------- Extract contact information --------
    extracted_email = EMAIL_REGEX.search(text)
    extracted_email = extracted_email.group(0) if extracted_email else None
    
    phone = PHONE_REGEX.search(text)
    phone = phone.group(0) if phone else None
    
    # Extract name from first PERSON entity
    extracted_name = None
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            extracted_name = ent.text
            break
    
    # Extract location from GPE entities
    location = None
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"]:
            location = ent.text
            break
    
    # Validate name and email if provided
    if fullName and extracted_name and fullName.lower() != extracted_name.lower():
        return {"error": "Sorry! our system can't autofill the profile because name doesn't match with your account. It may not be your resume."}
    
    if email and extracted_email and email.lower() != extracted_email.lower():
        return {"error": "Sorry! our system can't autofill the profile because email doesn't match with your account. It may not be your resume."}
    
    name = extracted_name
    email_result = extracted_email
    
    # -------- Extract summary (first few lines or sentences) --------
    lines = text.split("\n")
    summary = ""
    for i, line in enumerate(lines[:10]):  # Check first 10 lines
        if len(line.strip()) > 50 and not EMAIL_REGEX.search(line) and not PHONE_REGEX.search(line):
            summary = line.strip()
            break
    
    # -------- Extract skills using PhraseMatcher --------
    skills = set()
    matches = skill_matcher(doc)
    for _, start, end in matches:
        skills.add(doc[start:end].text)
    
    # Also extract skills from common sections
    skill_section_pattern = re.compile(r"(?:skills?|technologies?|expertise)[\s:]+([^\n]+(?:\n(?!\n)[^\n]+)*)", re.IGNORECASE)
    skill_sections = skill_section_pattern.findall(text)
    for section in skill_sections:
        # Split by common delimiters
        skill_items = re.split(r"[,;|•·]", section)
        for item in skill_items:
            cleaned = item.strip()
            if len(cleaned) > 1 and len(cleaned) < 50:
                skills.add(cleaned)
    
    skills_list = [s for s in skills if s]
    
    # ---------------------------------------------------------------
    # Experience processing using spaCy NER
    # ---------------------------------------------------------------
    experience_entries = []
    total_days = 0
    
    # Split text into sections (simple heuristic)
    exp_pattern = re.compile(r"(?:experience|work history|employment|professional experience)", re.IGNORECASE)
    exp_match = exp_pattern.search(text)
    
    if exp_match:
        exp_text = text[exp_match.start():]
        # Look for education section to limit experience section
        edu_pattern = re.compile(r"(?:education|academic|qualifications)", re.IGNORECASE)
        edu_match = edu_pattern.search(exp_text)
        if edu_match:
            exp_text = exp_text[:edu_match.start()]
        
        # Process experience section
        exp_doc = nlp(exp_text)
        
        # Extract organizations and dates
        current_entry = {}
        for sent in exp_doc.sents:
            sent_text = sent.text.strip()
            if len(sent_text) < 10:
                continue
            
            # Look for job titles, companies, dates
            orgs = [ent.text for ent in sent.ents if ent.label_ == "ORG"]
            dates = [ent.text for ent in sent.ents if ent.label_ == "DATE"]
            
            if orgs or dates:
                if current_entry.get("description"):
                    # Parse dates from previous entry
                    start_dt = _parse_date(current_entry.get("start_date"))
                    end_dt = _parse_date(current_entry.get("end_date")) or datetime.utcnow()
                    
                    duration_days = duration_years = duration_str = None
                    
                    if start_dt and end_dt:
                        delta_days = max(0, (end_dt - start_dt).days)
                        duration_days = delta_days
                        duration_years = delta_days / 365.25
                        
                        years = delta_days // 365
                        months = (delta_days % 365) // 30
                        
                        if years > 0:
                            duration_str = f"{years}y{f' {months}m' if months else ''}"
                        elif months > 0:
                            duration_str = f"{months}m"
                        else:
                            duration_str = f"{max(1, delta_days)}d"
                        
                        total_days += delta_days
                    
                    experience_entries.append({
                        "title": current_entry.get("title"),
                        "position": current_entry.get("title"),
                        "company": current_entry.get("company"),
                        "start_date": current_entry.get("start_date"),
                        "end_date": current_entry.get("end_date"),
                        "location": current_entry.get("location"),
                        "description": current_entry.get("description"),
                        "duration_days": duration_days,
                        "duration_years": duration_years,
                        "duration_str": duration_str,
                    })
                
                # Start new entry
                current_entry = {
                    "title": sent_text.split("\n")[0][:100],  # First line as title
                    "company": orgs[0] if orgs else None,
                    "start_date": dates[0] if len(dates) > 0 else None,
                    "end_date": dates[1] if len(dates) > 1 else None,
                    "location": None,
                    "description": sent_text
                }
                
                # Look for location
                locs = [ent.text for ent in sent.ents if ent.label_ in ["GPE", "LOC"]]
                if locs:
                    current_entry["location"] = locs[0]
        
        # Add last entry
        if current_entry.get("description"):
            start_dt = _parse_date(current_entry.get("start_date"))
            end_dt = _parse_date(current_entry.get("end_date")) or datetime.utcnow()
            
            duration_days = duration_years = duration_str = None
            
            if start_dt and end_dt:
                delta_days = max(0, (end_dt - start_dt).days)
                duration_days = delta_days
                duration_years = delta_days / 365.25
                
                years = delta_days // 365
                months = (delta_days % 365) // 30
                
                if years > 0:
                    duration_str = f"{years}y{f' {months}m' if months else ''}"
                elif months > 0:
                    duration_str = f"{months}m"
                else:
                    duration_str = f"{max(1, delta_days)}d"
                
                total_days += delta_days
            
            experience_entries.append({
                "title": current_entry.get("title"),
                "position": current_entry.get("title"),
                "company": current_entry.get("company"),
                "start_date": current_entry.get("start_date"),
                "end_date": current_entry.get("end_date"),
                "location": current_entry.get("location"),
                "description": current_entry.get("description"),
                "duration_days": duration_days,
                "duration_years": duration_years,
                "duration_str": duration_str,
            })
    
    total_years = total_days / 365.25 if total_days else 0
    total_experience = (
        f"{int(math.floor(total_years))}+ years"
        if total_years >= 1 else "<1 year"
    )
    
    # ---------------------------------------------------------------
    # Headline inference
    # ---------------------------------------------------------------
    primary_title = None
    
    if experience_entries:
        # Get most recent job title
        for entry in experience_entries:
            if entry.get("title"):
                primary_title = entry["title"]
                break
    
    headline = primary_title or (summary.split("\n")[0] if summary else None)
    
    if not headline:
        pool = " ".join(filter(None, [summary, " ".join(filter(None, skills_list))])).lower()
        
        if re.search(r"full[ -]?stack|frontend|backend", pool):
            headline = "Full Stack Developer"
        elif re.search(r"machine ?learning|ml|deep learning|ai|data scientist", pool):
            headline = "AI / ML Engineer"
        elif re.search(r"data engineer|etl|spark|hadoop", pool):
            headline = "Data Engineer"
        elif re.search(r"devops|sre|ci/cd", pool):
            headline = "DevOps Engineer"
        elif re.search(r"mobile|android|ios", pool):
            headline = "Mobile Developer"
    
    # ---------------------------------------------------------------
    # Location fallback
    # ---------------------------------------------------------------
    if not location:
        for exp in experience_entries:
            if exp.get("location"):
                location = exp["location"]
                break
    
    # ---------------------------------------------------------------
    # Education extraction
    # ---------------------------------------------------------------
    education_entries = []
    edu_pattern = re.compile(r"(?:education|academic|qualifications)", re.IGNORECASE)
    edu_match = edu_pattern.search(text)
    
    if edu_match:
        edu_text = text[edu_match.start():]
        # Limit to education section
        next_section = re.compile(r"(?:projects?|certifications?|awards?)", re.IGNORECASE)
        next_match = next_section.search(edu_text)
        if next_match:
            edu_text = edu_text[:next_match.start()]
        
        edu_doc = nlp(edu_text[:2000])  # Limit length
        
        for sent in edu_doc.sents:
            orgs = [ent.text for ent in sent.ents if ent.label_ == "ORG"]
            dates = [ent.text for ent in sent.ents if ent.label_ == "DATE"]
            
            if orgs or dates:
                degree_match = re.search(r"(bachelor|master|phd|b\.?s\.?|m\.?s\.?|b\.?tech|m\.?tech|diploma)", sent.text, re.IGNORECASE)
                degree = degree_match.group(0) if degree_match else None
                
                education_entries.append({
                    "degree": degree,
                    "institution": orgs[0] if orgs else None,
                    "start_date": dates[0] if len(dates) > 0 else None,
                    "end_date": dates[1] if len(dates) > 1 else (dates[0] if len(dates) == 1 else None),
                })
    
    result = {
        "name": name,
        "email": email_result,
        "phone": phone,
        "headline": headline,
        "primary_title": primary_title,
        "total_experience": total_experience,
        "total_experience_years": total_years,
        "location": location,
        "summary": summary,
        "skills": skills_list,
        "experience": experience_entries,
        "education": education_entries,
    }
    
    try:
        print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
    except Exception:
        print(result)
    
    return result

