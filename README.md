# Algo Trader Annual Report Analyzer

A comprehensive full-stack application for algorithmic trading and automated annual report analysis using AI-powered insights.

## 🚀 Features

### Backend (FastAPI)
- **Annual Report Analysis**: AI-powered analysis of NSE-listed company annual reports using multiple LLM models
- **Backtesting Engine**: Comprehensive backtesting framework with multiple technical indicators
- **Custom Strategy Creation**: Build and deploy custom trading strategies with Python code
- **Real-time Data**: Integration with NSE India for live market data
- **Multi-Model Racing**: Parallel analysis using various AI models via OpenRouter API

### Frontend (React + Vite)
- **Interactive Dashboard**: Modern UI for strategy management and backtesting
- **Report Visualization**: Display AI-generated analysis reports
- **Strategy Builder**: User-friendly interface for creating custom strategies
- **Real-time Updates**: Live data visualization and trading signals

## 🛠️ Tech Stack

### Backend
- **Python 3.8+**
- **FastAPI** - High-performance web framework
- **OpenAI API** - AI model integration
- **pdfplumber** - PDF text extraction
- **pandas/numpy** - Data analysis
- **yfinance** - Financial data (optional)

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Axios** - HTTP client
- **Chart.js** - Data visualization

## 📋 Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- Git

## 🚀 Installation

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/dkmishra2407/ALGO-TRADER-ANNUAL-REPORT-ANALYZER.git
   cd ALGO-TRADER-ANNUAL-REPORT-ANALYZER
   ```

2. **Navigate to Backend directory**
   ```bash
   cd Backend
   ```

3. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**
   Create a `.env` file in the Backend directory:
   ```env
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   ```

6. **Run the backend server**
   ```bash
   python main.py
   ```
   The API will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to Frontend directory**
   ```bash
   cd ../Frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm run dev
   ```
   The frontend will be available at `http://localhost:5173`

## 📖 Usage

### Annual Report Analysis

1. **Upload PDF**: Send a POST request to `/analyze` with the annual report PDF
2. **AI Analysis**: The system will analyze the report using multiple AI models
3. **Get Results**: Receive structured financial analysis with key metrics

### Backtesting

1. **Configure Strategy**: Use predefined strategies or create custom ones
2. **Set Parameters**: Define backtesting period, initial capital, etc.
3. **Run Backtest**: Execute the strategy against historical data
4. **View Results**: Analyze performance metrics and risk indicators

### Custom Strategy Creation

1. **Write Python Code**: Create strategy logic using the provided framework
2. **Register Strategy**: Add the strategy to the system
3. **Test & Deploy**: Backtest and deploy for live trading

## 🔌 API Endpoints

### Analysis Endpoints
- `POST /analyze` - Analyze annual report PDF
- `GET /strategies` - List available trading strategies

### Backtesting Endpoints
- `POST /backtest` - Run backtesting simulation
- `POST /custom-strategy` - Create and register custom strategy

### Data Endpoints
- `GET /market-data/{symbol}` - Get real-time market data

## 📊 Available Strategies

### Technical Indicators
- **SMA (Simple Moving Average)**
- **EMA (Exponential Moving Average)**
- **RSI (Relative Strength Index)**
- **MACD (Moving Average Convergence Divergence)**
- **Bollinger Bands**

### Custom Strategies
- Support for user-defined Python-based strategies
- Integration with technical indicators
- Risk management features

## 🔧 Configuration

### Environment Variables
- `OPENROUTER_API_KEY` - Your OpenRouter API key
- `OPENROUTER_BASE_URL` - OpenRouter API base URL

### Model Configuration
The system supports multiple AI models for analysis:
- DeepSeek models
- Meta Llama models
- Mistral models
- And many more via OpenRouter

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. Not intended for actual trading or investment decisions. Always consult with financial professionals before making investment choices.

## 📞 Support

For questions or issues:
- Create an issue on GitHub
- Contact the maintainers

## 🔄 Future Enhancements

- [ ] Live trading integration
- [ ] Advanced risk management
- [ ] Portfolio optimization
- [ ] Machine learning-based predictions
- [ ] Mobile app companion</content>
<parameter name="filePath">c:\Users\Devansh\Desktop\algo trader\README.md