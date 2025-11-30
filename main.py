"""
Pizza Time Owner - Backend API
FastAPI + Supabase Backend for Pizza Management System
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
import secrets
from supabase import create_client, Client
import os
import hashlib

# =====================================================
# CONFIGURATION
# =====================================================
SUPABASE_URL = "https://tyuufjwutazjfuiawiul.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR5dXVmand1dGF6amZ1aWF3aXVsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA1MDk4OTIsImV4cCI6MjA3NjA4NTg5Mn0.8WEsb2tBD6akNA9h9tR9zIAqjkZz0xZYVNbYCx2dEbc"

# Valid users with hashed passwords
VALID_USERS = {
    'Bo@Phuc': hashlib.sha256('Nhim=Khanh'.encode()).hexdigest(),
    'Nhim@Khanh': hashlib.sha256('Bo=Phuc'.encode()).hexdigest()
}

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================
# FASTAPI APP SETUP
# =====================================================
app = FastAPI(
    title="Pizza Time Owner API",
    description="Backend API for Pizza Time Management System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic Auth
security = HTTPBasic()

# =====================================================
# MODELS
# =====================================================
class LoginRequest(BaseModel):
    username: str
    password: str

class SalesQuery(BaseModel):
    start_date: date
    end_date: date
    stores: Optional[List[str]] = None

class QuantityQuery(BaseModel):
    start_date: date
    end_date: date
    store: Optional[str] = None

class ExportQuery(BaseModel):
    start_date: date
    end_date: date
    stores: Optional[List[str]] = None

class SalesResponse(BaseModel):
    cash: float
    transfer: float
    grab: float
    shopee: float
    total: float
    data: List[dict]

class QuantityResponse(BaseModel):
    total_quantity: int
    total_orders: int
    total_categories: int
    total_products: int
    data: List[dict]

class ExportResponse(BaseModel):
    total_quantity: float
    total_orders: int
    total_stores: int
    total_products: int
    data: List[dict]

# =====================================================
# AUTHENTICATION
# =====================================================
def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify user credentials"""
    username = credentials.username
    password = credentials.password
    
    # Hash the password to compare
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if username not in VALID_USERS or VALID_USERS[username] != password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return username

# =====================================================
# UTILITY FUNCTIONS
# =====================================================
def get_number_field(item: dict, candidates: List[str]) -> float:
    """Extract numeric field from item"""
    for name in candidates:
        if name in item and item[name] is not None:
            try:
                return float(item[name])
            except (ValueError, TypeError):
                continue
    return 0.0

def parse_store_filter(stores: Optional[List[str]]) -> Optional[str]:
    """Parse store filter for Supabase query"""
    if not stores or "all" in stores:
        return None
    
    # Create OR filter for multiple stores
    or_parts = [f"store_id.eq.{store}" for store in stores]
    return f"or=({','.join(or_parts)})"

# =====================================================
# API ENDPOINTS
# =====================================================

@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "message": "Pizza Time Owner API",
        "version": "1.0.0",
        "status": "online"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# -----------------------------------------------------
# LOGIN ENDPOINT
# -----------------------------------------------------
@app.post("/api/login")
async def login(request: LoginRequest):
    """Login endpoint for frontend authentication"""
    username = request.username
    password_hash = hashlib.sha256(request.password.encode()).hexdigest()
    
    if username in VALID_USERS and VALID_USERS[username] == password_hash:
        return {"success": True, "message": "Đăng nhập thành công"}
    else:
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")

