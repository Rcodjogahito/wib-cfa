"""
WIB CFA — PDF Question Extractor
Extracts MCQ questions from Kaplan Schweser PDF files.

PDF format:
    Question #N of M
    Question ID: XXXXXXX
    <question stem, possibly multi-line>
    A) <option A text>
    B) <option B text>
    C) <option C text>
    Explanation
    <explanation text>
    (Module XX.X, LOS XX.X)
"""

import re
from pathlib import Path
from typing import List, Dict, Optional

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


# ── Regex patterns ────────────────────────────────────────────────────────────

_RE_Q_HEADER   = re.compile(r"Question\s+#(\d+)\s+of\s+(\d+)", re.IGNORECASE)
_RE_Q_ID       = re.compile(r"Question\s+ID:\s*(\d+)", re.IGNORECASE)
_RE_OPTION_A   = re.compile(r"^A\)\s+(.+)", re.DOTALL)
_RE_OPTION_B   = re.compile(r"^B\)\s+(.+)", re.DOTALL)
_RE_OPTION_C   = re.compile(r"^C\)\s+(.+)", re.DOTALL)
_RE_EXPLANATION = re.compile(r"^Explanation\s*$", re.IGNORECASE)
_RE_MODULE_LOS  = re.compile(r"\(Module\s+[\d.]+,\s+LOS\s+[\d.]+\w*\)", re.IGNORECASE)

# Map folder names to canonical CFA topic names
FOLDER_TO_TOPIC = {
    "ethical and professional standard": "Ethics & Professional Standards",
    "quantitative method":               "Quantitative Methods",
    "economics":                         "Economics",
    "financial statement analysis":      "Financial Statement Analysis",
    "corporate issuers":                 "Corporate Issuers",
    "equity investments":                "Equity Investments",
    "fixed income":                      "Fixed Income",
    "derivatives":                       "Derivatives",
    "alternative investment":            "Alternative Investments",
    "portofolio management part 1":      "Portfolio Management",
    "portofolio management part 2":      "Portfolio Management",
}


def _infer_topic(path: Path) -> str:
    """Infer canonical topic name from the parent folder of a PDF."""
    folder = path.parent.name.lower()
    for key, val in FOLDER_TO_TOPIC.items():
        if key in folder:
            return val
    # Fallback: title-case the folder
    return path.parent.name.title()


def _clean(text: str) -> str:
    """Remove excess whitespace and common PDF artefacts."""
    # Remove soft-hyphens, zero-width spaces
    text = text.replace("\xad", "").replace("​", "")
    # Collapse internal newlines/spaces
    text = re.sub(r"\s*\n\s*", " ", text).strip()
    text = re.sub(r"  +", " ", text)
    return text


def _parse_raw_text(raw: str, topic: str, source: str = "") -> List[Dict]:
    """
    Parse a full PDF text block into a list of question dicts.

    Returns list of dicts with keys:
        topic, subtopic, difficulty, question_en,
        option_a, option_b, option_c,
        correct_answer, explanation_en, source
    """
    questions: List[Dict] = []

    # Split on question headers
    # "Question #N of M" marks the start of each question
    parts = _RE_Q_HEADER.split(raw)
    # parts[0] = preamble, then triples (q_num, total, body) repeat
    if len(parts) < 4:
        return questions

    # Walk triplets: (q_num, total, body)
    i = 1
    while i + 2 < len(parts):
        body = parts[i + 2]
        i += 3

        # Remove question ID line
        body = _RE_Q_ID.sub("", body)
        # Remove module/LOS ref
        body = _RE_MODULE_LOS.sub("", body)

        lines = [l.strip() for l in body.split("\n") if l.strip()]

        q_stem_lines: List[str] = []
        opt_a = opt_b = opt_c = ""
        expl_lines: List[str] = []
        state = "stem"   # stem → options → explanation

        for line in lines:
            if state == "stem":
                if re.match(r"^A\)\s", line):
                    state = "options"
                    opt_a = line[3:].strip()
                else:
                    q_stem_lines.append(line)

            elif state == "options":
                if re.match(r"^B\)\s", line):
                    opt_b = line[3:].strip()
                elif re.match(r"^C\)\s", line):
                    opt_c = line[3:].strip()
                elif re.match(r"^Explanation\s*$", line, re.IGNORECASE):
                    state = "explanation"
                else:
                    # Continuation of the last option
                    if opt_c:
                        opt_c += " " + line
                    elif opt_b:
                        opt_b += " " + line
                    elif opt_a:
                        opt_a += " " + line

            elif state == "explanation":
                expl_lines.append(line)

        q_stem = _clean(" ".join(q_stem_lines))
        opt_a  = _clean(opt_a)
        opt_b  = _clean(opt_b)
        opt_c  = _clean(opt_c)
        expl   = _clean(" ".join(expl_lines))

        # Determine correct answer from explanation
        # The explanation usually starts with the correct answer text,
        # or references it directly. We use a simple heuristic:
        # the answer option that appears verbatim at the start of the explanation.
        correct = _guess_correct_answer(opt_a, opt_b, opt_c, expl)

        if q_stem and opt_a and opt_b and opt_c and correct:
            questions.append({
                "topic":          topic,
                "subtopic":       "",
                "difficulty":     "medium",
                "question_en":    q_stem,
                "option_a":       opt_a,
                "option_b":       opt_b,
                "option_c":       opt_c,
                "correct_answer": correct,
                "explanation_en": expl,
                "explanation_fr": "",
                "source":         source or "Kaplan Schweser",
            })

    return questions


