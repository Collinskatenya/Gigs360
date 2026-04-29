Markdown
# ⚡ Gigs360

> **The Operating System for Kenyan Creatives.**
> Streamline your photography, event planning, or agency business with smart inventory tracking, conflict-free scheduling, and automated finance.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0-092E20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?style=for-the-badge&logo=bootstrap)](https://getbootstrap.com/)
[![Status](https://img.shields.io/badge/Status-Beta-orange?style=for-the-badge)](#)

---

## 📖 Table of Contents
- [About](#-about)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Configuration](#️-configuration)
- [Basic Usage](#-basic-usage)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🚀 About
**Gigs360** is a full-stack SaaS platform designed to solve the chaos of the creative gig economy. It moves businesses away from fragmented spreadsheets and WhatsApp bookings into a centralized, crash-proof system.

Whether you are a solo photographer or a large event agency, Gigs360 handles the "boring stuff"—tracking lenses, generating quotes, and flagging scheduling conflicts—so you can focus entirely on your creative work.

---

## ✨ Key Features

### 📦 1. The Gear Locker (Inventory & Hardware Tracking)
* **Asset Tracking:** Manage cameras, cables, and lighting with live status tracking (Available vs. Rented).
* **Rapid Scanner API:** Generate and scan unique QR Codes for every item to check gear In/Out instantly.
* **Public Discovery Hub:** Publish your gear to a public-facing marketplace for other creatives to rent.

### 📅 2. Event Operations & Booking
* **Smart Calendar:** Book gigs with precise start and end times.
* **Conflict Detection:** Bulletproof database architecture prevents double-booking. You cannot book a lens for a wedding if it is already reserved for a corporate shoot.
* **Digital Manifests:** Automatically generate packing lists for every specific event.

### 💰 3. Smart Invoicing & KYC Finance
* **Professional Docs:** Generate branded, styled PDF Quotes and Invoices (e.g., KK Photography style) in one click.
* **Auto-Fill:** "Import from Manifest" pulls all booked gear and daily rates into the invoice instantly.
* **Sentinel KYC Protocol:** Automated fraud detection validates KRA PINs and IDs to ensure a secure platform environment.
* **M-Pesa Integration (Beta):** Trigger STK Push payments directly from the dashboard.

### 🔔 4. The Notification Center
* **Real-time Alerts:** Get notified about security changes, new bookings, and inventory updates.
* **HQ Broadcasts:** Enterprise-grade messaging system for targeted administrative announcements.

---

## 🛠 Tech Stack
* **Backend:** Django (Python 3.10+)
* **Frontend:** HTML5, Bootstrap 5, Vanilla JavaScript, Jinja2 Templates
* **Database:** SQLite (Development) / PostgreSQL (Production)
* **PDF Engine:** `xhtml2pdf`
* **Payments:** `django-daraja` (Safaricom M-Pesa API)
* **Hardware & Media:** `qrcode`, `Pillow` (Image Processing)

---

## ⚡ Getting Started

Follow these steps to run Gigs360 locally on your machine.

### Prerequisites
* Python 3.10 or higher
* Git
* pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone [https://github.com/yourusername/gigs360.git](https://github.com/yourusername/gigs360.git)
   cd gigs360
Create a Virtual Environment

Bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
Install Dependencies

Bash
pip install -r requirements.txt
Apply Database Migrations

Bash
python manage.py makemigrations
python manage.py migrate
Collect Static Files (Crucial for PDF styling and Bootstrap)

Bash
python manage.py collectstatic
Run the Server

Bash
python manage.py runserver
Visit http://127.0.0.1:8000/ in your browser.

⚙️ Configuration
Gigs360 relies on environment variables for sensitive data. Create a .env file in the root directory (next to manage.py) and configure the following options:

Code snippet
# Django Settings
SECRET_KEY=your_super_secret_django_key_here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Database (Leave blank to default to SQLite in development)
DATABASE_URL=postgres://user:password@localhost:5432/gigs360

# M-Pesa Daraja API
MPESA_ENVIRONMENT=sandbox
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_PASSKEY=your_passkey
MPESA_SHORTCODE=174379
💡 Basic Usage
Complete KYC: Upon registration, navigate to Settings > Identity and submit your details. The Sentinel system will automatically review your profile.

Stock the Locker: Go to Inventory > Add Gear. Upload photos, set your daily rate, and save. The system will auto-generate a printable QR code.

Book a Gig: Navigate to Events > New Gig. Select your dates and assign gear from your locker. The system will warn you of any scheduling overlaps.

Bill the Client: Go to the event dashboard and click Generate Invoice. A branded PDF will be created using your saved company logo and theme color.

📂 Project Structure
Plaintext
Gigs360/
├── core/               # User Auth, Dashboard, Settings, Sentinel KYC, Admin Overrides
├── inventory/          # Gear management, QR Generation, Discovery Hub API
├── events/             # Gig booking, Manifest generation, Conflict logic
├── finance/            # M-Pesa Transactions, PDF Invoicing
├── templates/          # Global HTML files and Base Layouts
├── static/             # CSS, JS, Bootstrap components, Brand Images
├── media/              # User Uploads (Logos, Gear Photos, QR Codes)
└── radagig/            # Main project configuration (settings.py, urls.py)
🛠 Troubleshooting
PDFs are rendering without styling: Ensure you have run python manage.py collectstatic. xhtml2pdf requires absolute paths to static CSS files to render properly.

Images are not uploading: Ensure your HTML templates include enctype="multipart/form-data" in the form tags.

Database Locked Error: If using SQLite in development, concurrent rapid scans might lock the database. Production environments should use PostgreSQL to leverage select_for_update() concurrency control.

M-Pesa Callbacks Failing: If testing locally, Safaricom M-Pesa cannot reach localhost. You must use a tunneling service like Ngrok to expose your local server to the internet.

🤝 Contributing
We welcome contributions from the community to make Gigs360 the ultimate tool for creatives!

Fork the Project

Create your Feature Branch (git checkout -b feature/AmazingFeature)

Commit your Changes (git commit -m 'Add some AmazingFeature')

Push to the Branch (git push origin feature/AmazingFeature)

Open a Pull Request

📄 License
Distributed under the MIT License. See LICENSE for more information.