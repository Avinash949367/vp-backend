from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models import PackingItem, Trip, User
from auth import get_current_user
from database import get_database
from bson import ObjectId

router = APIRouter()

@router.post("/{trip_id}", response_model=PackingItem)
async def create_packing_item(trip_id: str, item: PackingItem, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=400, detail="Invalid trip ID")
    
    trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip_obj = Trip(**trip)
    
    # Check if user has access to this trip
    if trip_obj.owner_id != current_user.id and current_user.id not in trip_obj.collaborators:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Add packing item to trip
    item_dict = item.dict()
    item_dict["_id"] = ObjectId()
    
    await db.trips.update_one(
        {"_id": ObjectId(trip_id)},
        {"$push": {"packing_items": item_dict}}
    )
    
    return PackingItem(**item_dict)

@router.get("/{trip_id}", response_model=List[PackingItem])
async def get_trip_packing_items(trip_id: str, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=400, detail="Invalid trip ID")
    
    trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip_obj = Trip(**trip)
    
    # Check if user has access to this trip
    if trip_obj.owner_id != current_user.id and current_user.id not in trip_obj.collaborators:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return trip_obj.packing_items

@router.put("/{trip_id}/{item_id}", response_model=PackingItem)
async def update_packing_item(trip_id: str, item_id: str, item_update: PackingItem, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    if not ObjectId.is_valid(trip_id) or not ObjectId.is_valid(item_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    
    trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip_obj = Trip(**trip)
    
    # Check if user has access to this trip
    if trip_obj.owner_id != current_user.id and current_user.id not in trip_obj.collaborators:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update packing item
    item_dict = item_update.dict()
    item_dict["_id"] = ObjectId(item_id)
    
    await db.trips.update_one(
        {"_id": ObjectId(trip_id), "packing_items._id": ObjectId(item_id)},
        {"$set": {"packing_items.$": item_dict}}
    )
    
    return PackingItem(**item_dict)

@router.delete("/{trip_id}/{item_id}")
async def delete_packing_item(trip_id: str, item_id: str, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    if not ObjectId.is_valid(trip_id) or not ObjectId.is_valid(item_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    
    trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip_obj = Trip(**trip)
    
    # Check if user has access to this trip
    if trip_obj.owner_id != current_user.id and current_user.id not in trip_obj.collaborators:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Remove packing item
    await db.trips.update_one(
        {"_id": ObjectId(trip_id)},
        {"$pull": {"packing_items": {"_id": ObjectId(item_id)}}}
    )
    
    return {"message": "Packing item deleted successfully"}

@router.put("/{trip_id}/{item_id}/toggle")
async def toggle_packing_item(trip_id: str, item_id: str, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    if not ObjectId.is_valid(trip_id) or not ObjectId.is_valid(item_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    
    trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip_obj = Trip(**trip)
    
    # Check if user has access to this trip
    if trip_obj.owner_id != current_user.id and current_user.id not in trip_obj.collaborators:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Find the item and toggle its packed status
    for item in trip_obj.packing_items:
        if str(item.id) == item_id:
            new_packed_status = not item.packed
            await db.trips.update_one(
                {"_id": ObjectId(trip_id), "packing_items._id": ObjectId(item_id)},
                {"$set": {"packing_items.$.packed": new_packed_status}}
            )
            return {"packed": new_packed_status}
    
    raise HTTPException(status_code=404, detail="Packing item not found")

@router.get("/{trip_id}/categories")
async def get_packing_categories(trip_id: str, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=400, detail="Invalid trip ID")
    
    trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip_obj = Trip(**trip)
    
    # Check if user has access to this trip
    if trip_obj.owner_id != current_user.id and current_user.id not in trip_obj.collaborators:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Group items by category
    categories = {}
    for item in trip_obj.packing_items:
        category = item.category
        if category not in categories:
            categories[category] = {"items": [], "packed_count": 0, "total_count": 0}
        
        categories[category]["items"].append(item)
        categories[category]["total_count"] += 1
        if item.packed:
            categories[category]["packed_count"] += 1
    
    return categories
