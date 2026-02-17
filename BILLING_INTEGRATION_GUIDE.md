# Billing System Integration Guide

## Quick Start - 3 Steps to Get Started

### Step 1: Register Routes in app/main.py

Add these imports at the top of the file:

```python
from app.routes.billing import router as billing_router
from app.routes.billing_pages import router as billing_pages_router
```

Add these lines in the route registration section (after other router includes):

```python
# Billing System Routes
app.include_router(billing_router, prefix="/api/billing", tags=["billing"])
app.include_router(billing_pages_router, tags=["billing-pages"])
```

### Step 2: Run Database Migration

Open terminal in the project root and execute:

```bash
alembic upgrade head
```

This will create 4 new tables:
- `material_rates` - Vendor pricing data
- `bills` - Invoice records
- `bill_items` - Line items in bills
- `payments` - Payment records

### Step 3: Verify Installation

Test the API with:

```bash
# Get all bills (should return empty list initially)
curl http://localhost:8000/api/billing/bills

# Check other endpoints
curl http://localhost:8000/api/billing/reports/vendor-payment
```

Access the dashboard:
```
http://localhost:8000/app/billing/dashboard
```

## File Checklist

### Database Models ✅
- [x] `app/models/material_rate.py` - MaterialRate ORM model
- [x] `app/models/bill.py` - Bill ORM model
- [x] `app/models/bill_item.py` - BillItem ORM model
- [x] `app/models/payment.py` - Payment ORM model
- [x] `app/models/__init__.py` - Updated with new imports

### Database Layer ✅
- [x] `app/repositories/billing_repository.py` - 20+ CRUD methods
- [x] `alembic/versions/20260217_01_create_billing_system.py` - Migration file

### API Routes ✅
- [x] `app/routes/billing.py` - 15 API endpoints
- [x] `app/routes/billing_pages.py` - 4 HTML page routes

### Services ✅
- [x] `app/services/billing_reports.py` - Report generation

### Frontend Templates ✅
- [x] `app/templates/billing/bills_management.html` - Dashboard
- [x] `app/templates/billing/bill_detail.html` - Bill details page
- [x] `app/templates/billing/payment_record.html` - Payment form
- [x] `app/templates/billing/billing_reports.html` - Reports page

## API Endpoints Map

### Material Rates
```
POST   /api/billing/rates/create              Create new rate
GET    /api/billing/rates/{material_id}/{vendor_id}  Get current rate
```

### Bills
```
POST   /api/billing/bills/create              Create bill
GET    /api/billing/bills                     List all bills (paginated)
GET    /api/billing/bills/{bill_id}           Get bill details
GET    /api/billing/bills/project/{project_id}  List project bills
PUT    /api/billing/bills/{bill_id}           Update bill
DELETE /api/billing/bills/{bill_id}           Delete bill
```

### Bill Items
```
POST   /api/billing/bills/{bill_id}/add-item        Add item to bill
GET    /api/billing/bills/{bill_id}/items           List bill items
DELETE /api/billing/bills/{bill_id}/items/{item_id} Remove item
```

### Payments
```
POST   /api/billing/payments/record           Record payment
GET    /api/billing/payments/{bill_id}        List bill payments
```

### Reports
```
GET    /api/billing/reports/vendor-payment    Vendor payment summary
GET    /api/billing/reports/project-cost      Project cost breakdown
GET    /api/billing/reports/outstanding       Outstanding bills report
GET    /api/billing/reports/payment-analysis  Payment pattern analysis
```

### Pages
```
GET    /app/billing/dashboard                 Main billing dashboard
GET    /app/billing/bill?id={id}             Bill detail page
GET    /app/billing/payment-record?id={id}   Payment recording form
GET    /app/billing/reports                   Reports dashboard
```

## Key Features

### Automatic Number Generation
Bills and payments get auto-generated numbers with year prefix:
- Bills: `BILL-2025-0001`, `BILL-2025-0002`, etc.
- Payments: `PAY-2025-0001`, `PAY-2025-0002`, etc.

