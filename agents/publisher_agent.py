"""
WordPress Publisher Agent - Auto-publishes articles to WordPress.

This agent:
1. Connects to WordPress REST API
2. Creates a new post with the article
3. Sets Rank Math SEO fields (title, meta description, focus keyword)
4. Sets permalink structure
5. Publishes or saves as draft
6. Returns the published URL
"""

import json
import re
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth


class PublisherAgent:
    def __init__(self, config):
        self.wp_url = config['wordpress']['url'].rstrip('/')
        self.wp_user = config['wordpress']['username']
        self.wp_pass = config['wordpress']['application_password']
        self.auth = HTTPBasicAuth(self.wp_user, self.wp_pass)

        self.published_file = Path('data/published.json')
        self.published_data = self._load_published()

    def publish(self, article_data, keyword, category, year, auto_publish=False):
        """
        Publish article to WordPress.

        Args:
            article_data: Output from ContentAgent
            keyword: e.g. "best laptops 2026"
            category: e.g. "laptop"
            year: e.g. "2026"
            auto_publish: True = publish, False = save as draft

        Returns:
            {'success': bool, 'url': str, 'post_id': int} or {'success': False, 'error': str}
        """
        print("  Publishing to WordPress...")

        markdown = article_data['markdown']
        title = self._extract_title(markdown, keyword, year)

        meta_title = f"Best {category.title()}s {year}: Top Picks Tested & Reviewed"
        meta_desc = (
            f"Our editorial team researched the best {category}s in {year}. "
            "Expert picks for every budget -- read before you buy."
        )
        slug = f"best-{category}s-{year}"

        post_data = {
            'title': title,
            'content': self._markdown_to_html(markdown),
            'status': 'publish' if auto_publish else 'draft',
            'slug': slug,
            'categories': [self._get_or_create_category(category)],
            'meta': {
                'rank_math_title': meta_title,
                'rank_math_description': meta_desc,
                'rank_math_focus_keyword': keyword,
                'rank_math_robots': ['index', 'follow'],
            },
        }

        try:
            response = requests.post(
                f"{self.wp_url}/wp-json/wp/v2/posts",
                auth=self.auth,
                json=post_data,
                headers={'Content-Type': 'application/json'},
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

            post_id = result['id']
            post_url = result['link']

            self.published_data[keyword] = {
                'post_id': post_id,
                'url': post_url,
                'published_at': result['date'],
                'status': result['status'],
            }
            self._save_published()

            print(f"  Published: {post_url}")
            return {'success': True, 'url': post_url, 'post_id': post_id, 'status': result['status']}

        except requests.exceptions.RequestException as e:
            print(f"  Publishing failed: {e}")
            return {'success': False, 'error': str(e)}

    def _extract_title(self, markdown, keyword, year):
        """Extract H1 from markdown or generate a title."""
        h1_match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
        if h1_match:
            return h1_match.group(1)
        return f"The Best {keyword.title()} -- Expert Picks for {year}"

    def _markdown_to_html(self, markdown):
        """Convert markdown to HTML for WordPress."""
        html = markdown

        # Remove JSON-LD code blocks (handled separately by schema)
        html = re.sub(r'```json\s*\{[\s\S]*?"@context"[\s\S]*?\}\s*```', '', html)

        # Convert headers (order matters: h3 before h2 before h1)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Convert bold/italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # Convert links (add sponsored rel for affiliate links)
        def _replace_link(match):
            text = match.group(1)
            href = match.group(2)
            if 'amazon.com' in href:
                return f'<a href="{href}" target="_blank" rel="noopener sponsored nofollow">{text}</a>'
            return f'<a href="{href}" target="_blank" rel="noopener">{text}</a>'

        html = re.sub(r'\[(.+?)\]\((.+?)\)', _replace_link, html)

        # Convert unordered list items
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

        # Wrap consecutive <li> in <ul>
        html = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\1</ul>\n', html)

        # Convert horizontal rules
        html = re.sub(r'^---+$', '<hr>', html, flags=re.MULTILINE)

        # Wrap remaining loose text lines in <p> tags
        lines = html.split('\n')
        result = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('<'):
                result.append(stripped)
            else:
                result.append(f'<p>{stripped}</p>')
        html = '\n'.join(result)

        return html

    def _get_or_create_category(self, category):
        """Get WordPress category ID or create if it doesn't exist."""
        try:
            response = requests.get(
                f"{self.wp_url}/wp-json/wp/v2/categories",
                auth=self.auth,
                params={'search': category},
                timeout=15,
            )
            categories = response.json()
            if categories:
                return categories[0]['id']

            response = requests.post(
                f"{self.wp_url}/wp-json/wp/v2/categories",
                auth=self.auth,
                json={'name': category.title(), 'slug': category},
                timeout=15,
            )
            return response.json()['id']
        except requests.exceptions.RequestException:
            return 1  # Default "Uncategorized" category

    def _load_published(self):
        """Load published articles tracking."""
        if self.published_file.exists():
            try:
                with open(self.published_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_published(self):
        """Save published articles tracking."""
        self.published_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.published_file, 'w') as f:
            json.dump(self.published_data, f, indent=2)

    def is_published(self, keyword):
        """Check if keyword has already been published."""
        return keyword in self.published_data
