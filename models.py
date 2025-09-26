from pydantic import BaseModel, EmailStr, Field, field_serializer, model_validator
from pydantic.config import ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

class PyObjectId(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        from pydantic_core import core_schema
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.no_info_plain_validator_function(cls.validate),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str) and ObjectId.is_valid(v):
            return str(ObjectId(v))
        raise ValueError('Invalid ObjectId')

class User(BaseModel):
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    email: EmailStr
    username: str
    name: Optional[str] = None
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    profile: Optional[Dict[str, Any]] = {}
    profile_picture: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

    @field_serializer('id')
    def serialize_id(self, v):
        return str(v)

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    name: Optional[str] = None
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    profile_picture: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class Activity(BaseModel):
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    title: str
    time: str
    location: str
    activity_type: str  # food, transport, activity, lodging
    notes: Optional[str] = ""
    cost: Optional[float] = 0.0
    day: int
    order: int = 0

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

    @field_serializer('id')
    def serialize_id(self, v):
        return str(v)

class Expense(BaseModel):
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    title: str
    amount: float
    category: str  # accommodation, food, transport, entertainment
    date: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = ""

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

    @field_serializer('id')
    def serialize_id(self, v):
        return str(v)

class PackingItem(BaseModel):
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    name: str
    category: str  # clothes, toiletries, electronics, documents
    packed: bool = False
    notes: Optional[str] = ""

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

    @field_serializer('id')
    def serialize_id(self, v):
        return str(v)

class Trip(BaseModel):
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    title: str
    destination: str
    start_date: datetime
    end_date: datetime
    budget: float
    owner_id: PyObjectId
    collaborators: List[PyObjectId] = []
    activities: List[Activity] = []
    expenses: List[Expense] = []
    packing_items: List[PackingItem] = []
    notes: Optional[str] = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

    @field_serializer('id')
    def serialize_id(self, v):
        return str(v)

    @field_serializer('owner_id')
    def serialize_owner_id(self, v):
        return str(v)

    @field_serializer('collaborators')
    def serialize_collaborators(self, v):
        return [str(x) for x in v]

class TripCreate(BaseModel):
    title: str
    destination: str
    start_date: datetime
    end_date: datetime
    budget: float

class TripUpdate(BaseModel):
    title: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None
    notes: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