### Payment Status Tracking
Bills automatically update their status based on payments:
- **PENDING**: No payments received
- **PARTIAL**: Partial payment received
- **PAID**: Fully paid
- **OVERDUE**: Past due date with outstanding balance
- **CANCELLED**: Bill cancelled

### GST Calculations
Line-level and bill-level GST calculations:
```
Line Total = Quantity × Unit Price
GST Amount = Line Total × (GST% / 100)
Line Total with GST = Line Total + GST Amount
Bill Total = Sum of all line totals with GST
```

### Financial Analysis
Outstanding balance automatically calculated:
```
Outstanding = Bill Total - Total Paid
```

## Response Format

All API responses follow this format:

### Success Response
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {...}  // Optional, endpoint-specific data
}
```

### Error Response
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Report Queries

### Vendor Payment Report
Filters:
- `vendor_id` (optional)
- `start_date` (optional, YYYY-MM-DD format)
- `end_date` (optional, YYYY-MM-DD format)

Returns: Total bills, amounts, payment status distribution

### Project Cost Report
Parameters:
- `project_id` (required)

Returns: Cost by bill type, payment status, average bill amount

### Outstanding Bills Report
Parameters:
- `project_id` (optional)

Returns: Overdue bills with days aging, upcoming bills due soon

### Payment Analysis Report
Filters:
- `vendor_id` (optional)
- `start_date` (optional)
- `end_date` (optional)

Returns: Payment method breakdown, reconciliation status

## Common Tasks

### Create a Bill with Items

1. Create bill:
```bash
curl -X POST http://localhost:8000/api/billing/bills/create \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_id": 1,
    "project_id": 1,
    "bill_date": "2025-02-17",
    "due_date": "2025-03-17"
  }'
```

2. Add items:
```bash
curl -X POST http://localhost:8000/api/billing/bills/{bill_id}/add-item \
  -H "Content-Type: application/json" \
  -d '{
    "material_id": 1,
    "quantity": 100,
    "unit": "kg",
    "unit_price": 500,
    "gst_percentage": 18
  }'
```

### Record Payment

```bash
curl -X POST http://localhost:8000/api/billing/payments/record \
  -H "Content-Type: application/json" \
  -d '{
    "bill_id": 1,
    "vendor_id": 1,
    "project_id": 1,
    "amount_paid": 25000,
    "payment_date": "2025-02-18",
    "payment_method": "NEFT",
    "bank_name": "HDFC Bank"
  }'
```

### Generate Reports

```bash
# Vendor payment summary
curl 'http://localhost:8000/api/billing/reports/vendor-payment?vendor_id=1'

# Project cost breakdown
curl 'http://localhost:8000/api/billing/reports/project-cost?project_id=1'

# Outstanding bills
curl 'http://localhost:8000/api/billing/reports/outstanding?project_id=1'
```

## Troubleshooting

### Routes Not Found (404)
1. Check if routes are registered in main.py
2. Verify route decorators match API paths
3. Check import statements for typos

### Migration Error
1. Ensure alembic.ini is in project root
2. Check database connection settings
3. Verify no duplicate migration versions exist

### API Response Errors
1. Ensure bill_id/vendor_id/project_id are valid
2. Check authentication token (if required)
3. Verify request JSON format matches schema

### Frontend Not Loading
1. Check if JavaScript console shows errors
2. Verify template files exist in correct folder
3. Check CSS variable names in ux.css and ui_v2.css

## Performance Tips

1. **Pagination**: Use `skip` and `limit` parameters for large bill lists
2. **Filtering**: Apply vendor_id or project_id filters to reduce query scope
3. **Batch Operations**: Add multiple items before calculating totals
4. **Report Caching**: Cache report results if running frequently

## Security Reminders

1. Only superadmin/admin users can create/modify bills and payments
2. All financial amounts use Decimal(12,2) for precision
3. Dates are validated before storage
4. Payment methods have conditional field validation

## Next Phase Features

- [ ] PDF invoice generation
- [ ] Email notifications for overdue bills
- [ ] Bulk bill import from CSV
- [ ] Bill templates and presets
- [ ] Payment plan scheduling
- [ ] Vendor portal access
- [ ] Advanced analytics dashboard
- [ ] Bank reconciliation tools
