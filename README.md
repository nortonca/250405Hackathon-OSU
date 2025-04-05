# Flask + Tailwind + SocketIO Template

A simple web application template using Flask, Tailwind CSS, and Socket.IO for real-time communication.

## Features

- Flask web server
- Tailwind CSS for styling
- Socket.IO for real-time communication
- Simple chat interface

## Installation

1. Clone this repository
2. Install the requirements:

```bash
pip install -r requirements.txt
```

## Running the Application

Start the Flask server:

```bash
python app.py
```

The application will be available at http://localhost:5000

## Project Structure

```
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── static/             # Static assets
│   ├── css/            # CSS stylesheets
│   │   └── main.css    # Custom CSS
│   └── js/             # JavaScript files
│       └── main.js     # Client-side Socket.IO code
└── templates/          # HTML templates
    └── index.html      # Main page template
```

## Customization

- Modify `templates/index.html` to change the UI
- Edit `static/js/main.js` to customize Socket.IO behavior
- Update `static/css/main.css` for custom styling beyond Tailwind
- Extend `app.py` to add more routes and Socket.IO events 