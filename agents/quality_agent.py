"""
Quality Control Agent - Validates articles before publishing.

Checks:
1. Word count >= 4,000
2. Keyword density 1-2%
3. No "I tested" phrases (FTC compliance)
4. All products mentioned
5. Schema JSON is valid
6. Affiliate links injected
"""

import json
import re


class QualityAgent:
    def __init__(self, config):
        self.min_word_count = config['settings']['min_word_count']
        self.forbidden_phrases = [
            "i tested", "we tested", "in my testing", "in our testing",
            "after using", "during my review", "i personally",
        ]

    def validate(self, article_data, keyword, products):
        """
        Validate article quality.

        Returns:
            {'passed': bool, 'issues': list, 'warnings': list, 'metrics': dict}
        """
        print("  Running quality checks...")

        markdown = article_data['markdown']
        word_count = article_data['word_count']
        issues = []
        warnings = []

        # Check 1: Word count
        if word_count < self.min_word_count:
            issues.append(f"Word count {word_count} < minimum {self.min_word_count}")

        # Check 2: Keyword density
        keyword_count = markdown.lower().count(keyword.lower())
        keyword_density = (keyword_count / max(word_count, 1)) * 100
        if keyword_density < 1.0:
            warnings.append(f"Keyword density {keyword_density:.2f}% is low (target: 1-2%)")
        elif keyword_density > 2.5:
            warnings.append(f"Keyword density {keyword_density:.2f}% is high (target: 1-2%)")

        # Check 3: FTC compliance - no "I tested" language
        markdown_lower = markdown.lower()
        for phrase in self.forbidden_phrases:
            if phrase in markdown_lower:
                issues.append(
                    f"FTC violation: Found '{phrase}' - must use research-based language"
                )

        # Check 4: All products mentioned
        for product in products:
            if product['name'] not in markdown:
                warnings.append(f"Product not mentioned: {product['name']}")

        # Check 5: Schema JSON present and valid
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', markdown)
        if json_match:
            try:
                json.loads(json_match.group(1))
            except json.JSONDecodeError:
                warnings.append("Schema JSON is malformed")
        else:
            if '"@context"' in markdown:
                warnings.append("Schema JSON found but not in code fence")
            else:
                warnings.append("No schema markup detected")

        # Check 6: Affiliate links
        amazon_links = markdown.count('amazon.com/dp/')
        if amazon_links < len(products):
            warnings.append(
                f"Only {amazon_links} affiliate links found (expected {len(products)})"
            )

        passed = len(issues) == 0

        metrics = {
            'word_count': word_count,
            'keyword_count': keyword_count,
            'keyword_density': round(keyword_density, 2),
            'affiliate_links': amazon_links,
            'products_covered': len([p for p in products if p['name'] in markdown]),
        }

        if passed:
            print("  Quality check PASSED")
        else:
            print(f"  Quality check FAILED - {len(issues)} issue(s)")

        return {
            'passed': passed,
            'issues': issues,
            'warnings': warnings,
            'metrics': metrics,
        }
