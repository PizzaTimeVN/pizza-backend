"""
Pizza Time Owner - Backend API (Secure Version)
FastAPI + Supabase Backend with Discord Integration
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
import secrets
from supabase import create_client, Client
import httpx
import os

# =====================================================
# CONFIGURATION
# =====================================================
SUPABASE_URL = "https://tyuufjwutazjfuiawiul.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR5dXVmand1dGF6amZ1aWF3aXVsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA1MDk4OTIsImV4cCI6MjA3NjA4NTg5Mn0.8WEsb2tBD6akNA9h9tR9zIAqjkZz0xZYVNbYCx2dEbc"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1444701214490230895/KE3HDU0Fo8fsEt5yKrMyk83Gy3AIEqfDeOX98k-CWhhhh6awuQY2dAh7WUWn4MDopulc"



# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================
# FASTAPI APP SETUP
# =====================================================
app = FastAPI(
    title="Pizza Time Owner API",
    description="Backend API for Pizza Time Management System",
    version="2.0.0"
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
    date: date

class LoginResponse(BaseModel):
    success: bool
    username: str
    date: str

class InventoryItem(BaseModel):
    item: str
    quantity: float

class RawMaterialInput(BaseModel):
    date: date
    user_name: str
    items: List[InventoryItem]

class ProductionInput(BaseModel):
    date: date
    user_name: str
    items: List[InventoryItem]

class ExportInput(BaseModel):
    date: date
    user_name: str
    store: str
    items: List[InventoryItem]

class InventoryUpdate(BaseModel):
    item: str
    quantity: float

class OrderItem(BaseModel):
    name: str
    currentStock: float
    orderQty: int

class DiscordOrderRequest(BaseModel):
    user_name: str
    orders: List[OrderItem]

class SimpleLoginRequest(BaseModel):
    username: str
    password: str

class SimpleLoginResponse(BaseModel):
    success: bool
    username: str

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
async def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify user credentials from Supabase"""
    username = credentials.username
    password = credentials.password
    
    try:
        response = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        return username
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
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

# =====================================================
# API ENDPOINTS
# =====================================================

@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "message": "Pizza Time Owner API",
        "version": "2.0.0",
        "status": "online"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# -----------------------------------------------------
