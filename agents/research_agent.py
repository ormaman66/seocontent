"""
Research Agent - Uses Claude's web_search and web_fetch tools (no external APIs).

This agent:
1. Searches Google using Claude's web_search tool
2. Fetches top competitor pages using web_fetch
3. Extracts products, headings, word counts
4. Caches results for 7 days
5. Returns competitive intelligence JSON
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from anthropic import Anthropic


class ResearchAgent:
    def __init__(self, config):
        self.client = Anthropic(api_key=config['anthropic_api_key'])
        self.model = config['settings']['model']
        self.cache_dir = Path('data/cache')
        self.cache_ttl = config['settings']['cache_ttl_days']
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def research(self, keyword):
        """
        Main research method - uses ONLY Claude's built-in tools.

        Returns:
            {
                'keyword': str,
                'serp_results': [...],
                'competitor_analysis': {...},
                'cache_expires': str
            }
        """
        cache_file = self.cache_dir / f"{keyword.replace(' ', '_')}.json"
        if self._is_cache_valid(cache_file):
            print(f"  Using cached research for '{keyword}'")
            with open(cache_file, 'r') as f:
                return json.load(f)

        print(f"  Researching '{keyword}' using Claude's web_search...")

        # Step 1: SERP Research using web_search
        conversation = []

        conversation.append({
            "role": "user",
            "content": (
                f'Search Google for "{keyword}" and return the top 5 ranking results.\n\n'
                "For each result, extract:\n"
                "- URL\n- Page title\n- A brief snippet of what they cover\n"
                "- What products they mention (if you can tell from snippets)\n\n"
                "Return as JSON in this exact format:\n"
                '{\n  "results": [\n    {\n'
                '      "rank": 1,\n      "url": "https://...",\n'
                '      "title": "...",\n      "snippet": "...",\n'
                '      "products_mentioned": ["product1", "product2"]\n'
                "    }\n  ]\n}\n\nONLY return valid JSON, no other text."
            ),
        })

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
            messages=conversation,
        )

        serp_data = self._extract_json(response)
        conversation.append({"role": "assistant", "content": response.content})

        result_count = len(serp_data.get('results', []))
        print(f"  Found {result_count} results")

        # Step 2: Analyze top competitor using web_fetch
        competitor_analysis = {}
        if serp_data.get('results') and len(serp_data['results']) > 0:
            top_url = serp_data['results'][0]['url']
            print(f"  Analyzing top competitor: {top_url}")

            conversation.append({
                "role": "user",
                "content": (
                    f"Fetch the page at {top_url} and analyze:\n\n"
                    "1. Word count (approximate)\n"
                    "2. Heading structure (list all H2 and H3 headings)\n"
                    "3. What products they recommend (extract product names)\n"
                    "4. Content structure (what sections do they have?)\n"
                    "5. Content gaps (what angles could we cover better?)\n\n"
                    "Return as JSON:\n"
                    '{\n  "word_count": 3500,\n'
                    '  "headings": {"h2": ["heading1"], "h3": ["subheading1"]},\n'
                    '  "products": ["product1", "product2"],\n'
                    '  "sections": ["intro", "products", "buying guide", "faq"],\n'
                    '  "content_gaps": ["missing angle 1", "missing angle 2"]\n}'
                ),
            })

            response = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                tools=[{"type": "web_fetch_20250305", "name": "web_fetch"}],
                messages=conversation,
            )

            competitor_analysis = self._extract_json(response)
            print("  Competitor analysis complete")

        # Combine and cache results
        research_data = {
            'keyword': keyword,
            'timestamp': datetime.now().isoformat(),
            'serp_results': serp_data.get('results', []),
            'competitor_analysis': competitor_analysis,
            'cache_expires': (datetime.now() + timedelta(days=self.cache_ttl)).isoformat(),
        }

        with open(cache_file, 'w') as f:
            json.dump(research_data, f, indent=2)

        print(f"  Research complete and cached for {self.cache_ttl} days")
        return research_data

    def _extract_json(self, response):
        """Extract JSON from Claude's response, searching all text blocks."""
        for block in response.content:
            if block.type == "text":
                text = block.text
                start = text.find('{')
                end = text.rfind('}') + 1
                if start != -1 and end > start:
                    try:
                        return json.loads(text[start:end])
                    except json.JSONDecodeError:
                        pass
        return {}

    def _is_cache_valid(self, cache_file):
        """Check if cached research is still valid."""
        if not cache_file.exists():
            return False
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            expires = datetime.fromisoformat(data.get('cache_expires', '2000-01-01'))
            return datetime.now() < expires
        except (json.JSONDecodeError, KeyError, ValueError):
            return False
