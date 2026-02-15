"""
Content Generation Agent - Creates 4,000+ word SEO articles.

This agent:
1. Reads research data from Research Agent
2. Loads product database for the category
3. Builds a detailed prompt with competitor intel
4. Calls Claude API with max_tokens for long-form content
5. Returns markdown article + metadata
"""

import json
import re
from pathlib import Path

from anthropic import Anthropic


class ContentAgent:
    def __init__(self, config):
        self.client = Anthropic(api_key=config['anthropic_api_key'])
        self.model = config['settings']['model']
        self.max_tokens = config['settings']['max_tokens']
        self.affiliate_tag = config['affiliate_tag']

        with open('config/product_database.json', 'r') as f:
            self.product_db = json.load(f)

    def generate(self, keyword, category, year, research_data):
        """
        Generate 4,000+ word article.

        Args:
            keyword: e.g. "best laptops 2026"
            category: e.g. "laptop"
            year: e.g. "2026"
            research_data: Output from ResearchAgent

        Returns:
            {'markdown': str, 'word_count': int, 'metadata': dict}
        """
        print(f"  Generating article for '{keyword}'...")

        products = self.product_db.get(category, [])[:5]
        competitor_intel = self._build_competitor_summary(research_data)
        product_block = self._build_product_block(products)

        prompt = self._build_prompt(
            keyword, category, year, competitor_intel, product_block, products
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        markdown = ""
        for block in response.content:
            if block.type == "text":
                markdown += block.text

        markdown = self._inject_affiliate_links(markdown, products)
        word_count = len(markdown.split())

        print(f"  Article generated: {word_count} words")

        return {
            'markdown': markdown,
            'word_count': word_count,
            'metadata': {
                'keyword': keyword,
                'category': category,
                'year': year,
                'products_count': len(products),
            },
        }

    def _build_prompt(self, keyword, category, year, competitor_intel, product_block, products):
        """Build the master content generation prompt."""
        num_products = len(products)
        tag = self.affiliate_tag

        return f"""You are a senior editorial writer for a tech review publication. You write definitive buying guides that help readers make informed purchase decisions.

TARGET KEYWORD: "{keyword}"
YEAR: {year}
CATEGORY: {category}

=== COMPETITOR INTELLIGENCE ===
{competitor_intel}

Your article MUST cover all the angles competitors cover, plus find gaps they missed.

=== PRODUCTS TO REVIEW ===
{product_block}

=== CRITICAL LEGAL REQUIREMENT ===
You are a RESEARCH-BASED publication. You have NOT physically tested these products.

APPROVED language:
- "Based on expert reviews and benchmark data from professional testing labs..."
- "According to analysis of 40+ professional reviews..."
- "Verified performance data shows..."
- "Our editorial team analyzed expert sources and user feedback..."
- "Industry benchmark results indicate..."

NEVER use:
- "I tested" / "we tested" / "in our testing"
- "After using this" / "during my review period"
- Any first-person claims of physical product use

WHY: FTC Consumer Review Rule (2024) - civil penalties up to $53,088 per violation for false product testing claims.

=== ARTICLE STRUCTURE - 4,000+ WORDS MINIMUM ===

Write EVERY section at FULL length. Do not abbreviate.

## Editorial Disclosure
[1 sentence: Our editorial team researches... we earn commission via links... doesn't affect recommendations]

## Quick Answer: The Best {category.title()}s in {year}
[150 words. Direct answer. Name #1 pick with reason. Name budget pick. Target Google featured snippet.]

## Why Our Editorial Team Recommends These {category.title()}s
[200 words. Research methodology: "We analyzed 47 professional reviews from Tom's Guide, PCMag, Laptop Mag, TechRadar, plus cross-referenced benchmark databases and assessed 12,000+ verified user reviews." Be specific about sources and process.]

## The {num_products} Best {category.title()}s in {year} -- At a Glance
[Bullet list of all {num_products} products with one-line "Best For" labels]

---

[PRODUCT SECTIONS - 600-700 words EACH]

For EACH product, write this complete structure:

## [Number]. [Product Name] -- [Best For]

**Editorial Score: [score]/10** | **Price: [price]**

### Overview
[2 paragraphs, 120 words. Strong opinion based on expert consensus.]

### Performance & Specifications
[2 paragraphs, 180 words. Deep dive on specs. Quote specific benchmarks.]

### Who Should Choose This {category.title()}?

**This is the right choice if you:**
- [Specific use case with concrete reason]
- [Specific user type]
- [Specific scenario]

**Consider an alternative if you:**
- [Honest limitation]
- [Another real contraindication]

### Expert Verdict
[80 words. Summary recommendation. End with CTA: "Check current price on Amazon"]

---

## Complete Buying Guide: How to Choose the Best {category.title()} in {year}
[400 words total across these subsections:]

### Setting Your Budget: What Each Price Range Gets You
[110 words. Specific price brackets.]

### The Specifications That Actually Matter
[120 words. Focus on 3-4 key specs. Explain in plain English.]

### {category.title()}s to Avoid in {year}
[80 words. Types/spec combinations to avoid without naming specific products.]

### Premium vs. Budget: Is It Worth Spending More?
[90 words. Honest guidance on price/performance sweet spot.]

## How We Research and Evaluate {category.title()}s
[300 words. CRITICAL for E-E-A-T. Explain methodology in detail.]

## Frequently Asked Questions

### What is the best {category} to buy in {year}?
[100 words. Direct answer.]

### What is a good budget for a {category} in {year}?
[100 words. Specific price guidance.]

### How long does a {category} typically last?
[90 words. Practical durability guidance.]

### Is it worth buying a more expensive {category}?
[100 words. Nuanced answer with real trade-offs.]

### Which {category} brand is most reliable in {year}?
[90 words. Evidence-based brand reliability.]

## Our Final Verdict: The Best {category.title()}s in {year}
[300 words. Recap all picks. Restate overall winner. Use primary keyword naturally 2x.]

=== JSON-LD SCHEMA ===
At the very end, add a JSON-LD schema block wrapped in ```json fences containing:
- ItemList with {num_products} products (Amazon URLs with tag={tag})
- Article schema with headline and dateModified
- FAQPage schema with all 5 FAQ questions and answers

=== FORMATTING RULES ===
- Return ONLY markdown (no preamble)
- Write EVERY section at FULL length
- Minimum 4,000 words total
- Keep paragraphs 3-5 sentences (mobile-friendly)
- Use research/editorial voice throughout
"""

    def _build_competitor_summary(self, research_data):
        """Build competitor intelligence summary from research."""
        summary = f"SERP Analysis for '{research_data['keyword']}':\n\n"

        if research_data.get('serp_results'):
            summary += "Top Ranking Pages:\n"
            for result in research_data['serp_results'][:5]:
                summary += f"  {result.get('rank', '?')}. {result.get('title', 'N/A')} ({result.get('url', '')})\n"
                if result.get('products_mentioned'):
                    summary += f"     Products: {', '.join(result['products_mentioned'])}\n"

        ca = research_data.get('competitor_analysis')
        if ca:
            summary += f"\nTop Competitor Analysis:\n"
            summary += f"  Word Count: ~{ca.get('word_count', 'unknown')}\n"
            if ca.get('sections'):
                summary += f"  Sections: {', '.join(ca['sections'])}\n"
            if ca.get('content_gaps'):
                summary += f"  Content Gaps to Exploit: {', '.join(ca['content_gaps'])}\n"

        return summary

    def _build_product_block(self, products):
        """Format products for the prompt."""
        block = ""
        for i, p in enumerate(products, 1):
            block += f"\nPRODUCT {i}: {p['name']}\n"
            block += f"Price: {p['price']} | Rating: {p['rating']}/5 ({p['reviews']} reviews)\n"
            block += f"Best For: {p['best_for']}\n"
            block += f"Specs: {p['specs']}\n"
            block += f"Pros: {' / '.join(p['pros'])}\n"
            block += f"Cons: {' / '.join(p['cons'])}\n"
        return block

    def _inject_affiliate_links(self, markdown, products):
        """Auto-inject Amazon affiliate links for each product (first occurrence)."""
        for product in products:
            asin = product['asin']
            name = product['name']
            url = f"https://www.amazon.com/dp/{asin}?tag={self.affiliate_tag}"
            link = f"[{name}]({url})"
            # Only replace first occurrence that isn't already a link
            if name in markdown and f"[{name}]" not in markdown:
                markdown = markdown.replace(name, link, 1)
        return markdown
