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
TASK_WEBHOOK_URL = "https://discord.com/api/webhooks/1434581338786234388/YLq7OJfqS0_UBqTvY_bGbXdUKZgKXgbK3Mc9neAVTwBUfZZBgL4Eno6G5kUJRF87X7zm"
CAKE_CHECK_WEBHOOK_URL = "https://discord.com/api/webhooks/1429805698413232238/GAygBOBeaQQfL_G9m4_KA-UZVJ3d62WFPTDpJaX-8PwxRe3shjrnwmCXRggKRkqUEz1S"



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
class RevenueInput(BaseModel):
    store_id: str
    username: str
    date: date
    cash_revenue: float
    transfer_revenue: float
    grab_revenue: float
    shopee_revenue: float

class RevenueUpdateRequest(BaseModel):
    store_id: str
    date: date
    revenue_type: str  # 'cash_revenue', 'transfer_revenue', 'grab_revenue', 'shopee_revenue'
    new_amount: float

class StoreInventoryInput(BaseModel):
    store_id: str
    username: str
    date: date
    inventory: Dict[str, float]
    input_user: str

class StoreInventoryAdjustment(BaseModel):
    store_id: str
    username: str
    date: date
    input_user: str
    adjustments: List[Dict[str, Any]]  # [{"product": "...", "qty": ...}]

class StoreOrderInput(BaseModel):
    store_id: str
    username: str
    date: date
    order_items: List[Dict[str, Any]]

class SalesDataInput(BaseModel):
    store_id: str
    date: date
    employee: str
    items: List[Dict[str, Any]]  # [{"category": "...", "product_name": "...", "quantity": ...}]

class CakeCheckInput(BaseModel):
    store_id: str
    date: date
    user: str
    base_l_yesterday: int
    base_s_yesterday: int
    base_l_today: int
    base_s_today: int
    base_l_out: int
    base_s_out: int
    base_l_discard: int
    base_s_discard: int
    base_l_machine: int
    base_s_machine: int

class TaskReportInput(BaseModel):
    store_id: str
    session: str  # 'morning' or 'afternoon'
    person: str
    tasks: List[Dict[str, Any]]  # [{"task": "...", "completed": true/false}]

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
# endpoint mới /api/login-owner
# -----------------------------------------------------   
# Thêm đoạn code này vào file backend (main.py), sau endpoint /api/login-store

