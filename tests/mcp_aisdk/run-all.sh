#!/bin/bash

echo "🚀 MCP AI SDK Test Client - Full Demo"
echo "===================================="
echo ""

echo "1. Running Tests..."
echo "-------------------"
npm run test:run

echo ""
echo "2. Running Basic Example..."
echo "---------------------------"
npm run example:basic

echo ""
echo "3. Running Performance Benchmarks..."
echo "------------------------------------"
npm run benchmark

echo ""
echo "✅ Demo Complete!"
echo ""
echo "To run individual components:"
echo "  - Tests: npm test"
echo "  - Basic Example: npm run example:basic"
echo "  - AI Example: npm run example:ai"
echo "  - Benchmarks: npm run benchmark"