# Personal Portfolio Tracker

A zero-setup Python/CSV web app to track your stock positions from screenshots. Upload images, let your chosen LLM extract stock positions, and view/update your holdings—all without OCR services, databases, or logins.

## Features

- **Upload Screenshots**: Extract stock positions directly from screenshots using AI
- **Multiple Portfolios**: Tag positions by broker, account type, or any custom label
- **Live Price Data**: View current values using free stock price APIs
- **Filtering & Aggregation**: Group by symbol or filter by tag
- **AI Chat**: Ask questions about your portfolio and get AI-powered insights
- **No Database Setup**: All data stored in simple CSV files

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/portfolio-tracker.git
   cd portfolio-tracker
   ```

2. Install the requirements:
   ```
   pip install -r requirements.txt
   ```

3. Set up API keys (create a `.env` file in the root directory):
   ```
   # Choose one of these LLM providers (Gemini is the default)
   LLM_BACKEND=gemini  # or "openai" or "anthropic"
   
   # API keys based on your chosen provider
   GEMINI_API_KEY=your_gemini_api_key
   OPENAI_API_KEY=your_openai_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   
   # Optional: Choose price data provider (defaults to yfinance)
   PRICE_PROVIDER=yfinance  # or "alpha_vantage" or "iex_cloud"
   ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key
   IEX_CLOUD_API_KEY=your_iex_cloud_api_key
   ```

## Usage

1. Start the app:
   ```
   python app.py
   ```

2. Open your browser to [http://localhost:8000](http://localhost:8000)

3. Upload portfolio screenshots:
   - Provide a tag (e.g., "Robinhood-IRA", "Fidelity-Taxable")
   - Upload a screenshot of your positions
   - The app will extract symbols and share counts

4. View your portfolio:
   - See current prices and values
   - Filter by tag or group by symbol
   - Use the chat feature to ask questions about your portfolio

## API Endpoints

- **GET `/`**: Main web interface
- **POST `/upload`**: Upload a screenshot with tag
- **POST `/update`**: Update positions from screenshot (alias for `/upload`)
- **GET `/positions`**: Get current portfolio data with filters
- **PATCH `/edit`**: Manually edit a position
- **POST `/chat`**: Ask questions about your portfolio

## Data Storage

- **holdings.csv**: Stores all position data
- **images/**: Stores uploaded screenshots

## Extending

- **Switch LLM**: Set `LLM_BACKEND` environment variable to "gemini" (default), "openai", or "anthropic"
- **Change Price Provider**: Set `PRICE_PROVIDER` to "yfinance", "alpha_vantage", or "iex_cloud"
- **Add New Views**: Extend the HTML template in `templates/index.html`

## License

MIT 