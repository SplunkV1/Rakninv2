# AGE BYPASSER TOOLS

## Overview

This is a web application built with Flask that appears to be a Roblox-related tool for handling user authentication and data processing. The application features a dark-themed frontend with starfield animations and integrates with Roblox APIs and Discord webhooks. The system is designed to validate Roblox cookies, fetch user information, automatically detect premium items in user inventories, and send notifications based on user account properties.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Single Page Application**: Uses vanilla HTML/CSS/JavaScript with a dark space-themed design
- **Responsive Design**: Mobile-first approach with viewport meta tags and flexible layouts
- **Animation System**: CSS keyframe animations for background starfield effects and visual polish
- **Form Handling**: Client-side form processing for user input collection

### Backend Architecture
- **Flask Framework**: Lightweight Python web framework serving as the main application server
- **RESTful API Design**: HTTP endpoints for handling client requests and data processing
- **Background Processing**: Threading implementation for non-blocking Discord webhook notifications
- **Cookie Processing**: Automated cleaning and validation of Roblox authentication cookies
- **External API Integration**: Direct communication with Roblox APIs for user data retrieval

### Data Processing
- **Cookie Validation**: Multi-step validation process including warning prefix removal and API verification
- **User Information Extraction**: Real-time fetching of Roblox user profiles and account properties
- **Automatic Premium Item Detection**: Inventory API integration to automatically detect Korblox Deathspeaker (ID: 139607718) and Headless items (IDs: 134082579, 15093053680) without user input
- **Yearly Spending Analysis**: Transaction totals API integration to fetch user's Robux spending over the past year
- **Notification Routing**: Conditional webhook sending based on automatically detected account properties

### Deployment Configuration
- **Vercel Integration**: Cloud deployment setup with Python runtime configuration
- **Environment Management**: Secure handling of sensitive configuration through environment variables
- **Static File Serving**: Direct serving of frontend assets through Flask

## External Dependencies

### Core Framework Dependencies
- **Flask 2.3.3**: Web application framework and HTTP server
- **Requests 2.31.0**: HTTP client library for external API communications
- **Python-dotenv**: Environment variable management for configuration
- **Gunicorn**: WSGI HTTP server for production deployment

### Database Dependencies
- **Flask-SQLAlchemy**: ORM layer for database interactions (configured but not actively used)
- **Psycopg2-binary**: PostgreSQL adapter for Python database connections

### Third-Party Services
- **Roblox User API**: User authentication validation and profile data retrieval
- **Roblox Inventory API**: Automatic detection of premium items in user inventories
- **Roblox Economy API**: Transaction history and spending data retrieval
- **Discord Webhooks**: Real-time notification system for account events with enhanced embed formatting
- **Vercel Platform**: Cloud hosting and deployment infrastructure

### Development Tools
- **Node.js Package Management**: Package.json configuration for development dependencies
- **Flask Development Server**: Local development and testing environment

The application is architected as a lightweight web service that bridges Roblox user authentication with Discord notifications, emphasizing real-time processing and external service integration while maintaining a clean separation between frontend presentation and backend data processing.