# utils/ats_scanner.py - DETERMINISTIC ATS SCORING ENGINE
# Pure Python, zero API calls — simulates how real ATS software scores resumes
import re
import math
from collections import Counter


class ATSScanner:
    """
    Deterministic ATS scanner that scores resumes using rule-based checks,
    similar to tools like ATSFriendly and Jobscan.
    
    No AI calls — pure string analysis.
    """

    # Standard section headers that real ATS systems recognise
    STANDARD_SECTIONS = {
        "summary":        [r"\bsummary\b", r"\bprofessional\s+summary\b", r"\bobjective\b", r"\bprofile\b", r"\babout\s+me\b"],
        "experience":     [r"\bexperience\b", r"\bwork\s+experience\b", r"\bemployment\b", r"\bwork\s+history\b", r"\bprofessional\s+experience\b"],
        "education":      [r"\beducation\b", r"\bacademic\b", r"\bqualifications\b"],
        "skills":         [r"\bskills\b", r"\btechnical\s+skills\b", r"\bcore\s+competencies\b", r"\bcompetencies\b"],
        "projects":       [r"\bprojects\b", r"\bkey\s+projects\b", r"\bpersonal\s+projects\b"],
        "certifications": [r"\bcertification[s]?\b", r"\blicen[sc]e[s]?\b", r"\baccreditation[s]?\b"],
    }

    # Formatting red-flags that real ATS parsers choke on
    BAD_FORMAT_PATTERNS = [
        (r"[●▪▸►◆◇★☆✦✧⬥⬦⬧⬨]", "Uses non-standard bullet characters (use • or - instead)"),
        (r"\|.*\|.*\|", "Contains pipe-delimited tables (ATS may scramble columns)"),
        (r"[^\x00-\x7F]{3,}", "Contains blocks of non-ASCII/special characters"),
        (r"(?:^|\n)[A-Z\s]{30,}(?:\n|$)", "Excessive ALL-CAPS text (hard to parse)"),
        (r"(?:(?:https?://|www\.)\S+){4,}", "Too many raw URLs (use hyperlinked text instead)"),
    ]

    WEIGHTS = {
        "keyword":      0.35,
        "achievements": 0.20,
        "section":      0.15,
        "formatting":   0.15,
        "contact":      0.10,
        "length":       0.05,
    }

    # ── Public API ────────────────────────────────────────────────────────────

    def scan(self, resume_text: str, job_description: str, job_title: str, file_checks: dict = None) -> dict:
        """
        Run all deterministic checks and return a comprehensive result dict.
        
        Args:
            file_checks: optional dict from resume_parser with file-structure info
                         (page_count, has_images, has_tables, is_machine_readable, issues)
        """
        resume_text = resume_text.strip()
        job_description = (job_description or "").strip()
        job_title = (job_title or "").strip()

        section_result      = self._check_sections(resume_text)
        keyword_result      = self._check_keywords(resume_text, job_description, job_title)
        formatting_result   = self._check_formatting(resume_text)
        achievements_result = self._check_achievements(resume_text)
        length_result       = self._check_length(resume_text)
        contact_result      = self._check_contact(resume_text)

        # Merge file-structure issues into formatting if a file was uploaded
        file_issues = []
        if file_checks:
            file_issues = file_checks.get("issues", [])
            if file_issues:
                formatting_result["issues"].extend(file_issues)
                # Deduct points for each file-structure issue
                deduction = len(file_issues) * 10
                formatting_result["score"] = max(0, formatting_result["score"] - deduction)
            
            # Critical: if PDF is not machine-readable, it's a hard fail on formatting
            if not file_checks.get("is_machine_readable", True):
                formatting_result["score"] = max(0, formatting_result["score"] - 40)

        # Weighted overall score
        overall = (
            section_result["score"]      * self.WEIGHTS["section"]
            + keyword_result["score"]    * self.WEIGHTS["keyword"]
            + formatting_result["score"] * self.WEIGHTS["formatting"]
            + achievements_result["score"] * self.WEIGHTS["achievements"]
            + length_result["score"]     * self.WEIGHTS["length"]
            + contact_result["score"]    * self.WEIGHTS["contact"]
        )
        overall = int(round(overall))

        return {
            "overall_score":       overall,
            "section_score":       section_result["score"],
            "keyword_score":       keyword_result["score"],
            "formatting_score":    formatting_result["score"],
            "achievements_score":  achievements_result["score"],
            "length_score":        length_result["score"],
            "contact_score":       contact_result["score"],
            # Details
            "matched_keywords":    keyword_result["matched"],
            "missing_keywords":    keyword_result["missing"],
            "keyword_density":     keyword_result["density"],
            "detected_sections":   section_result["detected"],
            "missing_sections":    section_result["missing"],
            "formatting_issues":   formatting_result["issues"],
            "achievements_found":  achievements_result["found"],
            "word_count":          length_result["word_count"],
            "contact_info":        contact_result["details"],
            "length_feedback":     length_result["feedback"],
            # File structure (only present if a file was uploaded)
            "file_checks":         file_checks,
        }

    # ── Section Detection (20%) ───────────────────────────────────────────────

    def _check_sections(self, resume_text: str) -> dict:
        text_lower = resume_text.lower()
        detected = []
        missing = []

        for section_name, patterns in self.STANDARD_SECTIONS.items():
            found = False
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    found = True
                    break
            if found:
                detected.append(section_name.title())
            else:
                missing.append(section_name.title())

        # Core sections (experience, education, skills) matter most
        core = {"Experience", "Education", "Skills"}
        core_found = len(core & set(detected))
        core_total = len(core)

        # Score: 60% weight on core sections, 40% on all sections
        all_ratio = len(detected) / len(self.STANDARD_SECTIONS) if self.STANDARD_SECTIONS else 0
        core_ratio = core_found / core_total if core_total else 0
        score = int(round(core_ratio * 60 + all_ratio * 40))

        return {"score": score, "detected": detected, "missing": missing}

    # ── Keyword Match (30%) ───────────────────────────────────────────────────

    def _check_keywords(self, resume_text: str, job_description: str, job_title: str) -> dict:
        if not job_description and not job_title:
            return {"score": 50, "matched": [], "missing": [], "density": 0.0}

        # Extract meaningful keywords from the job description
        jd_keywords = self._extract_keywords(job_description + " " + job_title)
        
        if not jd_keywords:
            return {"score": 50, "matched": [], "missing": [], "density": 0.0}

        resume_lower = resume_text.lower()
        resume_words = resume_lower.split()
        total_words = len(resume_words)

        matched = []
        missing = []
        match_count = 0

        for kw in jd_keywords:
            kw_lower = kw.lower()
            # Check for exact word/phrase match
            if re.search(r'\b' + re.escape(kw_lower) + r'\b', resume_lower):
                matched.append(kw)
                # Count occurrences for density
                match_count += len(re.findall(r'\b' + re.escape(kw_lower) + r'\b', resume_lower))
            else:
                missing.append(kw)

        # Keyword density (keyword occurrences / total words * 100)
        density = round((match_count / total_words * 100), 1) if total_words > 0 else 0.0

        # Keyword match percentage
        match_ratio = len(matched) / len(jd_keywords) if jd_keywords else 0

        # Score calculation
        score = int(round(match_ratio * 100))

        # Penalise keyword stuffing (density > 5%)
        if density > 5.0:
            score = max(0, score - 15)
        # Slight bonus for healthy density (1.5% - 4%)
        elif 1.5 <= density <= 4.0:
            score = min(100, score + 5)

        return {"score": score, "matched": matched, "missing": missing[:15], "density": density}

    # Stopwords for keyword extraction — common English filler words
    _STOPWORDS = frozenset(
        "a an the and or but is are was were be been being have has had do does did "
        "will would shall should can could may might must need ought to of in on at by "
        "for with from as into about between through during before after above below up "
        "down out off over under again further then once here there when where why how "
        "all each every both few more most other some such no nor not only own same so "
        "than too very it its you your yours he him his she her hers we us our they them "
        "their this that these those what which who whom whose if because since while "
        "until unless also just already still even much many well however although "
        "able also always any apply become company employee employer experience "
        "include including join looking make new opportunity position responsibilities "
        "role team work working years year required requirements strong preferred "
        "must equivalent across within etc per via using please note ideal candidate "
        "description overview duties qualifications benefits salary compensation "
        "full time part job jobs title type posted date location apply now "
        "equal employer will".split()
    )

    def _extract_keywords(self, text: str) -> list:
        """
        Extract meaningful keywords/phrases from job description.
        Two-pass approach:
        1. Match hardcoded tech patterns (high-confidence)
        2. Extract meaningful bigrams + important unigrams via NLP-lite heuristics
        """
        if not text.strip():
            return []

        text_lower = text.lower()

        # Common technical skills and tools to look for
        tech_patterns = [
            # Programming languages
            r'\bpython\b', r'\bjava\b', r'\bjavascript\b', r'\btypescript\b',
            r'\bc\+\+\b', r'\bc#\b', r'\bruby\b', r'\bgo\b', r'\brust\b',
            r'\bswift\b', r'\bkotlin\b', r'\bscala\b', r'\br\b(?=\s|,|\.|$)',
            r'\bphp\b', r'\bperl\b', r'\bmatlab\b', r'\bsql\b',
            # Frameworks / libraries
            r'\breact\b', r'\bangular\b', r'\bvue\b', r'\bnode\.?js\b',
            r'\bdjango\b', r'\bflask\b', r'\bspring\b', r'\b\.net\b',
            r'\btensorflow\b', r'\bpytorch\b', r'\bscikit-learn\b',
            r'\bpandas\b', r'\bnumpy\b', r'\bspark\b', r'\bhadoop\b',
            r'\bkafka\b', r'\bairflow\b', r'\bdbt\b',
            # Cloud & DevOps
            r'\baws\b', r'\bazure\b', r'\bgcp\b', r'\bgoogle cloud\b',
            r'\bdocker\b', r'\bkubernetes\b', r'\bk8s\b', r'\bterraform\b',
            r'\bansible\b', r'\bci/cd\b', r'\bjenkins\b', r'\bgithub actions\b',
            r'\blinux\b', r'\bgit\b',
            # Data
            r'\bmachine learning\b', r'\bdeep learning\b', r'\bnlp\b',
            r'\bnatural language processing\b', r'\bcomputer vision\b',
            r'\bdata science\b', r'\bdata engineering\b', r'\bdata analysis\b',
            r'\bdata pipeline[s]?\b', r'\betl\b', r'\bdata warehouse\b',
            r'\bpostgresql\b', r'\bmongodb\b', r'\bredis\b', r'\belasticsearch\b',
            r'\bmysql\b', r'\bnosql\b', r'\bsqlite\b',
            r'\btableau\b', r'\bpower bi\b', r'\blooker\b',
            # Methodologies
            r'\bagile\b', r'\bscrum\b', r'\bkanban\b', r'\bdevops\b',
            r'\bmicroservices\b', r'\brest\s*api\b', r'\bgraphql\b',
            # Soft skills / business
            r'\bleadership\b', r'\bproject management\b', r'\bstakeholder\b',
            r'\bcross-functional\b', r'\bmentoring\b', r'\bcollaboration\b',
        ]

        found_keywords = []
        seen = set()

        # ── Pass 1: known tech patterns (high confidence) ─────────────────────
        for pattern in tech_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                kw = matches[0].strip()
                if kw not in seen and len(kw) > 1:
                    seen.add(kw)
                    found_keywords.append(kw)

        # ── Pass 2: NLP-lite extraction of JD-specific terms ──────────────────
        # Tokenize: keep only alphabetic words + hyphenated compounds
        tokens = re.findall(r'[a-z]+(?:-[a-z]+)*', text_lower)
        # Filter out stopwords and very short tokens
        clean_tokens = [t for t in tokens if t not in self._STOPWORDS and len(t) >= 3]

        # 2a. Bigrams — pairs of adjacent meaningful words
        bigram_counts = Counter()
        for i in range(len(clean_tokens) - 1):
            bigram = f"{clean_tokens[i]} {clean_tokens[i+1]}"
            bigram_counts[bigram] += 1

        # Keep bigrams that appear at least once (in short JDs everything appears once)
        # but prioritise those that appear multiple times
        for bigram, count in bigram_counts.most_common(30):
            if bigram not in seen:
                # Verify the bigram actually appears as a phrase in the original text
                if re.search(r'\b' + re.escape(bigram) + r'\b', text_lower):
                    seen.add(bigram)
                    found_keywords.append(bigram)

        # 2b. Important unigrams — domain words that are long enough to be meaningful
        unigram_counts = Counter(clean_tokens)
        for word, count in unigram_counts.most_common(40):
            if word not in seen and len(word) >= 4 and count >= 2:
                seen.add(word)
                found_keywords.append(word)

        # Cap at 40 keywords to avoid keyword-stuffing penalty
        return found_keywords[:40]

    # ── Formatting Compliance (20%) ───────────────────────────────────────────

    def _check_formatting(self, resume_text: str) -> dict:
        issues = []
        deductions = 0

        for pattern, message in self.BAD_FORMAT_PATTERNS:
            if re.search(pattern, resume_text):
                issues.append(message)
                deductions += 12

        # Check bullet consistency
        bullets = re.findall(r'^[\s]*([•\-\*▪►●→])', resume_text, re.MULTILINE)
        if bullets:
            unique_bullets = set(bullets)
            if len(unique_bullets) > 2:
                issues.append(f"Inconsistent bullet styles ({len(unique_bullets)} different types found)")
                deductions += 8

        # Check for header/footer-like content (email at very top or bottom without context)
        lines = resume_text.strip().split('\n')
        if len(lines) > 3:
            # Check if first line looks like a header
            first_line = lines[0].strip()
            if len(first_line) > 100:
                issues.append("First line is very long — ATS may misparse it as a header block")
                deductions += 5

        # Check for excessive blank lines
        blank_runs = re.findall(r'\n{4,}', resume_text)
        if blank_runs:
            issues.append("Excessive blank lines detected (keep to single line breaks)")
            deductions += 5

        score = max(0, 100 - deductions)
        if not issues:
            score = 100

        return {"score": score, "issues": issues}

    # ── Quantifiable Achievements (10%) ───────────────────────────────────────

    def _check_achievements(self, resume_text: str) -> dict:
        patterns = [
            r'\d+\s*%',                    # percentages: 35%, 10 %
            r'\$[\d,]+(?:\.\d+)?[KMBkmb]?', # dollar amounts: $1.2M, $50,000
            r'€[\d,]+(?:\.\d+)?[KMBkmb]?',  # euro amounts
            r'£[\d,]+(?:\.\d+)?[KMBkmb]?',  # pound amounts
            r'₹[\d,]+(?:\.\d+)?[KMBkmb]?',  # rupee amounts
            r'\d+\+?\s+years?',              # years: 5+ years, 3 years
            r'\d+x\b',                       # multipliers: 3x, 10x
            r'\b\d{1,3}(?:,\d{3})+\b',      # large numbers: 1,000,000
            r'\b(?:increased|decreased|improved|reduced|grew|saved|generated|boosted|cut|achieved)\b.*?\d+',  # action + number
        ]

        found = []
        for pattern in patterns:
            matches = re.findall(pattern, resume_text, re.IGNORECASE)
            for m in matches:
                cleaned = m.strip()[:50]  # Cap length
                if cleaned and cleaned not in found:
                    found.append(cleaned)

        # Score based on number of quantified achievements
        count = len(found)
        if count >= 8:
            score = 100
        elif count >= 5:
            score = 85
        elif count >= 3:
            score = 70
        elif count >= 1:
            score = 50
        else:
            score = 20

        return {"score": score, "found": found[:12]}  # Cap display at 12

    # ── Length & Structure (10%) ───────────────────────────────────────────────

    def _check_length(self, resume_text: str) -> dict:
        words = resume_text.split()
        word_count = len(words)
        lines = resume_text.strip().split('\n')
        line_count = len(lines)

        feedback = []

        # Optimal word count for a resume: 300-800
        if word_count < 150:
            score = 30
            feedback.append(f"Too short ({word_count} words). Aim for 300–800 words.")
        elif word_count < 300:
            score = 60
            feedback.append(f"Slightly short ({word_count} words). Consider adding more detail.")
        elif word_count <= 800:
            score = 100
            feedback.append(f"Good length ({word_count} words).")
        elif word_count <= 1200:
            score = 75
            feedback.append(f"Slightly long ({word_count} words). Consider trimming to under 800.")
        else:
            score = 50
            feedback.append(f"Too long ({word_count} words). ATS systems prefer concise resumes.")

        # Check for reasonable structure (at least some line breaks)
        if line_count < 10 and word_count > 200:
            score = max(30, score - 20)
            feedback.append("Very few line breaks — content appears as a wall of text.")

        return {"score": score, "word_count": word_count, "feedback": feedback}

    # ── Contact Information (10%) ─────────────────────────────────────────────

    def _check_contact(self, resume_text: str) -> dict:
        details = {"email": False, "phone": False, "linkedin": False}
        score = 0

        # Email
        if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', resume_text):
            details["email"] = True
            score += 40

        # Phone (various formats)
        if re.search(r'(?:\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}', resume_text):
            details["phone"] = True
            score += 30

        # LinkedIn
        if re.search(r'linkedin\.com/in/', resume_text, re.IGNORECASE):
            details["linkedin"] = True
            score += 30

        return {"score": score, "details": details}
