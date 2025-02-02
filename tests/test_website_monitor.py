"""
Unit tests for website monitor
"""

import unittest
from unittest.mock import Mock, patch
import asyncio
from datetime import datetime
from website_monitor import WebsiteMonitor
from database import Database

class TestWebsiteMonitor(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.mock_db = Mock(spec=Database)
        self.monitor = WebsiteMonitor(self.mock_db)
    
    def test_calculate_momentum(self):
        """Test momentum calculation"""
        # Test case 1: High volume relative to market cap
        token_data = {
            'price': 1.0,
            'volume_24h': 1000000,
            'market_cap': 1000000,
            'listed_on_major_exchange': True
        }
        score = self.monitor._calculate_momentum(token_data)
        self.assertGreaterEqual(score, 0.8)
        
        # Test case 2: Low volume relative to market cap
        token_data = {
            'price': 1.0,
            'volume_24h': 10000,
            'market_cap': 1000000,
            'listed_on_major_exchange': False
        }
        score = self.monitor._calculate_momentum(token_data)
        self.assertLessEqual(score, 0.3)
        
        # Test case 3: Missing data
        token_data = {
            'price': 0,
            'volume_24h': 0,
            'market_cap': 0
        }
        score = self.monitor._calculate_momentum(token_data)
        self.assertEqual(score, 0.0)
    
    def test_calculate_social_score(self):
        """Test social score calculation"""
        # Test case 1: All social elements present
        token_data = {
            'website': 'https://example.com',
            'whitepaper_url': 'https://example.com/whitepaper',
            'social_links': {
                'twitter': 'https://twitter.com/example',
                'telegram': 'https://t.me/example'
            }
        }
        score = self.monitor._calculate_social_score(token_data)
        self.assertEqual(score, 1.0)
        
        # Test case 2: Some social elements missing
        token_data = {
            'website': 'https://example.com',
            'social_links': {}
        }
        score = self.monitor._calculate_social_score(token_data)
        self.assertEqual(score, 0.3)
        
        # Test case 3: No social elements
        token_data = {
            'website': '',
            'social_links': {}
        }
        score = self.monitor._calculate_social_score(token_data)
        self.assertEqual(score, 0.0)
    
    def test_calculate_risk_score(self):
        """Test risk score calculation"""
        # Test case 1: Low risk
        token_data = {
            'website': 'https://example.com',
            'social_links': {'twitter': 'https://twitter.com/example'},
            'liquidity': 200000
        }
        score = self.monitor._calculate_risk_score(token_data)
        self.assertLessEqual(score, 0.2)
        
        # Test case 2: Medium risk
        token_data = {
            'website': 'https://example.com',
            'social_links': {},
            'liquidity': 50000
        }
        score = self.monitor._calculate_risk_score(token_data)
        self.assertGreaterEqual(score, 0.5)
        
        # Test case 3: High risk
        token_data = {
            'website': '',
            'social_links': {},
            'liquidity': 10000
        }
        score = self.monitor._calculate_risk_score(token_data)
        self.assertGreaterEqual(score, 0.8)
    
    @patch('website_monitor.BeautifulSoup')
    def test_parse_coinmarketcap(self, mock_bs):
        """Test CoinMarketCap parsing"""
        # Mock BeautifulSoup response
        mock_soup = Mock()
        mock_bs.return_value = mock_soup
        
        # Mock table row
        mock_row = Mock()
        mock_row.select_one.side_effect = lambda x: Mock(
            text=Mock(
                strip=Mock(return_value={
                    '.symbol': 'TEST',
                    '.name': 'Test Token',
                    '.price': '$1.00',
                    '.market-cap': '$1000000',
                    '.chain': 'ETH'
                }.get(x, ''))
            )
        )
        mock_soup.select.return_value = [mock_row]
        
        # Test parsing
        tokens = asyncio.run(self.monitor._parse_coinmarketcap('<html></html>'))
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0]['symbol'], 'TEST')
        self.assertEqual(tokens[0]['name'], 'Test Token')
        self.assertEqual(tokens[0]['price'], 1.0)
        self.assertEqual(tokens[0]['market_cap'], 1000000)
        self.assertEqual(tokens[0]['chain'], 'ETH')
    
    def test_process_new_tokens(self):
        """Test token processing"""
        tokens = [{
            'symbol': 'TEST',
            'name': 'Test Token',
            'price': 1.0,
            'market_cap': 1000000,
            'chain': 'ETH',
            'website': 'https://example.com',
            'social_links': {'twitter': 'https://twitter.com/example'},
            'liquidity': 200000
        }]
        
        # Test processing
        asyncio.run(self.monitor._process_new_tokens('coinmarketcap', tokens))
        
        # Verify database calls
        self.mock_db.store_new_token.assert_called_once()
        self.mock_db.store_token_analysis.assert_called_once()
        
        # Verify alert generation for high opportunity
        analysis_call = self.mock_db.store_token_analysis.call_args[0][0]
        if analysis_call['opportunity_score'] >= 0.7:
            self.mock_db.store_alert.assert_called_once()

if __name__ == '__main__':
    unittest.main()
