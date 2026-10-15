import unittest
import xml.etree.ElementTree as ET
from datetime import date
from unittest.mock import patch

import github_analytics as analytics


class AnalyticsTests(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(analytics.twelve_month_start(date(2026, 10, 15)), date(2025, 10, 16))
        self.assertEqual(analytics.twelve_month_start(date(2024, 2, 29)), date(2023, 3, 1))

    def test_pagination(self):
        def page(nodes, more, cursor):
            return {'user': {'contributionsCollection': {'issueContributions': {
                'nodes': nodes, 'pageInfo': {'hasNextPage': more, 'endCursor': cursor}}}}}
        with patch.object(analytics, 'query', side_effect=[
                page([{'id': 'one'}], True, 'next'), page([{'id': 'two'}], False, None)]) as query:
            result = list(analytics.contributions('yada071', date(2025, 10, 16),
                          date(2026, 10, 15), 'issueContributions', 'id'))
        self.assertEqual(len(result), 2)
        self.assertEqual(query.call_args_list[1].args[1]['after'], 'next')

    def test_counts_are_distinct_and_public(self):
        def resource(identifier, repo, private=False):
            return {'id': identifier, 'repository': {'nameWithOwner': repo, 'isPrivate': private}}
        def contributions(username, start, end, field, selection):
            return iter({
                'issueContributions': [{'issue': resource('i1', 'org/shared')}],
                'pullRequestContributions': [{'pullRequest': resource('p1', 'org/shared')}],
                'pullRequestReviewContributions': [
                    {'pullRequest': resource('p2', 'org/reviewed')},
                    {'pullRequest': resource('p2', 'org/reviewed')},
                    {'pullRequest': resource('p3', 'org/private', True)}],
            }[field])
        commits = {'user': {'contributionsCollection': {'commitContributionsByRepository': [
            {'repository': resource('unused', 'org/shared')['repository']},
            {'repository': resource('unused', 'org/code')['repository']},
            {'repository': resource('unused', 'org/private', True)['repository']},
        ]}}}
        with patch.object(analytics, 'contributions', side_effect=contributions), patch.object(
                analytics, 'query', side_effect=[{'search': {'issueCount': 7}}, commits]) as query:
            metrics = analytics.fetch_metrics('yada071', date(2026, 10, 15))
        self.assertEqual(metrics, {'merged': 7, 'reviewed': 1, 'repositories': 3})
        search = query.call_args_list[0].args[1]['q']
        self.assertIn('merged:2025-10-16..2026-10-15', search)
        self.assertIn('is:public', search)

    def test_svg_both_languages(self):
        for language in ('pt', 'en'):
            for metrics in (None, {'merged': 0, 'reviewed': 12, 'repositories': 1234}):
                svg = analytics.render(metrics, date(2026, 10, 15), 'yada071', language)
                root = ET.fromstring(svg)
                self.assertEqual(root.get('viewBox'), '0 0 1200 256')
                self.assertIn('prefers-reduced-motion', svg)
                self.assertEqual(svg.count('class="edge-light"'), 3)
                self.assertEqual(svg.count('class="metric"'), 3)
                self.assertNotIn('http://github', svg)
                self.assertNotIn('calendar', svg)
                self.assertIn('—' if metrics is None else ('1.234' if language == 'pt' else '1,234'), svg)


if __name__ == '__main__':
    unittest.main()
