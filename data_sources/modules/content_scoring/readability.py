"""Readability responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


class ReadabilityScoringMixin:
    def _score_readability(self, content: str) -> Dict[str, Any]:
        """Score content for readability, rhythm, and paragraph length"""
        issues = []
        details = {}

        # Use existing readability scorer
        try:
            analysis = self.readability_scorer.analyze(content)
            flesch = analysis.get('readability_metrics', {}).get('flesch_reading_ease', 50)
            grade = analysis.get('reading_level', 12)
        except Exception:
            # Fallback if module fails
            flesch = 60
            grade = 10

        details['flesch_reading_ease'] = flesch
        details['grade_level'] = grade

        # Target: Flesch 60-70 (fairly easy), Grade 8-10
        score = 100

        if flesch < 50:
            penalty = min(30, (50 - flesch) * 1.5)
            score -= penalty
            issues.append({
                'issue': f'Content too difficult (Flesch: {flesch})',
                'fix': 'Simplify sentences, use shorter words',
                'severity': 'high' if flesch < 40 else 'medium'
            })
        elif flesch < 60:
            score -= 10
            issues.append({
                'issue': f'Content slightly difficult (Flesch: {flesch})',
                'fix': 'Simplify some complex sentences',
                'severity': 'low'
            })
        elif flesch > 80:
            # Too simple (not heavily penalized)
            score -= 5

        if grade > 12:
            score -= 10
            issues.append({
                'issue': f'Reading level too high (Grade {grade})',
                'fix': 'Target 8th-10th grade reading level',
                'severity': 'medium'
            })

        # NEW: Check paragraph length (max 4 sentences)
        paragraph_issues = self._check_paragraph_length(content)
        details['long_paragraphs'] = paragraph_issues['count']
        details['longest_paragraph_sentences'] = paragraph_issues['longest']

        if paragraph_issues['count'] > 0:
            penalty = min(15, paragraph_issues['count'] * 3)
            score -= penalty
            issues.append({
                'issue': f'{paragraph_issues["count"]} paragraphs exceed 4 sentences (longest: {paragraph_issues["longest"]})',
                'fix': 'Break long paragraphs into smaller chunks (2-4 sentences max)',
                'severity': 'medium' if paragraph_issues['count'] < 5 else 'high'
            })

        # NEW: Check sentence rhythm (variety in length)
        rhythm_issues = self._check_sentence_rhythm(content)
        details['rhythm_score'] = rhythm_issues['rhythm_score']
        details['monotonous_sections'] = rhythm_issues['monotonous_count']

        if rhythm_issues['rhythm_score'] < 60:
            penalty = min(10, (60 - rhythm_issues['rhythm_score']) / 4)
            score -= penalty
            issues.append({
                'issue': f'Monotonous sentence rhythm ({rhythm_issues["monotonous_count"]} uniform sections)',
                'fix': 'Vary sentence length: mix short punchy (5-10 words) with longer flowing (15-25 words)',
                'severity': 'medium' if rhythm_issues['rhythm_score'] > 40 else 'high'
            })

        return {
            'score': max(0, min(100, round(score))),
            'flesch': flesch,
            'issues': issues,
            'details': details
        }
    def _check_paragraph_length(self, content: str) -> Dict[str, Any]:
        """Check for paragraphs that exceed 4 sentences"""
        # Split into paragraphs (double newline or blank line)
        paragraphs = re.split(r'\n\s*\n', content)

        long_paragraphs = 0
        longest = 0

        for para in paragraphs:
            para = para.strip()
            # Skip headers, lists, tables, metadata
            if not para or para.startswith('#') or para.startswith('-') or para.startswith('*') or para.startswith('|') or para.startswith('**Meta'):
                continue

            # Count sentences (rough: split by . ! ? followed by space or end)
            sentences = re.split(r'[.!?]+(?:\s|$)', para)
            sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

            sentence_count = len(sentences)
            if sentence_count > 4:
                long_paragraphs += 1
                longest = max(longest, sentence_count)

        return {
            'count': long_paragraphs,
            'longest': longest
        }
    def _check_sentence_rhythm(self, content: str) -> Dict[str, Any]:
        """Check for sentence length variety (rhythm)"""
        # Extract sentences
        sentences = re.split(r'[.!?]+(?:\s|$)', content)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

        if len(sentences) < 10:
            return {'rhythm_score': 70, 'monotonous_count': 0}  # Not enough to evaluate

        # Calculate word counts for each sentence
        word_counts = [len(s.split()) for s in sentences]

        # Check rhythm in sliding windows of 5 sentences
        monotonous_sections = 0
        window_size = 5

        for i in range(len(word_counts) - window_size + 1):
            window = word_counts[i:i + window_size]
            avg = sum(window) / len(window)

            # Check if all sentences in window are within 5 words of average (monotonous)
            all_similar = all(abs(wc - avg) <= 5 for wc in window)
            if all_similar:
                monotonous_sections += 1

        # Calculate rhythm score
        # More variety = higher score
        if len(word_counts) > 0:
            std_dev = (sum((wc - sum(word_counts)/len(word_counts))**2 for wc in word_counts) / len(word_counts)) ** 0.5
        else:
            std_dev = 0

        # Target std_dev around 8-15 (good variety)
        if std_dev < 5:
            rhythm_score = 40 + (std_dev * 6)  # Too uniform
        elif std_dev <= 15:
            rhythm_score = 100 - abs(10 - std_dev) * 2  # Sweet spot
        else:
            rhythm_score = 80  # High variety is fine

        # Penalize for monotonous sections
        rhythm_score -= monotonous_sections * 3
        rhythm_score = max(0, min(100, rhythm_score))

        return {
            'rhythm_score': round(rhythm_score),
            'monotonous_count': monotonous_sections,
            'std_dev': round(std_dev, 1)
        }
