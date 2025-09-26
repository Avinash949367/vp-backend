from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models import Activity, Trip, User
from auth import get_current_user
from database import get_database
from bson import ObjectId

router = APIRouter()

@router.post("/{trip_id}", response_model=Activity)
async def create_activity(trip_id: str, activity: Activity, current_user: User = Depends(get_current_user)):
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
    
    # Add activity to trip
    activity_dict = activity.dict()
    activity_dict["_id"] = ObjectId()
    
    await db.trips.update_one(
        {"_id": ObjectId(trip_id)},
        {"$push": {"activities": activity_dict}}
    )
    
    return Activity(**activity_dict)

@router.get("/{trip_id}", response_model=List[Activity])
async def get_trip_activities(trip_id: str, current_user: User = Depends(get_current_user)):
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
    
    return trip_obj.activities

@router.put("/{trip_id}/{activity_id}", response_model=Activity)
async def update_activity(trip_id: str, activity_id: str, activity_update: Activity, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    if not ObjectId.is_valid(trip_id) or not ObjectId.is_valid(activity_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    
    trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip_obj = Trip(**trip)
    
    # Check if user has access to this trip
    if trip_obj.owner_id != current_user.id and current_user.id not in trip_obj.collaborators:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update activity
    activity_dict = activity_update.dict()
    activity_dict["_id"] = ObjectId(activity_id)
    
    await db.trips.update_one(
        {"_id": ObjectId(trip_id), "activities._id": ObjectId(activity_id)},
        {"$set": {"activities.$": activity_dict}}
    )
    
    return Activity(**activity_dict)

@router.delete("/{trip_id}/{activity_id}")
async def delete_activity(trip_id: str, activity_id: str, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    if not ObjectId.is_valid(trip_id) or not ObjectId.is_valid(activity_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    
    trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip_obj = Trip(**trip)
    
    # Check if user has access to this trip
    if trip_obj.owner_id != current_user.id and current_user.id not in trip_obj.collaborators:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Remove activity
    await db.trips.update_one(
        {"_id": ObjectId(trip_id)},
        {"$pull": {"activities": {"_id": ObjectId(activity_id)}}}
    )
    
    return {"message": "Activity deleted successfully"}

@router.put("/{trip_id}/reorder")
async def reorder_activities(trip_id: str, activity_orders: List[dict], current_user: User = Depends(get_current_user)):
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
    
    # Update activity orders
    for order_data in activity_orders:
        activity_id = order_data.get("activity_id")
        new_order = order_data.get("order")
        
        if ObjectId.is_valid(activity_id):
            await db.trips.update_one(
                {"_id": ObjectId(trip_id), "activities._id": ObjectId(activity_id)},
                {"$set": {"activities.$.order": new_order}}
            )
    
    return {"message": "Activities reordered successfully"}
