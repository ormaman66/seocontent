"""
Main Orchestrator - Runs the full SEO content agent pipeline.

Usage:
    python main.py --keyword "best laptops 2026" --category laptop --year 2026
    python main.py --batch data/keywords.csv
    python main.py --batch data/keywords.csv --publish
"""

import argparse
import csv
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

from agents.research_agent import ResearchAgent
from agents.content_agent import ContentAgent
from agents.quality_agent import QualityAgent
from agents.publisher_agent import PublisherAgent


class SEOAgent:
    def __init__(self, config_path='config/config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.research_agent = ResearchAgent(self.config)
        self.content_agent = ContentAgent(self.config)
        self.quality_agent = QualityAgent(self.config)
        self.publisher_agent = PublisherAgent(self.config)

        self.output_dir = Path('data/output')
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_keyword(self, keyword, category, year, auto_publish=False):
        """
        Full agent pipeline for one keyword.

        Steps:
        1. Research Agent -> SERP intelligence
        2. Content Agent -> Generate article
        3. Quality Agent -> Validate
        4. Publisher Agent -> WordPress (if auto_publish)
        """
        print(f"\n{'=' * 60}")
        print(f"Processing: {keyword}")
        print(f"{'=' * 60}\n")

        if self.publisher_agent.is_published(keyword):
            url = self.publisher_agent.published_data[keyword]['url']
            print(f"  Already published: {url}")
            return {'success': True, 'skipped': True, 'reason': 'already_published'}

        try:
            # Step 1: Research
            research_data = self.research_agent.research(keyword)

            # Step 2: Generate content
            article_data = self.content_agent.generate(
                keyword=keyword,
                category=category,
                year=year,
                research_data=research_data,
            )

            # Save to file
            filename = f"{keyword.replace(' ', '_')}_{year}.md"
            output_file = self.output_dir / filename
            with open(output_file, 'w') as f:
                f.write(article_data['markdown'])
            print(f"  Saved: {output_file}")

            # Step 3: Quality control
            products = self.content_agent.product_db.get(category, [])[:5]
            qa_result = self.quality_agent.validate(
                article_data=article_data,
                keyword=keyword,
                products=products,
            )

            print(f"\n  Quality Metrics:")
            for key, value in qa_result['metrics'].items():
                print(f"    {key}: {value}")

            if qa_result['warnings']:
                print(f"\n  Warnings:")
                for warning in qa_result['warnings']:
                    print(f"    - {warning}")

            if not qa_result['passed']:
                print(f"\n  Quality check failed:")
                for issue in qa_result['issues']:
                    print(f"    - {issue}")
                return {'success': False, 'qa_failed': True, 'issues': qa_result['issues']}

            # Step 4: Publish (if requested)
            if auto_publish:
                publish_result = self.publisher_agent.publish(
                    article_data=article_data,
                    keyword=keyword,
                    category=category,
                    year=year,
                    auto_publish=True,
                )
                if publish_result['success']:
                    return {
                        'success': True,
                        'published': True,
                        'url': publish_result['url'],
                        'metrics': qa_result['metrics'],
                    }
                else:
                    return {
                        'success': False,
                        'publish_failed': True,
                        'error': publish_result.get('error'),
                    }
            else:
                print(f"\n  Article ready (use --publish to auto-publish)")
                return {
                    'success': True,
                    'published': False,
                    'file': str(output_file),
                    'metrics': qa_result['metrics'],
                }

        except Exception as e:
            print(f"\n  Error: {e}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    def process_batch(self, csv_file, auto_publish=False):
        """Process multiple keywords from CSV."""
        results = []

        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            keywords = list(reader)

        total = len(keywords)
        print(f"\n  Processing {total} keywords from {csv_file}")

        for i, row in enumerate(keywords, 1):
            print(f"\n[{i}/{total}]")
            result = self.process_keyword(
                keyword=row['keyword'],
                category=row['category'],
                year=row['year'],
                auto_publish=auto_publish,
            )
            results.append({'keyword': row['keyword'], **result})

        # Summary
        print(f"\n{'=' * 60}")
        print("BATCH SUMMARY")
        print(f"{'=' * 60}")
        print(f"Total: {total}")
        print(f"Success: {sum(1 for r in results if r['success'])}")
        print(f"Failed: {sum(1 for r in results if not r['success'])}")
        print(f"Published: {sum(1 for r in results if r.get('published'))}")
        print(f"Skipped: {sum(1 for r in results if r.get('skipped'))}")

        return results


def main():
    parser = argparse.ArgumentParser(description='AI SEO Content Agent')
    parser.add_argument('--keyword', help='Single keyword to process')
    parser.add_argument('--category', help='Category (laptop, monitor, etc)')
    parser.add_argument('--year', help='Year (e.g., 2026)')
    parser.add_argument('--batch', help='CSV file with keywords')
    parser.add_argument('--publish', action='store_true', help='Auto-publish to WordPress')
    parser.add_argument('--config', default='config/config.json', help='Config file path')

    args = parser.parse_args()

    agent = SEOAgent(config_path=args.config)

    if args.keyword:
        if not args.category or not args.year:
            print("Error: --category and --year required for single keyword mode")
            sys.exit(1)
        result = agent.process_keyword(
            keyword=args.keyword,
            category=args.category,
            year=args.year,
            auto_publish=args.publish,
        )
        sys.exit(0 if result['success'] else 1)

    elif args.batch:
        results = agent.process_batch(csv_file=args.batch, auto_publish=args.publish)
        results_file = (
            Path('data/output') / f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n  Results saved: {results_file}")
        sys.exit(0 if all(r['success'] for r in results) else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
