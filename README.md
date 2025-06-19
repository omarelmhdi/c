# Telegram PDF Bot 🤖📄

A professional, multilingual Telegram bot for comprehensive PDF editing operations. Built with Python, FastAPI, and python-telegram-bot v20+, designed for seamless deployment on Vercel.

## ✨ Features

### 📄 PDF Operations
- **Merge PDFs** - Combine multiple PDF files into one
- **Split PDF** - Split by specific pages or page ranges
- **Delete Pages** - Remove unwanted pages from PDFs
- **Rotate Pages** - Rotate pages by 90°, 180°, or 270°
- **Reorder Pages** - Rearrange pages in custom order
- **Compress PDF** - Reduce file size with quality options
- **Extract Text** - Extract all text content from PDFs
- **Extract Images** - Extract embedded images from PDFs
- **Convert PDF to Images** - Convert each page to image format
- **Convert Images to PDF** - Create PDF from multiple images
- **Rename Files** - Custom filename for output files

### 🌍 Multilingual Support
- **English** and **Arabic** interface
- Auto language detection from user messages
- Fallback language selection
- RTL support for Arabic text

### 👨‍💼 Admin Panel
- User statistics and analytics
- Broadcast messages to all users
- Error logs monitoring
- System information dashboard
- User activity tracking

### 🔧 Technical Features
- **Webhook-based** (no polling) for better performance
- **Async/await** throughout for scalability
- **Automatic cleanup** of temporary files
- **Error handling** with user-friendly messages
- **File size limits** and validation
- **Session management** for multi-step operations

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Telegram Bot Token (from @BotFather)
- Vercel account (for deployment)

### Local Development

1. **Clone the repository**
```bash
git clone <repository-url>
cd telegram-pdf-bot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Environment setup**
Create a `.env` file:
```env
BOT_TOKEN=your_bot_token_here
WEBHOOK_URL=https://your-domain.vercel.app
ADMIN_IDS=123456789,987654321
DEBUG=True
```

4. **Run locally**
```bash
python main.py
```

The bot will start on `http://localhost:8000`

### 🌐 Deployment on Vercel

1. **Install Vercel CLI**
```bash
npm install -g vercel
```

2. **Login to Vercel**
```bash
vercel login
```

3. **Deploy**
```bash
vercel --prod
```

4. **Set environment variables**
In Vercel dashboard, add:
- `BOT_TOKEN`: Your Telegram bot token
- `WEBHOOK_URL`: Your Vercel app URL
- `ADMIN_IDS`: Comma-separated admin user IDs

5. **Set webhook**
After deployment, the webhook will be automatically configured.

## 📁 Project Structure

```
project/
│
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── vercel.json            # Vercel deployment configuration
├── README.md              # This file
│
├── handlers/              # Telegram bot handlers
│   ├── start.py          # Start command and main menu
│   ├── merge.py          # PDF merging functionality
│   ├── split.py          # PDF splitting functionality
│   ├── delete_pages.py   # Page deletion functionality
│   ├── rotate.py         # Page rotation functionality
│   ├── reorder.py        # Page reordering functionality
│   ├── compress.py       # PDF compression functionality
│   ├── extract_text.py   # Text extraction functionality
│   ├── extract_images.py # Image extraction functionality
│   ├── convert.py        # PDF/Image conversion functionality
│   ├── admin.py          # Admin panel functionality
│   └── language.py       # Language selection functionality
│
├── utils/                 # Utility modules
│   ├── pdf_tools.py      # PDF processing utilities
│   ├── i18n.py           # Internationalization utilities
│   └── cleanup.py        # File cleanup utilities
│
├── config/               # Configuration
│   └── settings.py       # Application settings
│
├── locales/              # Language files
│   ├── en.json          # English translations
│   └── ar.json          # Arabic translations
│
└── templates/            # Message templates
    └── messages.py       # Message formatting utilities
```

## 🎯 Usage

### Basic Commands
- `/start` - Initialize bot and show main menu
- `/help` - Show help information
- `/cancel` - Cancel current operation
- `/admin` - Access admin panel (admin only)

### PDF Operations Workflow

1. **Send PDF file** to the bot
2. **Choose operation** from the inline keyboard
3. **Follow prompts** for operation-specific inputs
4. **Receive processed file** with optional renaming

### Admin Features

Admins can access:
- **User Statistics**: Total users, operations, errors
- **Broadcast**: Send messages to all users
- **Error Logs**: Monitor and debug issues
- **System Info**: Server status and cleanup

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|----------|
| `BOT_TOKEN` | Telegram bot token | Yes | - |
| `WEBHOOK_URL` | Base URL for webhook | Yes | - |
| `ADMIN_IDS` | Comma-separated admin user IDs | Yes | - |
| `DEBUG` | Enable debug mode | No | `False` |
| `MAX_FILE_SIZE` | Maximum file size in bytes | No | `20MB` |
| `MAX_PDF_PAGES` | Maximum PDF pages to process | No | `100` |
| `TEMP_DIR` | Temporary files directory | No | `/tmp` |

### Customization

#### Adding New Languages
1. Create new JSON file in `locales/` (e.g., `fr.json`)
2. Add language code to `SUPPORTED_LANGUAGES` in `config/settings.py`
3. Update language selection in `handlers/language.py`

#### Modifying PDF Operations
1. Edit functions in `utils/pdf_tools.py`
2. Update corresponding handlers in `handlers/`
3. Add new translations if needed

## 🔧 Dependencies

### Core Dependencies
- **FastAPI**: Web framework for webhook handling
- **python-telegram-bot**: Telegram Bot API wrapper
- **PyPDF2**: PDF manipulation library
- **PyMuPDF**: Advanced PDF processing
- **Pillow**: Image processing
- **ReportLab**: PDF generation

### Optional Dependencies
- **pdf2image**: Better PDF to image conversion
- **pytesseract**: OCR capabilities
- **poppler-utils**: PDF utilities (system dependency)

## 🐛 Troubleshooting

### Common Issues

1. **Webhook not receiving updates**
   - Check WEBHOOK_URL is correct
   - Verify SSL certificate is valid
   - Check Vercel function logs

2. **PDF processing errors**
   - Ensure file size is within limits
   - Check PDF is not password protected
   - Verify PyMuPDF installation

3. **Memory issues**
   - Reduce MAX_PDF_PAGES
   - Implement file streaming for large files
   - Monitor Vercel function memory usage

### Debug Mode

Enable debug mode by setting `DEBUG=True` in environment variables:
- Detailed logging
- Error stack traces
- Development server reload

## 📊 Monitoring

### Health Checks
- `GET /` - Basic status
- `GET /health` - Detailed health check
- `GET /stats` - Bot statistics

### Logging
- Structured logging with timestamps
- Error tracking with user context
- Admin panel for log viewing

## 🔒 Security

### Best Practices
- Admin access restricted by user ID
- File size and type validation
- Temporary file cleanup
- No sensitive data in logs
- Environment variable protection

### Rate Limiting
- Implement rate limiting for heavy operations
- User session management
- File processing queues

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Add type hints
- Write comprehensive docstrings
- Include error handling
- Add tests for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Excellent Telegram Bot API wrapper
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) - Powerful PDF processing library
- [FastAPI](https://github.com/tiangolo/fastapi) - Modern web framework
- [Vercel](https://vercel.com) - Seamless deployment platform

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check existing documentation
- Review troubleshooting section

---

**Made with ❤️ for the Telegram community**