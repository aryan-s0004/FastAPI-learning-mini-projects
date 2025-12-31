from fastapi import FastAPI, Path, Query, HTTPException
from pydantic import BaseModel, Field, computed_field
from typing import Annotated, Literal, Optional
from pathlib import Path as FilePath
import json

# Create FastAPI application
app = FastAPI(title="Patient Management System")

# Path to JSON data file
DATA_FILE = FilePath("data/patients.json")


# Load patient data from JSON file
def load_data() -> dict:
    if not DATA_FILE.exists():
        return {}
    return json.loads(DATA_FILE.read_text())


# Save patient data to JSON file
def save_data(data: dict):
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2))


# Patient data model
class Patient(BaseModel):
    id: Annotated[str, Field(..., example="P001")]
    name: str
    city: str
    age: Annotated[int, Field(gt=0, lt=120)]
    gender: Literal["male", "female", "others"]
    height: Annotated[float, Field(gt=0)]
    weight: Annotated[float, Field(gt=0)]

    # Calculate BMI
    @computed_field
    @property
    def bmi(self) -> float:
        return round(self.weight / (self.height ** 2), 2)

    # Health category based on BMI
    @computed_field
    @property
    def verdict(self) -> str:
        if self.bmi < 18.5:
            return "Underweight"
        elif self.bmi < 25:
            return "Normal"
        elif self.bmi < 30:
            return "Overweight"
        return "Obese"


# Model for partial update
class PatientUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    age: Optional[int] = Field(default=None, gt=0)
    gender: Optional[Literal["male", "female", "others"]] = None
    height: Optional[float] = Field(default=None, gt=0)
    weight: Optional[float] = Field(default=None, gt=0)


# Home endpoint
@app.get("/")
def home():
    return {"message": "Patient Management System API"}


# About endpoint
@app.get("/about")
def about():
    return {"message": "CRUD API built using FastAPI and Pydantic"}


# Get all patients
@app.get("/patients")
def get_all_patients():
    return load_data()


# Get a single patient by ID
@app.get("/patients/{patient_id}")
def get_patient(patient_id: str = Path(..., example="P001")):
    data = load_data()
    if patient_id not in data:
        raise HTTPException(404, "Patient not found")
    return data[patient_id]


# Filter patients using query parameters
@app.get("/patients/filter")
def filter_patients(
    city: Optional[str] = None,
    gender: Optional[Literal["male", "female", "others"]] = None,
    min_age: Optional[int] = Query(None, ge=0),
    max_age: Optional[int] = Query(None, le=120)
):
    data = load_data()
    patients = data.values()

    if city:
        patients = filter(lambda p: p["city"].lower() == city.lower(), patients)
    if gender:
        patients = filter(lambda p: p["gender"] == gender, patients)
    if min_age is not None:
        patients = filter(lambda p: p["age"] >= min_age, patients)
    if max_age is not None:
        patients = filter(lambda p: p["age"] <= max_age, patients)

    return list(patients)


# Sort patients by selected field
@app.get("/patients/sort")
def sort_patients(
    sort_by: str = Query(..., description="age | height | weight | bmi"),
    order: str = Query("asc", description="asc | desc")
):
    if sort_by not in ["age", "height", "weight", "bmi"]:
        raise HTTPException(400, "Invalid sort field")

    data = load_data()
    return sorted(
        data.values(),
        key=lambda x: x.get(sort_by, 0),
        reverse=(order == "desc")
    )


# Create a new patient record
@app.post("/patients", status_code=201)
def create_patient(patient: Patient):
    data = load_data()
    if patient.id in data:
        raise HTTPException(400, "Patient already exists")

    data[patient.id] = patient.model_dump(exclude=["id"])
    save_data(data)
    return {"message": "Patient created successfully"}


# Replace an entire patient record
@app.put("/patients/{patient_id}")
def replace_patient(patient_id: str, patient: Patient):
    data = load_data()

    if patient_id != patient.id:
        raise HTTPException(400, "Patient ID mismatch")
    if patient_id not in data:
        raise HTTPException(404, "Patient not found")

    data[patient_id] = patient.model_dump(exclude=["id"])
    save_data(data)
    return {"message": "Patient replaced successfully"}


# Update selected patient fields
@app.patch("/patients/{patient_id}")
def update_patient(patient_id: str, updates: PatientUpdate):
    data = load_data()
    if patient_id not in data:
        raise HTTPException(404, "Patient not found")

    for key, value in updates.model_dump(exclude_unset=True).items():
        data[patient_id][key] = value

    updated_patient = Patient(id=patient_id, **data[patient_id])
    data[patient_id] = updated_patient.model_dump(exclude=["id"])

    save_data(data)
    return {"message": "Patient updated successfully"}


# Delete a patient record
@app.delete("/patients/{patient_id}")
def delete_patient(patient_id: str):
    data = load_data()
    if patient_id not in data:
        raise HTTPException(404, "Patient not found")

    del data[patient_id]
    save_data(data)
    return {"message": "Patient deleted successfully"}