@app.post("/api/login-owner", response_model=SimpleLoginResponse)
async def login_owner(request: SimpleLoginRequest):
    """
    Login riêng cho App Owner - Chỉ owner/admin mới truy cập được
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
        
        # ✅ Kiểm tra quyền: Phải có app_owner HOẶC là admin
        if "app_owner" not in app_access and user_data.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản này không có quyền truy cập App Owner"
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
    
# -----------------------------------------------------
# STORE REVENUE ENDPOINTS
# -----------------------------------------------------
@app.post("/api/store/revenue")
async def save_store_revenue(
    data: RevenueInput,
    username: str = Depends(verify_credentials)
):
    """Lưu doanh thu cho quán"""
    try:
        total_revenue = (
            data.cash_revenue + 
            data.transfer_revenue + 
            data.grab_revenue + 
            data.shopee_revenue
        )
        
        record = {
            "store_id": data.store_id,
            "username": data.username,
            "date": str(data.date),
            "cash_revenue": data.cash_revenue,
            "transfer_revenue": data.transfer_revenue,
            "grab_revenue": data.grab_revenue,
            "shopee_revenue": data.shopee_revenue,
            "total_revenue": total_revenue,
            "created_at": datetime.now().isoformat()
        }
        
        response = supabase.table("sale_quan").insert([record]).execute()
        
        return {"success": True, "message": "Đã lưu doanh thu thành công", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/store/revenue/update")
async def update_store_revenue(
    data: RevenueUpdateRequest,
    username: str = Depends(verify_credentials)
):
    """Cập nhật doanh thu cho quán"""
    try:
        # Tìm bản ghi cần cập nhật
        response = supabase.table("sale_quan")\
            .select("*")\
            .eq("store_id", data.store_id)\
            .eq("date", str(data.date))\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu doanh thu")
        
        record = response.data[0]
        old_amount = record.get(data.revenue_type, 0)
        
        # Tính lại tổng
        old_total = record.get("total_revenue", 0)
        new_total = old_total - old_amount + data.new_amount
        
        # Cập nhật
        update_data = {
            data.revenue_type: data.new_amount,
            "total_revenue": new_total
        }
        
        supabase.table("sale_quan")\
            .update(update_data)\
            .eq("id", record["id"])\
            .execute()
        
        return {
            "success": True,
            "message": "Cập nhật thành công",
            "old_amount": old_amount,
            "new_amount": data.new_amount
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# STORE INVENTORY ENDPOINTS
# -----------------------------------------------------
@app.post("/api/store/inventory")
async def save_store_inventory(
    data: StoreInventoryInput,
    username: str = Depends(verify_credentials)
):
    """Lưu kiểm hàng tồn kho quán"""
    try:
        record = {
            "store_id": data.store_id,
            "username": data.username,
            "date": str(data.date),
            "inventory": data.inventory,
            "input_user": data.input_user,
            "created_at": datetime.now().isoformat()
        }
        
        response = supabase.table("ton_quan").insert([record]).execute()
        
        return {"success": True, "message": "Đã lưu tồn kho", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/store/inventory/adjust")
async def adjust_store_inventory(
    data: StoreInventoryAdjustment,
    username: str = Depends(verify_credentials)
):
    """Điều chỉnh tồn kho quán"""
    try:
        # Lấy inventory mới nhất
        response = supabase.table("ton_quan")\
            .select("inventory")\
            .eq("store_id", data.store_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        inventory = response.data[0]["inventory"] if response.data else {}
        
        # Áp dụng điều chỉnh
        for adj in data.adjustments:
            inventory[adj["product"]] = adj["qty"]
        
        # Lưu bản ghi mới
        new_record = {
            "store_id": data.store_id,
            "date": str(data.date),
            "username": data.username,
            "input_user": data.input_user,
            "inventory": inventory,
            "created_at": datetime.now().isoformat()
        }
        
        supabase.table("ton_quan").insert([new_record]).execute()
        
        return {"success": True, "message": "Đã lưu điều chỉnh", "inventory": inventory}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/store/inventory/latest/{store_id}")
async def get_latest_inventory(
    store_id: str,
    username: str = Depends(verify_credentials)
):
    """Lấy tồn kho mới nhất của quán"""
    try:
        response = supabase.table("ton_quan")\
            .select("*")\
            .eq("store_id", store_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        return {"success": True, "data": response.data[0] if response.data else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# STORE ORDER ENDPOINTS
# -----------------------------------------------------
@app.post("/api/store/order")
async def create_store_order(
    data: StoreOrderInput,
    username: str = Depends(verify_credentials)
):
    """Tạo đơn đặt hàng từ quán"""
    try:
        record = {
            "store_id": data.store_id,
            "username": data.username,
            "date": str(data.date),
            "order_items": data.order_items,
            "created_at": datetime.now().isoformat()
        }
        
        response = supabase.table("order_quan").insert([record]).execute()
        
        # Gửi Telegram
        await send_order_telegram(data.store_id, data.username, data.order_items)
        
        return {"success": True, "message": "Đã lưu và gửi đơn hàng"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def send_order_telegram(store_id: str, username: str, order_items: List[Dict]):
    """Gửi thông báo đơn hàng qua Telegram"""
    bot_token = '8036982528:AAEymf0l1HH47SB10gcd7QwxyugpBLxrvas'
    chat_id = '-4776196182'
    
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y %H:%M")
    
    items_list = "\n".join([
        f"{item['item'].ljust(20)} - {item['order_quantity']}"
        for item in order_items
    ])
    
    message = f"""🛒 *ĐƠN ĐẶT HÀNG MỚI*

🏪 *Quán:* {store_id}
👤 *Người đặt:* {username}
📅 *Thời gian:* {date_str}

📦 *Danh sách hàng đặt:*
```
{items_list}
```

