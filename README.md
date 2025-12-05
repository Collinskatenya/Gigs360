Gigs360 - The OS for African Creatives 🚀

Gigs360 is a comprehensive Business Operating System (BOS) designed to professionalize the fragmented creative industry in Kenya. It unifies POS, Inventory Tracking, and Escrow Payments into a single platform for Photographers, Event Planners, and Rental Houses.

🌟 Key Features

🛡️ Secure Ganji (Escrow): Automated M-Pesa deposits held securely until job completion.

📷 Gear Locker: QR-Code based asset tracking to prevent inventory shrinkage.

📄 Smart Admin: Auto-generation of PDF contracts and invoices.

📊 Analytics: Real-time dashboard for vendor earnings.

🛠️ Tech Stack

Backend: Python 3.13, Django 5.2

Frontend: Bootstrap 5, HTML5, CSS3, JavaScript

Database: SQLite (Dev) / PostgreSQL (Prod)

Integrations: Safaricom Daraja API (Planned Phase 4)

🚀 Local Setup Guide

Follow these steps to get Gigs360 running locally on your machine.

1. Clone the Repository

git clone [https://github.com/YOUR_USERNAME/gigs360.git](https://github.com/YOUR_USERNAME/gigs360.git)
cd POS


2. Create Virtual Environment

# Windows
python -m venv venv
source venv/Scripts/activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate


3. Install Dependencies

pip install -r requirements.txt


4. Configure Environment Variables

Create a file named .env in the root directory (same folder as manage.py) and add your configuration:

SECRET_KEY=your_secret_key_here
DEBUG=True


5. Run Migrations & Server

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver


Visit http://127.0.0.1:8000 to see the Landing Page.

🚧 Development Roadmap

[x] Phase 1: Landing Page & Brand Identity (Complete)

[x] Phase 2: Authentication (Login/Signup with Role Selection)

[ ] Phase 3: Dashboard Logic (Inventory & Booking Models)

[ ] Phase 4: Payments API (M-Pesa Integration)

Built with ❤️ in Nairobi, Kenya.