# AUTHENTICATION ENDPOINTS
# -----------------------------------------------------
@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login endpoint for App Xưởng (requires date field)
    """
    try:
        response = supabase.table("users").select("*").eq("username", request.username).eq("password", request.password).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        user_data = response.data[0]
        app_access = user_data.get("app_access", [])
        
        # Kiểm tra quyền app_xuong
        if "app_xuong" not in app_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản này không có quyền truy cập app xưởng"
            )
        
        return LoginResponse(
            success=True,
            username=request.username,
            date=str(request.date)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SimpleLoginRequest(BaseModel):
    username: str
    password: str

class SimpleLoginResponse(BaseModel):
    success: bool
    username: str
    user: dict

class LoginWithStoreRequest(BaseModel):
    username: str
    password: str
    store_id: str

class LoginWithStoreResponse(BaseModel):
    success: bool
    username: str
    user: dict
    store_id: str
# -----------------------------------------------------
# endpoint mới /api/login
# ----------------------------------------------------- 

@app.post("/api/login", response_model=SimpleLoginResponse)
async def simple_login(request: SimpleLoginRequest):
    """
    Login cho App Xưởng & App Owner (không cần chọn quán)
    """
    try:
        # Query từ Supabase users table
        response = supabase.table("users").select("*").eq("username", request.username).eq("password", request.password).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tên đăng nhập hoặc mật khẩu không đúng"
            )
        
        user_data = response.data[0]
        app_access = user_data.get("app_access", [])
        
        # Kiểm tra quyền app_xuong hoặc app_owner
        if "app_xuong" not in app_access and "app_owner" not in app_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản này không có quyền truy cập ứng dụng này"
            )
        
        return SimpleLoginResponse(
            success=True,
            username=user_data["username"],
            user={
                "display_name": user_data["display_name"],
                "role": user_data["role"],
                "app_access": user_data["app_access"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

# -----------------------------------------------------
# endpoint mới /api/login-store
# -----------------------------------------------------   
@app.post("/api/login-store", response_model=LoginWithStoreResponse)
async def login_with_store(request: LoginWithStoreRequest):
    """
    Login cho App Quán - Nhân viên chọn quán để đăng nhập
    """
    try:
        response = supabase.table("users").select("*").eq("username", request.username).eq("password", request.password).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tên đăng nhập hoặc mật khẩu không đúng"
            )
        
        user_data = response.data[0]
        app_access = user_data.get("app_access", [])
        
        # Kiểm tra quyền app_quan
        if "app_quan" not in app_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản này không có quyền truy cập ứng dụng quán"
            )
        
        return LoginWithStoreResponse(
            success=True,
            username=user_data["username"],
            user={
                "display_name": user_data["display_name"],
                "role": user_data["role"],
                "app_access": user_data["app_access"]
            },
            store_id=request.store_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

# -----------------------------------------------------
# INVENTORY ENDPOINTS
# -----------------------------------------------------
@app.get("/api/inventory")
def get_inventory(username: str = Depends(verify_credentials)):
    """
    Get all inventory items
    """
    try:
        response = supabase.table("inventory").select("*").execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inventory/update")
def update_inventory_item(
    update: InventoryUpdate,
    username: str = Depends(verify_credentials)
):
    """
    Update inventory item quantity
    """
    try:
        response = supabase.table("inventory").upsert(
            {"item": update.item, "quantity": update.quantity},
            on_conflict="item"
        ).execute()
        
        return {"success": True, "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# RAW MATERIALS ENDPOINTS
# -----------------------------------------------------
@app.post("/api/raw-materials")
def add_raw_materials(
    input_data: RawMaterialInput,
    username: str = Depends(verify_credentials)
):
    """
    Add raw materials input
    """
    try:
        # Insert raw materials records
        records = []
        for item in input_data.items:
            records.append({
                "date": str(input_data.date),
                "user_name": input_data.user_name,
                "item": item.item,
                "quantity": item.quantity
            })
        
        if records:
            supabase.table("raw_materials_input").insert(records).execute()
        
        # Update inventory
        for item in input_data.items:
            # Get current quantity
            inv_response = supabase.table("inventory").select("quantity").eq("item", item.item).execute()
            current_qty = inv_response.data[0]["quantity"] if inv_response.data else 0
            new_qty = current_qty + item.quantity
            
            # Update inventory
            supabase.table("inventory").upsert(
                {"item": item.item, "quantity": new_qty},
                on_conflict="item"
            ).execute()
        
        return {"success": True, "message": "Raw materials added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# PRODUCTION ENDPOINTS
# -----------------------------------------------------
@app.post("/api/production")
def add_production(
    input_data: ProductionInput,
    username: str = Depends(verify_credentials)
):
    """
    Add production records
    """
    try:
        # Insert production records
        records = []
        for item in input_data.items:
            records.append({
                "date": str(input_data.date),
                "user_name": input_data.user_name,
                "item": item.item,
                "quantity": item.quantity
            })
        
        if records:
            supabase.table("production").insert(records).execute()
        
        # Update inventory
        for item in input_data.items:
            inv_response = supabase.table("inventory").select("quantity").eq("item", item.item).execute()
            current_qty = inv_response.data[0]["quantity"] if inv_response.data else 0
            new_qty = current_qty + item.quantity
            
            supabase.table("inventory").upsert(
                {"item": item.item, "quantity": new_qty},
                on_conflict="item"
            ).execute()
        
        return {"success": True, "message": "Production added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# EXPORT ENDPOINTS
# -----------------------------------------------------
@app.post("/api/exports/create")
def create_export(
    input_data: ExportInput,
    username: str = Depends(verify_credentials)
):
    """
    Create export records
    """
    try:
        # Insert export records
        records = []
        for item in input_data.items:
            records.append({
                "date": str(input_data.date),
                "user_name": input_data.user_name,
                "store": input_data.store,
                "item": item.item,
                "quantity": -abs(item.quantity)  # Negative for export
            })
        
        if records:
            supabase.table("exports").insert(records).execute()
        
        # Update inventory (subtract quantities)
        for item in input_data.items:
            inv_response = supabase.table("inventory").select("quantity").eq("item", item.item).execute()
            current_qty = inv_response.data[0]["quantity"] if inv_response.data else 0
            new_qty = current_qty - abs(item.quantity)
            
            supabase.table("inventory").upsert(
                {"item": item.item, "quantity": new_qty},
                on_conflict="item"
            ).execute()
        
        return {"success": True, "message": "Export created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/exports/history")
def get_export_history(username: str = Depends(verify_credentials)):
    """
    Get latest export history
    """
    try:
        # Get latest date
        latest_response = supabase.table("exports").select("date").order("date", desc=True).limit(1).execute()
        
        if not latest_response.data:
            return {"success": True, "data": [], "date": None}
        
        latest_date = latest_response.data[0]["date"]
        
        # Get all exports for that date
        exports_response = supabase.table("exports").select("*").eq("date", latest_date).order("created_at", desc=True).execute()
        
        return {
            "success": True,
            "data": exports_response.data,
            "date": latest_date
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# DISCORD INTEGRATION
# -----------------------------------------------------
@app.post("/api/discord/send-order")
async def send_order_to_discord(
    request: DiscordOrderRequest,
    username: str = Depends(verify_credentials)
):
    """
    Send order to Discord webhook
    """
    try:
        # Create order message
        now = datetime.now()
        date_str = now.strftime("%d/%m/%Y")
        time_str = now.strftime("%H:%M:%S")
        
        message = f"🍕 **ĐƠN ĐẶT HÀNG - PIZZA TIME**\n\n"
        message += f"📅 **Ngày:** {date_str} - {time_str}\n"
        message += f"👤 **Người đặt:** {request.user_name}\n"
        message += f"📦 **Số mặt hàng:** {len(request.orders)}\n\n"
        message += f"**CHI TIẾT ĐƠN HÀNG:**\n"
        message += f"{'=' * 50}\n"
        
        for idx, order in enumerate(request.orders, 1):
            message += f"{idx}. **{order.name}**\n"
            message += f"   └ Tồn kho hiện tại: {order.currentStock}\n"
            message += f"   └ Số lượng đặt: **{order.orderQty}**\n\n"
        
        message += f"{'=' * 50}\n"
        message += f"⚠️ *Vui lòng xác nhận và xử lý đơn hàng này!*"
        
        # Send to Discord
        async with httpx.AsyncClient() as client:
            discord_response = await client.post(
                DISCORD_WEBHOOK_URL,
                json={
                    "content": message,
                    "username": "Pizza Time Bot",
                    "avatar_url": "https://em-content.zobj.net/thumbs/120/apple/354/pizza_1f355.png"
                }
            )
        
        if discord_response.status_code not in [200, 204]:
            raise HTTPException(status_code=500, detail="Failed to send Discord message")
        
        # Save order to database
        order_data = {
            "date": now.strftime("%Y-%m-%d"),
            "time": time_str,
            "user_name": request.user_name,
            "items": [order.dict() for order in request.orders],
            "total_items": len(request.orders)
        }
        
        supabase.table("orders").insert([order_data]).execute()
        
        return {"success": True, "message": "Order sent to Discord successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# STORE INVENTORY ENDPOINTS
# -----------------------------------------------------
@app.get("/api/store-inventory/{store_id}")
def get_store_inventory(
    store_id: str,
    username: str = Depends(verify_credentials)
):
    """
    Get inventory for a specific store
    """
    try:
        response = supabase.table("ton_quan").select("inventory, date, created_at").eq("store_id", store_id).order("created_at", desc=True).limit(1).execute()
        
        if not response.data:
            return {"success": True, "data": None, "message": "No data found"}
        
        return {"success": True, "data": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# SALES ENDPOINTS (From original code)
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
        q = supabase.table("sale_quan").select("*")
        q = q.gte("date", str(query.start_date))
        q = q.lte("date", str(query.end_date))
        
        if query.stores and "all" not in query.stores:
            q = q.in_("store_id", query.stores)
        
        response = q.execute()
        data = response.data
        
        if not data:
            return SalesResponse(
                cash=0, transfer=0, grab=0, shopee=0, total=0, data=[]
            )
        
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
        
        stores = {}
        for item in response.data:
            store_id = item.get("store_id")
            if store_id and store_id not in stores:
                stores[store_id] = item
        
        return {"stores": list(stores.values())}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/quantity", response_model=QuantityResponse)
def get_quantity(
    query: QuantityQuery,
    username: str = Depends(verify_credentials)
):
    """
    Get quantity data with filters
    """
    try:
        q = supabase.table("pizza_sales").select("*")
        q = q.gte("date", str(query.start_date))
        q = q.lte("date", str(query.end_date))
        
        if query.store:
            q = q.eq("store", query.store)
        
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

@app.post("/api/exports", response_model=ExportResponse)
def get_exports(
    query: ExportQuery,
    username: str = Depends(verify_credentials)
):
    """
    Get export data with filters
    """
    try:
        q = supabase.table("exports").select("*")
        q = q.gte("date", str(query.start_date))
        q = q.lte("date", str(query.end_date))
        q = q.order("created_at", desc=True)
        
        if query.stores and "all" not in query.stores:
            q = q.in_("store", query.stores)
        
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
        
        grouped = {}
        for item in raw_data:
            key = f"{item['date']}|{item['store']}|{item['item']}"
            if key not in grouped or item['created_at'] > grouped[key]['created_at']:
                grouped[key] = item
        
        data = list(grouped.values())
        
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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
