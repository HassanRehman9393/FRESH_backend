"""
Export Readiness Service (Simplified)
Business logic for fruit grading and compliance checking
"""

from typing import List, Optional
from src.schemas.export_readiness import (
    FruitGradeRequest, FruitGradeResponse,
    ComplianceCheckRequest, ComplianceCheckResponse,
    ComplianceIssue, ExportStandardResponse
)
from src.core.supabase_client import supabase
from fastapi import HTTPException, status
import uuid
from datetime import datetime


class ExportReadinessService:
    
    # ========================================================================
    # GRADING LOGIC
    # ========================================================================
    
    @staticmethod
    def calculate_grade(size_mm: float, defect_count: int, disease_detected: Optional[str], 
                       standard: dict) -> tuple[float, str]:
        """
        Calculate overall grade based on simplified scoring
        Returns: (overall_grade, grade_category)
        """
        # Size score (25%): Compare against minimum
        if size_mm >= standard['min_size_mm'] + 10:
            size_score = 100
        elif size_mm >= standard['min_size_mm']:
            size_score = 80
        else:
            size_score = max(0, 50 - (standard['min_size_mm'] - size_mm) * 5)
        
        # Defect score (30%): Based on defect count
        defect_score = max(0, 100 - (defect_count * 15))
        
        # Disease score (35%): Presence of disease
        if disease_detected and disease_detected != 'none':
            disease_score = 0 if standard['disease_tolerance'] == 'zero' else 40
        else:
            disease_score = 100
        
        # Uniformity score (10%): Default 85
        uniformity_score = 85
        
        # Calculate weighted overall grade
        overall = (
            (size_score * 0.25) +
            (defect_score * 0.30) +
            (disease_score * 0.35) +
            (uniformity_score * 0.10)
        )
        
        # Determine category
        if overall >= 90:
            category = 'premium'
        elif overall >= 75:
            category = 'grade_a'
        elif overall >= 60:
            category = 'grade_b'
        else:
            category = 'reject'
        
        return round(overall, 2), category
    
    @staticmethod
    async def grade_fruit(request: FruitGradeRequest, user_id: str) -> FruitGradeResponse:
        """Grade a single fruit for export"""
        try:
            # Get export standard for target market
            standard_result = supabase.table('export_standards').select('*').eq(
                'country', request.target_market
            ).eq('fruit_type', request.fruit_type).execute()
            
            if not standard_result.data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No standards found for {request.target_market} - {request.fruit_type}"
                )
            
            standard = standard_result.data[0]
            
            # Calculate grade
            overall_grade, grade_category = ExportReadinessService.calculate_grade(
                request.size_mm,
                request.defect_count,
                request.disease_detected,
                standard
            )
            
            # Insert grade record
            grade_id = str(uuid.uuid4())
            grade_data = {
                'id': grade_id,
                'orchard_id': request.orchard_id,
                'fruit_type': request.fruit_type,
                'size_mm': request.size_mm,
                'defect_count': request.defect_count,
                'disease_detected': request.disease_detected,
                'overall_grade': overall_grade,
                'grade_category': grade_category,
                'target_market': request.target_market
            }
            
            result = supabase.table('fruit_grades').insert(grade_data).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to save grade")
            
            return FruitGradeResponse(
                grade_id=grade_id,
                orchard_id=request.orchard_id,
                fruit_type=request.fruit_type,
                size_mm=request.size_mm,
                defect_count=request.defect_count,
                disease_detected=request.disease_detected,
                overall_grade=overall_grade,
                grade_category=grade_category,
                target_market=request.target_market,
                graded_at=datetime.now()
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to grade fruit: {str(e)}"
            )
    
    # ========================================================================
    # COMPLIANCE CHECKING
    # ========================================================================
    
    @staticmethod
    async def check_compliance(request: ComplianceCheckRequest) -> ComplianceCheckResponse:
        """Check compliance against export standards"""
        try:
            # Get standard
            standard_result = supabase.table('export_standards').select('*').eq(
                'country', request.target_market
            ).eq('fruit_type', request.fruit_type).execute()
            
            if not standard_result.data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No standards found for {request.target_market}"
                )
            
            standard = standard_result.data[0]
            issues = []
            
            # Check size
            if request.size_mm < standard['min_size_mm']:
                issues.append(ComplianceIssue(
                    criterion="Size",
                    status="fail",
                    message=f"Fruit too small for {request.target_market}",
                    standard_value=f"≥{standard['min_size_mm']}mm",
                    actual_value=f"{request.size_mm}mm"
                ))
            else:
                issues.append(ComplianceIssue(
                    criterion="Size",
                    status="pass",
                    message="Meets size requirement",
                    standard_value=f"≥{standard['min_size_mm']}mm",
                    actual_value=f"{request.size_mm}mm"
                ))
            
            # Check defects
            if request.defect_percentage > standard['max_defects_percent']:
                issues.append(ComplianceIssue(
                    criterion="Defects",
                    status="fail",
                    message="Exceeds maximum defect percentage",
                    standard_value=f"≤{standard['max_defects_percent']}%",
                    actual_value=f"{request.defect_percentage}%"
                ))
            else:
                issues.append(ComplianceIssue(
                    criterion="Defects",
                    status="pass",
                    message="Within acceptable defect range",
                    standard_value=f"≤{standard['max_defects_percent']}%",
                    actual_value=f"{request.defect_percentage}%"
                ))
            
            # Check disease
            if request.disease_detected:
                if standard['disease_tolerance'] == 'zero':
                    issues.append(ComplianceIssue(
                        criterion="Disease",
                        status="fail",
                        message=f"Disease detected: {request.disease_detected}",
                        standard_value="Zero tolerance",
                        actual_value=request.disease_detected
                    ))
                else:
                    issues.append(ComplianceIssue(
                        criterion="Disease",
                        status="warning",
                        message=f"Disease detected but within tolerance",
                        standard_value=f"{standard['disease_tolerance']} tolerance",
                        actual_value=request.disease_detected
                    ))
            else:
                issues.append(ComplianceIssue(
                    criterion="Disease",
                    status="pass",
                    message="No disease detected",
                    standard_value="Disease-free preferred",
                    actual_value="None"
                ))
            
            # Check pests
            if request.pest_detected:
                issues.append(ComplianceIssue(
                    criterion="Pests",
                    status="fail",
                    message="Pest detected",
                    standard_value="Zero tolerance",
                    actual_value="Pest present"
                ))
            else:
                issues.append(ComplianceIssue(
                    criterion="Pests",
                    status="pass",
                    message="No pests detected",
                    standard_value="Pest-free",
                    actual_value="None"
                ))
            
            # Determine overall status
            failed = any(i.status == 'fail' for i in issues)
            warnings = any(i.status == 'warning' for i in issues)
            
            if failed:
                compliance_status = 'non_compliant'
            elif warnings:
                compliance_status = 'conditional'
            else:
                compliance_status = 'compliant'
            
            return ComplianceCheckResponse(
                compliance_status=compliance_status,
                target_market=request.target_market,
                fruit_type=request.fruit_type,
                issues=issues,
                checked_at=datetime.now()
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to check compliance: {str(e)}"
            )
    
    # ========================================================================
    # EXPORT STANDARDS
    # ========================================================================
    
    @staticmethod
    async def get_standards(country: str, fruit_type: str) -> ExportStandardResponse:
        """Get export standards for a specific market"""
        try:
            result = supabase.table('export_standards').select('*').eq(
                'country', country
            ).eq('fruit_type', fruit_type).execute()
            
            if not result.data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No standards found for {country} - {fruit_type}"
                )
            
            data = result.data[0]
            return ExportStandardResponse(**data)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch standards: {str(e)}"
            )
    
    @staticmethod
    async def get_all_markets():
        """Get all available export markets"""
        try:
            result = supabase.table('export_standards').select('country, fruit_type').execute()
            
            # Group by country
            markets = {}
            for row in result.data:
                country = row['country']
                if country not in markets:
                    markets[country] = []
                markets[country].append(row['fruit_type'])
            
            return [
                {"country": country, "supported_fruits": fruits}
                for country, fruits in markets.items()
            ]
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch markets: {str(e)}"
            )
