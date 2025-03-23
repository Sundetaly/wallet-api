# Wallet API

A REST API built with Django REST Framework for managing wallets and transactions.

## Features

- Wallet management (create, read, update, list)
- Transaction management (create, read, list)
- Pagination, sorting, and filtering for all endpoints
- Automatic wallet balance calculation
- Prevention of negative wallet balances
- Complete test coverage with pytest
- Interactive API documentation with Swagger/OpenAPI

## Technical Stack

- Python 3.11+
- Django 4.2
- Django REST Framework
- PostgreSQL database
- Docker & Docker Compose
- pytest for testing
- flake8 for linting

## Models

### Wallet
- `id`: Primary key
- `label`: String field for wallet name
- `balance`: Decimal field (18-digit precision) calculated from transactions
- `created_at`: Date/time when the wallet was created
- `updated_at`: Date/time when the wallet was last updated

### Transaction
- `id`: Primary key
- `wallet_id`: Foreign key to Wallet
- `txid`: Unique auto-generated UUID for the transaction
- `amount`: Decimal field (18-digit precision) for the transaction amount
- `created_at`: Date/time when the transaction was created

## Business Rules

- Transaction amount can be positive or negative
- Wallet balance is automatically calculated as the sum of all transaction amounts
- Wallet balance should NEVER be negative
- Transactions can only be created (never updated or deleted)

## Quick Start Guide

### Prerequisites

- Docker and Docker Compose installed on your system

### Setup and Run

1. Clone the repository:
   ```bash
   git clone https://github.com
   cd wallet-api
   ```

2. Start the services using Docker Compose:
   ```bash
   docker-compose up -d
   ```

3. The API will be available at http://localhost:8000/api/
4. API documentation is available at:
   - Swagger UI: http://localhost:8000/swagger/
   - ReDoc: http://localhost:8000/redoc/

### Running Tests

```bash
docker-compose exec web pytest
```
### Formatting Code (Black)
To automatically format your code to comply with style guidelines:
```bash
docker-compose exec web black .
```
Check Formatting Without Making Changes
```bash
docker-compose exec web black --check .
```

### Running Linter

```bash
docker-compose exec web flake8
```

## API Endpoints

### Wallets

- `GET /api/wallets/` - List all wallets
- `POST /api/wallets/` - Create a new wallet
- `GET /api/wallets/{id}/` - Get a specific wallet
- `PUT /api/wallets/{id}/` - Update a wallet
- `PATCH /api/wallets/{id}/` - Partially update a wallet
- `DELETE /api/wallets/{id}/` - Delete a wallet
- `GET /api/wallets/{id}/transactions/` - Get all transactions for a specific wallet

### Transactions

- `GET /api/transactions/` - List all transactions
- `POST /api/transactions/` - Create a new transaction
- `GET /api/transactions/{id}/` - Get a specific transaction

## Filtering, Searching and Ordering

### Wallets

- Filter by label: `GET /api/wallets/?label=My%20Wallet`
- Search: `GET /api/wallets/?search=wallet`
- Order by: `GET /api/wallets/?ordering=-balance` (descending order by balance)

### Transactions

- Filter by wallet: `GET /api/transactions/?wallet=1`
- Filter by txid: `GET /api/transactions/?txid=abc123`
- Search: `GET /api/transactions/?search=abc`
- Order by: `GET /api/transactions/?ordering=-amount` (descending order by amount)

## Pagination

All list endpoints support pagination with the following query parameters:
- `page`: Page number
- `page_size`: Number of items per page (default: 20, max: 100)

Example: `GET /api/wallets/?page=2&page_size=10`