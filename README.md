# ⚡ Gigs360

> **The Operating System for Kenyan Creatives.**
> Streamline your photography, event planning, or agency business with smart inventory tracking, conflict-free scheduling, and automated finance.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0-092E20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?style=for-the-badge&logo=bootstrap)](https://getbootstrap.com/)
[![Status](https://img.shields.io/badge/Status-Beta-orange?style=for-the-badge)](https://github.com/)

---

## 📖 Table of Contents
- [About](#-about)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🚀 About
**Gigs360** is a full-stack SaaS platform designed to solve the chaos of the creative gig economy. It moves businesses away from spreadsheets and WhatsApp bookings into a centralized, crash-proof system.

Whether you are a solo photographer or a large event agency, Gigs360 handles the "boring stuff"—tracking lenses, generating quotes, and flagging scheduling conflicts—so you can focus on the creative work.

---

## ✨ Key Features

### 📦 **1. The Gear Locker (Inventory)**
* **Asset Tracking:** Manage cameras, cables, and lighting with status tracking (Available vs. Rented).
* **Rapid Scanner:** Generate and scan unique QR Codes for every item to check them In/Out instantly.
* **Safe-Links:** Smart notifications redirect you safely even if an item is deleted.

### 📅 **2. Event Operations**
* **Smart Calendar:** Book gigs with start/end times.
* **Conflict Detection:** The system prevents double-booking. You cannot book a lens for a wedding if it's already at a corporate shoot.
* **Digital Manifests:** Automatically generate packing lists for every event.

### 💰 **3. Smart Invoicing & Finance**
* **Professional Docs:** Generate branded PDF Quotes and Invoices (KK Photography style) in one click.
* **Auto-Fill:** "Import from Manifest" pulls all booked gear into the invoice instantly.
* **M-Pesa Integration:** (In Progress) Trigger STK Push payments directly from the dashboard.

### 🔔 **4. The Notification Center**
* **Real-time Alerts:** Get notified about security changes, new bookings, and inventory updates.
* **Persistent History:** A built-in notification tray tracks all system activity.

---

## 🛠 Tech Stack
* **Backend:** Django (Python)
* **Frontend:** Bootstrap 5, JavaScript (Vanilla), Jinja2 Templates
* **Database:** SQLite (Dev) / PostgreSQL (Prod)
* **PDF Engine:** `xhtml2pdf`
* **Payments:** `django-daraja` (Safaricom M-Pesa API)

---

## ⚡ Getting Started

Follow these steps to run Gigs360 locally on your machine.

### Prerequisites
* Python 3.10 or higher
* Git

### Installation

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/yourusername/gigs360.git](https://github.com/yourusername/gigs360.git)
    cd gigs360
    ```

2.  **Create a Virtual Environment**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Apply Database Migrations**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5.  **Collect Static Files** (Important for PDF styling)
    ```bash
    python manage.py collectstatic
    ```

6.  **Run the Server**
    ```bash
    python manage.py runserver
    ```

> Visit `http://127.0.0.1:8000/` in your browser.

---

## 📂 Project Structure

```text
Gigs360/
├── core/               # User Auth, Dashboard, Notifications, Signals
├── inventory/          # Gear management, QR Scanning logic
├── events/             # Gig booking, PDF Generation, Conflict logic
├── finance/            # M-Pesa Transactions, Receipts
├── templates/          # HTML files (Bootstrap 5)
├── static/             # CSS, JS, Images
└── radagig/            # Main project settings