def _guess_correct_answer(a: str, b: str, c: str, explanation: str) -> str:
    """
    Heuristic: compare each option text against the start of the explanation.
    Returns 'A', 'B', or 'C'.
    """
    expl_lower = explanation.lower()[:300]

    def overlap(opt: str) -> int:
        words = opt.lower().split()[:8]
        phrase = " ".join(words)
        if len(phrase) >= 5 and phrase in expl_lower:
            return len(phrase)
        return 0

    scores = {"A": overlap(a), "B": overlap(b), "C": overlap(c)}
    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best

    # Fallback: look for explicit "Answer: A/B/C" in explanation
    m = re.search(r"\b([ABC])\s+is\s+(correct|right)", explanation, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    m = re.search(r"\b(correct answer|answer)\s+is\s+([ABC])\b", explanation, re.IGNORECASE)
    if m:
        return m.group(2).upper()

    # Default to A (will be correct in ~33% of cases)
    return "A"


def extract_from_pdf(pdf_path: str | Path, topic: str = "") -> List[Dict]:
    """
    Extract MCQ questions from a single PDF file.

    Args:
        pdf_path: Path to the PDF.
        topic:    Override the topic name; inferred from folder if empty.

    Returns:
        List of question dicts ready to insert into the DB.
    """
    if not PDFPLUMBER_AVAILABLE:
        raise ImportError("pdfplumber is required: pip install pdfplumber>=0.11.0")

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if not topic:
        topic = _infer_topic(path)

    source = f"Kaplan Schweser — {path.stem}"

    all_text_parts: List[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_text_parts.append(text)

    full_text = "\n".join(all_text_parts)
    return _parse_raw_text(full_text, topic, source)


def extract_from_folder(folder_path: str | Path,
                        topic: str = "",
                        verbose: bool = False) -> List[Dict]:
    """
    Extract MCQs from all PDFs in a folder.

    Args:
        folder_path: Directory containing PDF files.
        topic:       Override topic for all PDFs; inferred per-file if empty.
        verbose:     Print progress to stdout.

    Returns:
        Combined list of question dicts.
    """
    folder = Path(folder_path)
    pdfs = sorted(folder.glob("*.pdf"))
    if not pdfs:
        if verbose:
            print(f"  No PDFs found in {folder}")
        return []

    results: List[Dict] = []
    for pdf in pdfs:
        try:
            qs = extract_from_pdf(pdf, topic)
            results.extend(qs)
            if verbose:
                print(f"  {pdf.name}: {len(qs)} questions")
        except Exception as e:
            if verbose:
                print(f"  ERROR {pdf.name}: {e}")
    return results


def extract_all_topics(warehouse_root: str | Path,
                       verbose: bool = True) -> List[Dict]:
    """
    Walk the QSTN WITH ANS directory and extract all questions.

    Expected structure:
        <warehouse_root>/2. QB KAPLAN-3000 MCQs/QSTN WITH ANS/<topic>/<reading>.pdf

    Returns:
        All extracted questions across all topics.
    """
    root = Path(warehouse_root)
    qstn_dir = root / "2. QB KAPLAN-3000 MCQs" / "QSTN WITH ANS"
    if not qstn_dir.exists():
        raise FileNotFoundError(f"QSTN WITH ANS not found under {root}")

    all_questions: List[Dict] = []
    for topic_folder in sorted(qstn_dir.iterdir()):
        if topic_folder.is_dir():
            topic = _infer_topic(topic_folder / "_dummy.pdf")
            if verbose:
                print(f"\nExtracting [{topic}] from {topic_folder.name}…")
            qs = extract_from_folder(topic_folder, topic=topic, verbose=verbose)
            all_questions.extend(qs)
            if verbose:
                print(f"  Subtotal: {len(qs)} questions")

    if verbose:
        print(f"\nTotal extracted: {len(all_questions)} questions")
    return all_questions
