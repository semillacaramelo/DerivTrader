# Deriv Trading Bot with 3 MA Strategy

A modular trading bot for Deriv.com implementing a three Moving Average strategy for automated trading. See [Technical Documentation](docs/documentation.md) for detailed implementation details.

## Quick Start

1. **Prerequisites**
   - Python 3.10+
   - Deriv.com account (demo/real)
   - API tokens from Deriv.com

2. **Installation**
   ```bash
   git clone [your-repo-url]
   cd DerivTrader
   python -m venv traderenv
   source traderenv/bin/activate  # On Windows: traderenv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configuration**
   ```bash
   cp config/.env.example .env
   ```
   Edit `.env` with your API tokens and settings. See [Environment Configuration](docs/documentation.md#environment-configuration) for details.

4. **Run**
   ```bash 
   # Start trading
   python __main__.py

   # Run tests
   pytest tests/
   ```

## Project Structure
```
trading_bot/
├── config/             # Configuration files and templates
├── docs/              # Documentation
├── modules/           # Core functionality
├── tests/            # Test suites
└── utils/            # Helper utilities
```

## Development

- [Development Guidelines](docs/documentation.md#development-guidelines)
- [API Details](docs/documentation.md#api-details) 
- [Troubleshooting Guide](docs/documentation.md#troubleshooting)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes with clear messages
4. Write tests for new features
5. Submit a Pull Request

See [Development Guidelines](docs/documentation.md#development-guidelines) for code style and testing requirements.

## License

MIT License - See LICENSE file for details.

## Disclaimer

Trading involves risk of loss. This software is for educational purposes only. Test thoroughly in a demo account first. Past performance does not guarantee future results.