# -----------------------------------------------------
# SALES ENDPOINTS
# -----------------------------------------------------
@app.post("/api/sales", response_model=SalesResponse)
def get_sales(
    query: SalesQuery,
    username: str = Depends(verify_credentials)
):
    """
    Get sales data with filters
    """
    try:
        # Build query
        q = supabase.table("sale_quan").select("*")
        q = q.gte("date", str(query.start_date))
        q = q.lte("date", str(query.end_date))
        
        # Apply store filter
        if query.stores and "all" not in query.stores:
            # Filter by specific stores
            q = q.in_("store_id", query.stores)
        
        # Execute query
        response = q.execute()
        data = response.data
        
        if not data:
            return SalesResponse(
                cash=0, transfer=0, grab=0, shopee=0, total=0, data=[]
            )
        
        # Calculate totals
        totals = {
            "cash": 0.0,
            "transfer": 0.0,
            "grab": 0.0,
            "shopee": 0.0,
            "total": 0.0
        }
        
        for item in data:
            totals["cash"] += get_number_field(item, ["cash_revenue", "cash", "cash_amount"])
            totals["transfer"] += get_number_field(item, ["transfer_revenue", "momo", "transfer"])
            totals["grab"] += get_number_field(item, ["grab_revenue", "grab"])
            totals["shopee"] += get_number_field(item, ["shopee_revenue", "shopee"])
            totals["total"] += get_number_field(item, ["total_revenue", "total", "total_amount"])
        
        return SalesResponse(**totals, data=data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sales/stores")
def get_stores(username: str = Depends(verify_credentials)):
    """Get list of available stores"""
    try:
        response = supabase.table("sale_quan").select("store_id, username").execute()
        
        # Remove duplicates
        stores = {}
        for item in response.data:
            store_id = item.get("store_id")
            if store_id and store_id not in stores:
                stores[store_id] = item
        
        return {"stores": list(stores.values())}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# QUANTITY ENDPOINTS
# -----------------------------------------------------
@app.post("/api/quantity", response_model=QuantityResponse)
def get_quantity(
    query: QuantityQuery,
    username: str = Depends(verify_credentials)
):
    """
    Get quantity data with filters
    """
    try:
        # Build query
        q = supabase.table("pizza_sales").select("*")
        q = q.gte("date", str(query.start_date))
        q = q.lte("date", str(query.end_date))
        
        # Apply store filter
        if query.store:
            q = q.eq("store", query.store)
        
        # Execute query
        response = q.execute()
        data = response.data
        
        if not data:
            return QuantityResponse(
                total_quantity=0,
                total_orders=0,
                total_categories=0,
                total_products=0,
                data=[]
            )
        
        # Calculate totals
        total_quantity = sum(int(item.get("quantity", 0)) for item in data)
        total_orders = len(data)
        categories = set(item.get("category", "Khác") for item in data)
        products = set(item.get("product_name") or item.get("product", "Unknown") for item in data)
        
        return QuantityResponse(
            total_quantity=total_quantity,
            total_orders=total_orders,
            total_categories=len(categories),
            total_products=len(products),
            data=data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# EXPORT ENDPOINTS
# -----------------------------------------------------
@app.post("/api/exports", response_model=ExportResponse)
def get_exports(
    query: ExportQuery,
    username: str = Depends(verify_credentials)
):
    """
    Get export data with filters
    """
    try:
        # Build query
        q = supabase.table("exports").select("*")
        q = q.gte("date", str(query.start_date))
        q = q.lte("date", str(query.end_date))
        q = q.order("created_at", desc=True)
        
        # Apply store filter
        if query.stores and "all" not in query.stores:
            q = q.in_("store", query.stores)
        
        # Execute query
        response = q.execute()
        raw_data = response.data
        
        if not raw_data:
            return ExportResponse(
                total_quantity=0,
                total_orders=0,
                total_stores=0,
                total_products=0,
                data=[]
            )
        
        # Group by date + store + item, keep only latest
        grouped = {}
        for item in raw_data:
            key = f"{item['date']}|{item['store']}|{item['item']}"
            if key not in grouped or item['created_at'] > grouped[key]['created_at']:
                grouped[key] = item
        
        data = list(grouped.values())
        
        # Calculate totals
        total_quantity = sum(abs(float(item.get("quantity", 0))) for item in data)
        total_orders = len(data)
        stores = set(item.get("store") for item in data)
        products = set(item.get("item") for item in data)
        
        return ExportResponse(
            total_quantity=total_quantity,
            total_orders=total_orders,
            total_stores=len(stores),
            total_products=len(products),
            data=data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# RUN SERVER
# =====================================================
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
