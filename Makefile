.PHONY: dev test smoke-test install clean help

# Default target
help:
	@echo "DifficultAI LiveKit Agent - Available Commands:"
	@echo ""
	@echo "  make dev         - Start the LiveKit agent in development mode"
	@echo "  make smoke-test  - Run smoke test (joins room, prints transcripts)"
	@echo "  make test        - Run all tests"
	@echo "  make install     - Install dependencies"
	@echo "  make clean       - Clean up temporary files"
	@echo ""
	@echo "Requirements:"
	@echo "  - Set up .env file with LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, OPENAI_API_KEY"
	@echo "  - Install dependencies: make install"
	@echo ""

# Start the LiveKit agent in development mode
dev:
	@echo "Starting DifficultAI LiveKit agent..."
	python -m apps.livekit_agent dev

# Run smoke test
smoke-test:
	@echo "Running smoke test..."
	python apps/livekit_agent/smoke_test.py

# Run all tests
test:
	@echo "Running test suite..."
	python -m unittest discover -p "test_*.py" -v

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

# Clean up
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "scorecard_*.json" -delete
	@echo "Clean complete"
