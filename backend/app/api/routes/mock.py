import random
from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()

MOCK_ORDERS = [
    {
        "order_id": "ORD-20240315-0012",
        "customer": "张三",
        "product": "MacBook Pro 14寸 M3",
        "quantity": 1,
        "price": 14999.00,
        "status": "已发货",
        "payment": "已支付",
        "shipping": "顺丰快递 SF1234567890",
        "estimated_delivery": "2024-03-18",
        "address": "北京市朝阳区建国路88号",
    },
    {
        "order_id": "ORD-20240316-0034",
        "customer": "李四",
        "product": "AirPods Pro 2",
        "quantity": 2,
        "price": 1899.00,
        "status": "待发货",
        "payment": "已支付",
        "shipping": "待分配",
        "estimated_delivery": "2024-03-20",
        "address": "上海市浦东新区陆家嘴环路1000号",
    },
    {
        "order_id": "ORD-20240317-0056",
        "customer": "王五",
        "product": "iPhone 15 Pro Max 256GB",
        "quantity": 1,
        "price": 9999.00,
        "status": "配送中",
        "payment": "已支付",
        "shipping": "京东物流 JD9876543210",
        "estimated_delivery": "2024-03-17",
        "address": "广州市天河区体育西路191号",
    },
]

MOCK_INVENTORY = [
    {"sku": "MBP-14-M3-512", "product": "MacBook Pro 14寸 M3 512GB", "stock": 45, "warehouse": "华北仓", "status": "充足"},
    {"sku": "APP-PRO-2", "product": "AirPods Pro 2", "stock": 3, "warehouse": "华东仓", "status": "库存紧张"},
    {"sku": "IP15-PM-256", "product": "iPhone 15 Pro Max 256GB", "stock": 0, "warehouse": "华南仓", "status": "缺货"},
    {"sku": "IPD-AIR-M2", "product": "iPad Air M2 256GB", "stock": 120, "warehouse": "华北仓", "status": "充足"},
    {"sku": "AW-U9-45", "product": "Apple Watch Ultra 2 49mm", "stock": 8, "warehouse": "华东仓", "status": "库存紧张"},
]

MOCK_WEATHER = [
    {"city": "北京", "temperature": "22°C", "weather": "晴", "humidity": "35%", "wind": "北风3级", "aqi": 65, "suggestion": "适宜户外活动"},
    {"city": "上海", "temperature": "18°C", "weather": "多云", "humidity": "72%", "wind": "东风2级", "aqi": 48, "suggestion": "适宜出行"},
    {"city": "广州", "temperature": "28°C", "weather": "阵雨", "humidity": "85%", "wind": "南风2级", "aqi": 52, "suggestion": "建议携带雨具"},
    {"city": "深圳", "temperature": "27°C", "weather": "雷阵雨", "humidity": "88%", "wind": "东南风3级", "aqi": 55, "suggestion": "注意防雷避雨"},
    {"city": "成都", "temperature": "20°C", "weather": "阴", "humidity": "68%", "wind": "微风", "aqi": 78, "suggestion": "适合室内活动"},
]


@router.get("/order")
async def mock_order():
    order = random.choice(MOCK_ORDERS)
    return {
        "success": True,
        "data": order,
        "query_time": datetime.now(timezone.utc).isoformat(),
        "note": "模拟数据，仅供功能演示",
    }


@router.get("/inventory")
async def mock_inventory():
    return {
        "success": True,
        "data": MOCK_INVENTORY,
        "total_products": len(MOCK_INVENTORY),
        "out_of_stock": sum(1 for item in MOCK_INVENTORY if item["stock"] == 0),
        "query_time": datetime.now(timezone.utc).isoformat(),
        "note": "模拟数据，仅供功能演示",
    }


@router.get("/weather")
async def mock_weather():
    return {
        "success": True,
        "data": MOCK_WEATHER,
        "query_time": datetime.now(timezone.utc).isoformat(),
        "note": "模拟数据，仅供功能演示",
    }
