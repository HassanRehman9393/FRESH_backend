"""
Export Readiness Schemas (Simplified)
Pydantic models for export grading and compliance checking
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    CONDITIONAL = "conditional"


class GradeCategory(str, Enum):
    PREMIUM = "premium"
    GRADE_A = "grade_a"
    GRADE_B = "grade_b"
    REJECT = "reject"


class PestTolerance(str, Enum):
    ZERO = "zero"
    LOW = "low"
    MEDIUM = "medium"


class DiseaseTolerance(str, Enum):
    ZERO = "zero"
    LOW = "low"
    MEDIUM = "medium"


class ExportDocumentType(str, Enum):
    GRADE_REPORT = "grade_report"
    COMPLIANCE_REPORT = "compliance_report"
    READINESS_SUMMARY = "readiness_summary"


# ============================================================================
# EXPORT STANDARDS
# ============================================================================

class ExportStandardResponse(BaseModel):
    id: str
    country: str
    fruit_type: str
    min_size_mm: int
    max_defects_percent: int
    pest_tolerance: str
    disease_tolerance: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# FRUIT GRADING
# ============================================================================

class FruitGradeRequest(BaseModel):
    orchard_id: str
    fruit_type: str = Field(..., max_length=50)
    size_mm: float = Field(..., gt=0, description="Fruit size in mm")
    defect_count: int = Field(0, ge=0, description="Number of defects")
    disease_detected: Optional[str] = Field(None, description="Disease type if any")
    target_market: str = Field(..., description="Target export market")


class FruitGradeResponse(BaseModel):
    grade_id: str
    orchard_id: str
    fruit_type: str
    size_mm: float
    defect_count: int
    disease_detected: Optional[str]
    overall_grade: float
    grade_category: str
    target_market: str
    graded_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# COMPLIANCE CHECKING
# ============================================================================

class ComplianceCheckRequest(BaseModel):
    fruit_type: str
    size_mm: float
    defect_percentage: float = Field(..., ge=0, le=100)
    disease_detected: Optional[str] = None
    pest_detected: bool = False
    target_market: str


class ComplianceIssue(BaseModel):
    criterion: str
    status: str  # 'pass', 'fail', 'warning'
    message: str
    standard_value: str
    actual_value: str


class ComplianceCheckResponse(BaseModel):
    compliance_status: str
    target_market: str
    fruit_type: str
    issues: List[ComplianceIssue]
    checked_at: datetime


# ============================================================================
# MARKET INFO
# ============================================================================

class MarketInfo(BaseModel):
    country: str
    supported_fruits: List[str]
    
    class Config:
        from_attributes = True


# ============================================================================
# EXPORT DOCUMENTATION
# ============================================================================

class ExportDocumentGenerateRequest(BaseModel):
    orchard_id: str
    target_market: str
    document_type: ExportDocumentType = ExportDocumentType.GRADE_REPORT
    fruit_type: Optional[str] = None
    include_grades: bool = True
    include_summary: bool = True
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class ExportDocumentResponse(BaseModel):
    id: str
    orchard_id: str
    user_id: str
    document_type: str
    target_market: str
    file_name: str
    file_size_bytes: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
