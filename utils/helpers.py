"""Utility functions for the SEO content agent system."""

import json
import re
import unicodedata


def slugify(text):
    """Convert text to URL-friendly slug."""
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def count_words(text):
    """Count words in text, stripping markdown formatting."""
    clean = re.sub(r'```[\s\S]*?```', '', text)
    clean = re.sub(r'[#*`\[\]()>|_~]', ' ', clean)
    clean = re.sub(r'https?://\S+', '', clean)
    return len(clean.split())


def extract_json_from_text(text):
    """Extract the first valid JSON object from a text string."""
    start = text.find('{')
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None
