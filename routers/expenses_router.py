from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models import Expense, Trip, User
from auth import get_current_user
from database import get_database
from bson import ObjectId

router = APIRouter()

@router.post("/{trip_id}", response_model=Expense)
async def create_expense(trip_id: str, expense: Expense, current_user: User = Depends(get_current_user)):
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
    
    # Add expense to trip
    expense_dict = expense.dict()
    expense_dict["_id"] = ObjectId()
    
    await db.trips.update_one(
        {"_id": ObjectId(trip_id)},
        {"$push": {"expenses": expense_dict}}
    )
    
    return Expense(**expense_dict)

@router.get("/{trip_id}", response_model=List[Expense])
async def get_trip_expenses(trip_id: str, current_user: User = Depends(get_current_user)):
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
    
    return trip_obj.expenses

@router.put("/{trip_id}/{expense_id}", response_model=Expense)
async def update_expense(trip_id: str, expense_id: str, expense_update: Expense, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    if not ObjectId.is_valid(trip_id) or not ObjectId.is_valid(expense_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    
    trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip_obj = Trip(**trip)
    
    # Check if user has access to this trip
    if trip_obj.owner_id != current_user.id and current_user.id not in trip_obj.collaborators:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update expense
    expense_dict = expense_update.dict()
    expense_dict["_id"] = ObjectId(expense_id)
    
    await db.trips.update_one(
        {"_id": ObjectId(trip_id), "expenses._id": ObjectId(expense_id)},
        {"$set": {"expenses.$": expense_dict}}
    )
    
    return Expense(**expense_dict)

@router.delete("/{trip_id}/{expense_id}")
async def delete_expense(trip_id: str, expense_id: str, current_user: User = Depends(get_current_user)):
    db = await get_database()
    
    if not ObjectId.is_valid(trip_id) or not ObjectId.is_valid(expense_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    
    trip = await db.trips.find_one({"_id": ObjectId(trip_id)})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip_obj = Trip(**trip)
    
    # Check if user has access to this trip
    if trip_obj.owner_id != current_user.id and current_user.id not in trip_obj.collaborators:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Remove expense
    await db.trips.update_one(
        {"_id": ObjectId(trip_id)},
        {"$pull": {"expenses": {"_id": ObjectId(expense_id)}}}
    )
    
    return {"message": "Expense deleted successfully"}

@router.get("/{trip_id}/summary")
async def get_expense_summary(trip_id: str, current_user: User = Depends(get_current_user)):
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
    
    # Calculate summary
    total_spent = sum(expense.amount for expense in trip_obj.expenses)
    budget = trip_obj.budget
    remaining = budget - total_spent
    
    # Category breakdown
    category_totals = {}
    for expense in trip_obj.expenses:
        category = expense.category
        if category in category_totals:
            category_totals[category] += expense.amount
        else:
            category_totals[category] = expense.amount
    
    return {
        "budget": budget,
        "total_spent": total_spent,
        "remaining": remaining,
        "category_breakdown": category_totals
    }
