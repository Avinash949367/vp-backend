from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import List
from datetime import datetime
from models import Trip, TripCreate, TripUpdate, User, Activity, Expense
from auth import get_current_user
from database import get_database
from bson import ObjectId
from services.export_service import export_service
from config import settings

router = APIRouter()

@router.post("/", response_model=Trip)
async def create_trip(trip: TripCreate, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    trip_dict = {
        "title": trip.title,
        "destination": trip.destination,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "budget": trip.budget,
        "owner_id": current_user.id,
        "collaborators": [],
        "activities": [],
        "expenses": [],
        "packing_items": [],
        "notes": "",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.trips.insert_one(trip_dict)
    trip_dict["_id"] = result.inserted_id
    
    return Trip(**trip_dict)

@router.get("/", response_model=List[Trip])
async def get_user_trips(current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    trips = []
    async for trip in db.trips.find({
        "$or": [
            {"owner_id": current_user.id},
            {"collaborators": current_user.id}
        ]
    }).sort("created_at", -1):
        trips.append(Trip(**trip))
    
    return trips

@router.get("/{trip_id}", response_model=Trip)
async def get_trip(trip_id: str, current_user: User = Depends(get_current_user)):
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
    
    return trip_obj

@router.put("/{trip_id}", response_model=Trip)
async def update_trip(trip_id: str, trip_update: TripUpdate, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=400, detail="Invalid trip ID")
    
    trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip_obj = Trip(**trip)
    
    # Check if user is the owner
    if trip_obj.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only trip owner can update trip details")
    
    # Update only provided fields
    update_data = {k: v for k, v in trip_update.dict().items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.trips.update_one(
            {"_id": ObjectId(trip_id)},
            {"$set": update_data}
        )
    
    # Return updated trip
    updated_trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    return Trip(**updated_trip)

@router.delete("/{trip_id}")
async def delete_trip(trip_id: str, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=400, detail="Invalid trip ID")
    
    trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip_obj = Trip(**trip)
    
    # Check if user is the owner
    if trip_obj.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only trip owner can delete trip")
    
    await db.trips.delete_one({"_id": ObjectId(trip_id)})
    return {"message": "Trip deleted successfully"}

@router.post("/{trip_id}/collaborators/{user_email}")
async def add_collaborator(trip_id: str, user_email: str, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=400, detail="Invalid trip ID")
    
    trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip_obj = Trip(**trip)
    
    # Check if user is the owner
    if trip_obj.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only trip owner can add collaborators")
    
    # Find user by email
    user = await db.users.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_obj = User(**user)
    
    # Add collaborator if not already added
    if user_obj.id not in trip_obj.collaborators:
        await db.trips.update_one(
            {"_id": ObjectId(trip_id)},
            {"$push": {"collaborators": user_obj.id}}
        )
    
    return {"message": "Collaborator added successfully"}

@router.post("/join/{trip_id}")
async def join_trip(trip_id: str, current_user: User = Depends(get_current_user)):
    """Join a trip using trip ID"""
    db = await get_database()
    
    if not ObjectId.is_valid(trip_id):
        raise HTTPException(status_code=400, detail="Invalid trip ID")
    
    trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip_obj = Trip(**trip)
    
    # Check if user is already the owner
    if trip_obj.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="You are already the owner of this trip")
    
    # Check if user is already a collaborator
    if current_user.id in trip_obj.collaborators:
        raise HTTPException(status_code=400, detail="You are already a collaborator of this trip")
    
    # Add user as collaborator
    await db.trips.update_one(
        {"_id": ObjectId(trip_id)},
        {"$push": {"collaborators": current_user.id}}
    )
    
    # Return the trip details
    updated_trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    return Trip(**updated_trip)

@router.get("/{trip_id}/export/pdf")
async def export_trip_pdf(trip_id: str, current_user: User = Depends(get_current_user)):
    """Export trip as PDF report"""
    if not settings.enable_pdf_export:
        raise HTTPException(status_code=403, detail="PDF export is disabled")

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

    # Get activities and expenses
    activities = []
    async for activity in db.activities.find({"trip_id": ObjectId(trip_id)}):
        activities.append(Activity(**activity))

    expenses = []
    async for expense in db.expenses.find({"trip_id": ObjectId(trip_id)}):
        expenses.append(Expense(**expense))

    # Generate PDF
    pdf_data = export_service.generate_trip_pdf(trip_obj, activities, expenses)

    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={trip_obj.title.replace(' ', '_')}_report.pdf"}
    )

@router.get("/{trip_id}/export/calendar")
async def export_trip_calendar(trip_id: str, current_user: User = Depends(get_current_user)):
    """Export trip activities as calendar file"""
    if not settings.enable_calendar_export:
        raise HTTPException(status_code=403, detail="Calendar export is disabled")

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

    # Get activities
    activities = []
    async for activity in db.activities.find({"trip_id": ObjectId(trip_id)}):
        activities.append(Activity(**activity))

    # Generate ICS calendar
    ics_content = export_service.generate_calendar_ics(trip_obj, activities)

    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename={trip_obj.title.replace(' ', '_')}_calendar.ics"}
    )

@router.get("/{trip_id}/export/json")
async def export_trip_json(trip_id: str, current_user: User = Depends(get_current_user)):
    """Export trip data as JSON"""
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

    # Get activities and expenses
    activities = []
    async for activity in db.activities.find({"trip_id": ObjectId(trip_id)}):
        activities.append(Activity(**activity))

    expenses = []
    async for expense in db.expenses.find({"trip_id": ObjectId(trip_id)}):
        expenses.append(Expense(**expense))

    # Generate JSON export
    json_data = export_service.export_trip_data(trip_obj, activities, expenses)

    return Response(
        content=json_data,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={trip_obj.title.replace(' ', '_')}_data.json"}
    )
