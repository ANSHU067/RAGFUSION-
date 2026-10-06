"""Test configuration and fixtures."""

import pytest


@pytest.fixture
def sample_transcript():
    """Sample transcript data for testing."""
    return [
        {'text': 'Welcome to this video tutorial.', 'start': 0.0, 'duration': 2.5},
        {'text': 'Today we will learn about machine learning.', 'start': 2.5, 'duration': 3.0},
        {'text': 'Machine learning is a subset of artificial intelligence.', 'start': 5.5, 'duration': 3.5},
        {'text': 'It focuses on training algorithms to make predictions.', 'start': 9.0, 'duration': 3.0},
        {'text': 'There are three main types of machine learning.', 'start': 12.0, 'duration': 3.0},
    ]


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing."""
    return {
        'success': True,
        'video_id': 'test_video_123',
        'title': 'Introduction to Machine Learning',
        'author': 'Test Channel',
        'length': 600,
        'views': 10000,
        'description': 'A comprehensive introduction to machine learning concepts.',
        'keywords': ['machine learning', 'AI', 'tutorial'],
    }


@pytest.fixture
def long_text():
    """Generate long text for chunking tests."""
    return " ".join([f"This is sentence number {i}." for i in range(100)])
