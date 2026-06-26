# 🛒 MarketHub - Multi-Vendor Ecommerce Platform

> A complete Multi-Vendor Ecommerce Platform developed using Django, enabling customers, vendors, and administrators to interact through a secure, scalable, and feature-rich online marketplace.

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![Django](https://img.shields.io/badge/Django-5.x-success.svg)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-purple.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

# 📖 Overview

MarketHub is a comprehensive Multi-Vendor Ecommerce Platform developed as a **Bachelor of Science in Computer Science (BSCS) Final Year Project**.

The platform allows multiple vendors to register and manage their own online stores while customers can browse products, place orders, track deliveries, review products, and securely complete purchases.

The system includes dedicated dashboards for:

- Customers
- Vendors
- Administrators

along with secure authentication, order management, payment handling, coupon management, vendor withdrawals, email notifications, QR/Barcode receipt generation, and much more.

---

# ✨ Key Features

## 👤 Customer Module

- Customer Registration
- Email Verification
- Secure Login
- Password Reset
- Profile Management
- Browse Products
- Search Products
- Category Filtering
- Shopping Cart
- Apply Coupons
- Checkout
- Order Confirmation
- Order Tracking
- Order History
- Payment History
- Product Reviews
- Product Ratings
- Product Questions
- Reorder Previous Orders

---

## 🏪 Vendor Module

- Vendor Registration
- Vendor Dashboard
- Product Management
- Product Variants
- Inventory Management
- Stock Updates
- Manage Customer Orders
- Shipping Updates
- Earnings Dashboard
- Withdrawal Requests
- Payment Details
- Vendor Store
- Vendor Profile Management

---

## 🛠 Admin Module

- Admin Dashboard
- Product Management
- Vendor Management
- Customer Management
- Coupon Management
- Order Management
- Withdrawal Management
- Vendor Payment Verification
- CSV Export
- PDF Export
- Payment Monitoring

---

## 🛍 Shopping Features

- Product Categories
- Featured Products
- Related Products
- Product Variants
- Color Variants
- Size Variants
- AJAX Product Filtering
- Product Quick View
- Search Functionality
- Pagination
- Wishlist Ready Architecture

---

## 💳 Checkout & Payment

- Complete Checkout System
- Billing Information Validation
- Card Validation
- Visa & MasterCard Support
- Payment Records
- Secure Order Creation
- Automatic Cart Clearing
- Order Confirmation Email

---

## 📦 Order Management

- Order History
- Order Details
- Order Tracking
- Shipping Status
- Courier Information
- Tracking Number
- Estimated Delivery
- QR Code Receipt
- Barcode Receipt

---

## 💰 Vendor Earnings

- Automatic Earnings Calculation
- Available Balance
- Withdrawal Requests
- Withdrawal Approval Workflow
- Vendor Payment Verification
- Withdrawal History

---

## 🎟 Coupon System

- Coupon Creation
- Coupon Expiry
- Active/Inactive Coupons
- Usage Limits
- Customer Validation
- Discount Calculation

---

## 📧 Email Notifications

The system automatically sends emails for:

- Account Verification
- Password Reset
- Password Change
- Order Confirmation
- Contact Form
- Withdrawal Approval
- Withdrawal Rejection
- Vendor Notifications

---

# 🏗 System Architecture

```
                 +------------------+
                 |     Customer     |
                 +------------------+
                          |
                          |
                 Django Authentication
                          |
          --------------------------------
          |              |               |
          |              |               |
      Customer        Vendor         Administrator
      Dashboard      Dashboard        Dashboard
          |              |               |
          |              |               |
     Shopping      Product CRUD     System Control
          |              |               |
          --------------------------------
                    Django ORM
                         |
                     SQLite Database
```

---

# 🛠 Technology Stack

## Backend

- Python
- Django
- Django ORM

## Frontend

- HTML5
- CSS3
- Bootstrap 5
- JavaScript
- AJAX

## Database

- SQLite

## Email

- SMTP Email Backend

## Libraries

- qrcode
- python-barcode
- Pillow
- ReportLab

---

# 📂 Project Structure

```
MarketHub/
│
├── api/
│   ├── admin.py
│   ├── adminviews.py
│   ├── authviews.py
│   ├── cartviews.py
│   ├── checkoutviews.py
│   ├── contactviews.py
│   ├── paymentviews.py
│   ├── productsviews.py
│   ├── shopviews.py
│   ├── userdashviews.py
│   ├── vendorviews.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   ├── models.py
│   └── signals.py
│
├── templates/
│   ├── admin/
│   ├── auth/
│   ├── customers/
│   ├── vendor/
│   ├── purchase/
│   ├── products/
│   ├── partials/
│   ├── emails/
│   └── includes/
│
├── media/
├── static/
├── manage.py
└── requirements.txt
```

---

# 📊 Modules

- Authentication
- Product Management
- Vendor Management
- Customer Management
- Shopping Cart
- Checkout
- Payment
- Coupons
- Reviews
- Ratings
- Product Questions
- Order Tracking
- Vendor Earnings
- Withdrawals
- QR Receipt
- Barcode Receipt
- Email System
- Contact System

---

# 🔒 Security Features

- Django Authentication
- Login Required Views
- Admin Authorization
- Vendor Authorization
- Form Validation
- CSRF Protection
- Email Verification
- Password Encryption
- Secure Payment Storage
- Session Based Cart

---

# 📷 Screenshots

Add screenshots here after deployment.

```
Home Page

Customer Dashboard

Vendor Dashboard

Admin Dashboard

Product Details

Shopping Cart

Checkout

Order Tracking

Vendor Earnings

Admin Orders
```

---

# 🚀 Installation

## Clone Repository

```bash
git clone https://github.com/yourusername/MarketHub.git

cd MarketHub
```

---

## Create Virtual Environment

```bash
python -m venv venv
```

Windows

```bash
venv\Scripts\activate
```

Linux / Mac

```bash
source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Run Migrations

```bash
python manage.py makemigrations

python manage.py migrate
```

---

## Create Superuser

```bash
python manage.py createsuperuser
```

---

## Run Server

```bash
python manage.py runserver
```

Open

```
http://127.0.0.1:8000/
```

---

# 📈 Future Enhancements

- Stripe Integration
- JazzCash Integration
- EasyPaisa Integration
- PayPal
- Product Recommendations
- AI Chatbot
- Sales Analytics
- REST API
- Mobile App
- Real-Time Notifications
- Multi-language Support
- Docker Deployment
- PostgreSQL Deployment

---

# 🎓 Academic Information

**Project Title**

MarketHub - Multi-Vendor Ecommerce Platform

**Degree**

Bachelor of Science in Computer Science (BSCS)

**Project Type**

Final Year Project (FYP)

---

# 👨‍💻 Developer

**Muhammad Haseeb**

Software Developer

📧 mhasseb3112@example.com

📍 Bahawalpur, Pakistan

GitHub:
https://github.com/MuhammadHaseeb3112

LinkedIn:
(Add Your LinkedIn)

---

# 📄 License

This project was developed for educational purposes as a BSCS Final Year Project.

---

# ⭐ Acknowledgements

Special thanks to:

- Django Documentation
- Bootstrap
- Python Community
- Stack Overflow
- Open Source Contributors

---

## ⭐ If you found this project useful, don't forget to star the repository.