_Hệ thống quản lý Pizza_"""
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            })
        except Exception as e:
            print(f"Telegram error: {e}")

# -----------------------------------------------------
# SALES DATA ENDPOINTS
# -----------------------------------------------------
@app.post("/api/store/sales")
async def save_sales_data(
    data: SalesDataInput,
    username: str = Depends(verify_credentials)
):
    """Lưu dữ liệu bán hàng"""
    try:
        records = []
        for item in data.items:
            records.append({
                "date": str(data.date),
                "store": data.store_id,
                "employee": data.employee,
                "category": item["category"],
                "product_name": item["product_name"],
                "quantity": item["quantity"],
                "created_at": datetime.now().isoformat()
            })
        
        response = supabase.table("pizza_sales").insert(records).execute()
        
        return {"success": True, "message": "Đã lưu dữ liệu bán hàng"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# CAKE CHECK ENDPOINTS
# -----------------------------------------------------
@app.get("/api/store/cake/base-data/{store_id}")
async def get_cake_base_data(
    store_id: str,
    username: str = Depends(verify_credentials)
):
    """Lấy dữ liệu đế bánh cho check bánh"""
    try:
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # Lấy tồn hôm qua
        yesterday_inv = supabase.table("ton_quan")\
            .select("inventory")\
            .eq("store_id", store_id)\
            .eq("date", str(yesterday))\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        # Lấy tồn hôm nay
        today_inv = supabase.table("ton_quan")\
            .select("inventory")\
            .eq("store_id", store_id)\
            .eq("date", str(today))\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        # Lấy exports hôm nay
        exports_l = supabase.table("exports")\
            .select("quantity")\
            .eq("store", store_id)\
            .eq("date", str(today))\
            .eq("item", "Đế L")\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        exports_s = supabase.table("exports")\
            .select("quantity")\
            .eq("store", store_id)\
            .eq("date", str(today))\
            .eq("item", "Đế S")\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        yesterday_data = yesterday_inv.data[0]["inventory"] if yesterday_inv.data else {}
        today_data = today_inv.data[0]["inventory"] if today_inv.data else {}
        
        return {
            "success": True,
            "data": {
                "base_l_yesterday": yesterday_data.get("Đế L", 0),
                "base_s_yesterday": yesterday_data.get("Đế S", 0),
                "base_l_today": today_data.get("Đế L", 0),
                "base_s_today": today_data.get("Đế S", 0),
                "base_l_out": abs(exports_l.data[0]["quantity"]) if exports_l.data else 0,
                "base_s_out": abs(exports_s.data[0]["quantity"]) if exports_s.data else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from datetime import timedelta

@app.post("/api/store/cake/check")
async def check_cake_result(
    data: CakeCheckInput,
    username: str = Depends(verify_credentials)
):
    """Kiểm tra kết quả bánh và gửi Discord"""
    try:
        # Tính toán
        l_actual = data.base_l_yesterday - data.base_l_today + data.base_l_out - data.base_l_discard
        s_actual = data.base_s_yesterday - data.base_s_today + data.base_s_out - data.base_s_discard
        l_diff = l_actual - data.base_l_machine
        s_diff = s_actual - data.base_s_machine
        
        # Gửi Discord
        color = 3066993 if (l_diff == 0 and s_diff == 0) else (15158332 if (l_diff > 0 or s_diff > 0) else 3447003)
        
        def format_result(actual, machine, diff):
            if diff == 0:
                return f"Thực tế: **{actual}** | Máy: **{machine}** → ✅ **Đủ**"
            elif diff > 0:
                return f"Thực tế: **{actual}** | Máy: **{machine}** → ⚠️ **Thiếu {diff}**"
            else:
                return f"Thực tế: **{actual}** | Máy: **{machine}** → ✅ **Dư {-diff}**"
        
        embed = {
            "title": "🧁 Kết Quả Kiểm Tra Bánh",
            "color": color,
            "fields": [
                {"name": "📅 Ngày", "value": str(data.date), "inline": True},
                {"name": "🏪 Quán", "value": data.store_id, "inline": True},
                {"name": "👤 Người kiểm", "value": data.user, "inline": True},
                {"name": "\u200B", "value": "\u200B"},
                {"name": "📊 Số liệu hôm qua", "value": f"Đế L: {data.base_l_yesterday} | Đế S: {data.base_s_yesterday}"},
                {"name": "📊 Số liệu hôm nay", "value": f"Đế L: {data.base_l_today} | Đế S: {data.base_s_today}"},
                {"name": "📦 Mang ra", "value": f"Đế L: {data.base_l_out} | Đế S: {data.base_s_out}"},
                {"name": "🗑️ Bỏ đi", "value": f"Đế L: {data.base_l_discard} | Đế S: {data.base_s_discard}"},
                {"name": "🤖 Máy bán", "value": f"Đế L: {data.base_l_machine} | Đế S: {data.base_s_machine}"},
                {"name": "\u200B", "value": "\u200B"},
                {"name": "🔍 Kết quả Đế L", "value": format_result(l_actual, data.base_l_machine, l_diff)},
                {"name": "🔍 Kết quả Đế S", "value": format_result(s_actual, data.base_s_machine, s_diff)}
            ],
            "timestamp": datetime.now().isoformat(),
            "footer": {"text": "Hệ thống quản lý bánh"}
        }
        
        async with httpx.AsyncClient() as client:
            await client.post(CAKE_CHECK_WEBHOOK_URL, json={"embeds": [embed]})
        
        return {
            "success": True,
            "message": "Đã gửi kết quả",
            "result": {
                "l_actual": l_actual,
                "s_actual": s_actual,
                "l_diff": l_diff,
                "s_diff": s_diff
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# TASK REMINDER ENDPOINTS
# -----------------------------------------------------
@app.post("/api/store/tasks/report")
async def send_task_report(
    data: TaskReportInput,
    username: str = Depends(verify_credentials)
):
    """Gửi báo cáo công việc lên Discord"""
    try:
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%d/%m/%Y")
        
        session_name = "☀️ CA SÁNG (14:00)" if data.session == "morning" else "🌤️ CA CHIỀU (17:00)"
        
        message = f"**📋 BÁO CÁO {session_name.upper()} - {data.store_id}**\n"
        message += f"**📅 {date_str} {time_str}**\n\n"
        message += f"**{session_name}** - Người làm: {data.person}\n"
        
        for task in data.tasks:
            status = "✅" if task["completed"] else "❌"
            message += f"{status} {task['task']}\n"
        
        async with httpx.AsyncClient() as client:
            await client.post(TASK_WEBHOOK_URL, json={"content": message})
        
        return {"success": True, "message": "Đã gửi báo cáo"}
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
