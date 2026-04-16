"""
Export Readiness Service (Simplified)
Business logic for fruit grading and compliance checking
"""

from typing import List, Optional, Tuple
import io
import csv
import base64
from src.schemas.export_readiness import (
    FruitGradeRequest, FruitGradeResponse,
    ComplianceCheckRequest, ComplianceCheckResponse,
    ComplianceIssue, ExportStandardResponse,
    ExportDocumentGenerateRequest, ExportDocumentResponse
)
from src.core.supabase_client import supabase
from fastapi import HTTPException, status
import uuid
from datetime import datetime
from pathlib import Path


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
    async def grade_fruit(request: FruitGradeRequest) -> FruitGradeResponse:
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

    # ========================================================================
    # EXPORT DOCUMENTATION
    # ========================================================================

    @staticmethod
    async def generate_document(request: ExportDocumentGenerateRequest, user_id: str) -> ExportDocumentResponse:
        """Generate export documentation (CSV/PDF) and persist metadata/content."""
        try:
            orchard_check = supabase.table('orchards').select('id').eq('id', request.orchard_id).eq('user_id', user_id).execute()
            if not orchard_check.data:
                raise HTTPException(status_code=403, detail='You do not have access to this orchard')

            query = supabase.table('fruit_grades')\
                .select('*')\
                .eq('orchard_id', request.orchard_id)\
                .eq('target_market', request.target_market)

            if request.fruit_type:
                query = query.eq('fruit_type', request.fruit_type)
            if request.date_from:
                query = query.gte('created_at', request.date_from.isoformat())
            if request.date_to:
                query = query.lte('created_at', f"{request.date_to.isoformat()}T23:59:59")

            grades_result = query.order('created_at', desc=True).execute()
            grades = grades_result.data or []

            metadata_rows, summary_rows, detail_rows = ExportReadinessService._build_document_rows(request, grades)

            if request.document_format.value == 'pdf':
                content_bytes = ExportReadinessService._generate_pdf_bytes(metadata_rows, summary_rows, detail_rows)
                content = f"base64:{base64.b64encode(content_bytes).decode('utf-8')}"
                extension = 'pdf'
                size_bytes = len(content_bytes)
            else:
                content = ExportReadinessService._generate_csv_content(metadata_rows, summary_rows, detail_rows)
                extension = 'csv'
                size_bytes = len(content.encode('utf-8'))

            doc_id = str(uuid.uuid4())
            safe_market = request.target_market.replace(' ', '_').lower()
            file_name = f"{request.document_type.value}_{safe_market}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{extension}"

            doc_data = {
                'id': doc_id,
                'orchard_id': request.orchard_id,
                'user_id': user_id,
                'document_type': request.document_type.value,
                'target_market': request.target_market,
                'fruit_type': request.fruit_type,
                'file_name': file_name,
                'file_size_bytes': size_bytes,
                'status': 'completed',
                'date_from': request.date_from.isoformat() if request.date_from else None,
                'date_to': request.date_to.isoformat() if request.date_to else None,
                'generated_content': content,
            }

            result = supabase.table('export_documents').insert(doc_data).execute()
            if not result.data:
                raise HTTPException(status_code=500, detail='Failed to save generated document')

            return ExportDocumentResponse(**result.data[0])
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Failed to generate document: {str(e)}')

    @staticmethod
    async def list_documents(user_id: str, orchard_id: Optional[str] = None, limit: int = 50) -> List[ExportDocumentResponse]:
        """List generated export documents for the authenticated user."""
        try:
            query = supabase.table('export_documents')\
                .select('id, orchard_id, user_id, document_type, target_market, file_name, file_size_bytes, status, created_at')\
                .eq('user_id', user_id)

            if orchard_id:
                query = query.eq('orchard_id', orchard_id)

            result = query.order('created_at', desc=True).limit(limit).execute()
            return [ExportDocumentResponse(**item) for item in (result.data or [])]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Failed to list documents: {str(e)}')

    @staticmethod
    async def get_document_content(document_id: str, user_id: str) -> tuple[str, bytes, str]:
        """Get generated document content for download."""
        try:
            result = supabase.table('export_documents')\
                .select('file_name, generated_content')\
                .eq('id', document_id)\
                .eq('user_id', user_id)\
                .execute()

            if not result.data:
                raise HTTPException(status_code=404, detail='Document not found')

            doc = result.data[0]
            file_name = doc['file_name']
            raw_content = doc['generated_content'] or ''

            if isinstance(raw_content, str) and raw_content.startswith('base64:'):
                content_bytes = base64.b64decode(raw_content.split(':', 1)[1])
            else:
                content_bytes = str(raw_content).encode('utf-8')

            media_type = 'application/pdf' if file_name.lower().endswith('.pdf') else 'text/csv'
            return file_name, content_bytes, media_type
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Failed to fetch document: {str(e)}')

    @staticmethod
    def _build_document_rows(request: ExportDocumentGenerateRequest, grades: List[dict]) -> Tuple[List[List[str]], List[List[str]], List[List[str]]]:
        metadata_rows: List[List[str]] = [
            ['Export Documentation'],
            ['Document Type', request.document_type.value],
            ['Document Format', request.document_format.value],
            ['Target Market', request.target_market],
            ['Orchard ID', request.orchard_id],
            ['Fruit Type Filter', request.fruit_type or 'all'],
            ['Generated At', datetime.utcnow().isoformat()],
            [],
        ]

        summary_rows: List[List[str]] = []
        detail_rows: List[List[str]] = []

        if not grades:
            summary_rows.extend([
                ['Notice'],
                ['No graded fruits found for the selected filters.'],
                [],
            ])

        if request.include_summary:
            premium = len([g for g in grades if g.get('grade_category') == 'premium'])
            grade_a = len([g for g in grades if g.get('grade_category') == 'grade_a'])
            grade_b = len([g for g in grades if g.get('grade_category') == 'grade_b'])
            reject = len([g for g in grades if g.get('grade_category') == 'reject'])
            compliant_count = premium + grade_a + grade_b
            compliance_rate = (compliant_count / len(grades)) * 100 if grades else 0

            summary_rows.extend([
                ['Summary'],
                ['Total Fruits', str(len(grades))],
                ['Premium', str(premium)],
                ['Grade A', str(grade_a)],
                ['Grade B', str(grade_b)],
                ['Rejected', str(reject)],
                ['Compliance Rate (%)', str(round(compliance_rate, 1))],
                [],
            ])

        if request.include_grades:
            detail_rows.append(['Detailed Grades'])
            detail_rows.append(['Grade ID', 'Fruit Type', 'Size (mm)', 'Defect Count', 'Disease', 'Overall Grade', 'Category', 'Created At'])
            for grade in grades:
                detail_rows.append([
                    str(grade.get('id')),
                    str(grade.get('fruit_type')),
                    str(grade.get('size_mm')),
                    str(grade.get('defect_count')),
                    str(grade.get('disease_detected') or 'none'),
                    str(grade.get('overall_grade')),
                    str(grade.get('grade_category')),
                    str(grade.get('created_at')),
                ])

        return metadata_rows, summary_rows, detail_rows

    @staticmethod
    def _generate_csv_content(metadata_rows: List[List[str]], summary_rows: List[List[str]], detail_rows: List[List[str]]) -> str:
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        for row in metadata_rows + summary_rows + detail_rows:
            writer.writerow(row)
        return csv_buffer.getvalue()

    @staticmethod
    def _generate_pdf_bytes(metadata_rows: List[List[str]], summary_rows: List[List[str]], detail_rows: List[List[str]]) -> bytes:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
            from xml.sax.saxutils import escape
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'PDF generation dependency missing: {str(e)}')

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=14 * mm,
            rightMargin=14 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
            title="Export Documentation",
        )

        styles = getSampleStyleSheet()
        heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading3'],
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=6,
            spaceBefore=6,
        )
        table_header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=9,
            textColor=colors.white,
        )
        table_body_style = ParagraphStyle(
            'TableBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor('#0f172a'),
            wordWrap='CJK',
        )

        title_text = metadata_rows[0][0] if metadata_rows and metadata_rows[0] else 'Export Documentation'
        elements = []

        # Logo from web public assets for PDF heading branding.
        logo_path = Path(__file__).resolve().parents[2].parent / 'FRESH_web-desktop' / 'public' / 'videos' / 'logo.png'
        if logo_path.exists():
            try:
                elements.append(RLImage(str(logo_path), width=24 * mm, height=24 * mm))
                elements.append(Spacer(1, 4))
            except Exception:
                # If image loading fails, continue PDF generation without logo.
                pass

        elements.extend([
            Paragraph(title_text, styles['Title']),
            Spacer(1, 6),
        ])

        # Metadata table (key-value rows)
        metadata_kv = []
        for row in metadata_rows[1:]:
            if len(row) < 2 or not str(row[0]).strip():
                continue

            key = str(row[0])
            value = str(row[1])

            if key == 'Orchard ID':
                continue
            if key == 'Document Type':
                value = 'Grade Report'

            metadata_kv.append([key, value])
        if metadata_kv:
            elements.append(Paragraph('Document Information', heading_style))
            meta_table = Table(metadata_kv, colWidths=[40 * mm, 130 * mm])
            meta_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f5f9')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0f172a')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.extend([meta_table, Spacer(1, 8)])

        # Summary table
        summary_kv = [
            row for row in summary_rows
            if len(row) >= 2 and row[0] not in ('Summary', 'Notice') and str(row[0]).strip()
        ]
        notice_row = next((row for row in summary_rows if row and row[0] == 'No graded fruits found for the selected filters.'), None)

        if summary_kv or notice_row:
            elements.append(Paragraph('Summary', heading_style))
            if summary_kv:
                summary_table = Table(summary_kv, colWidths=[55 * mm, 35 * mm])
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecfeff')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0f172a')),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#a5f3fc')),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                elements.append(summary_table)
            elif notice_row:
                elements.append(Paragraph('No graded fruits found for the selected filters.', styles['BodyText']))

            elements.append(Spacer(1, 8))

        # Detailed grades table
        if len(detail_rows) > 2:
            elements.append(Paragraph('Detailed Grades', heading_style))
            headers = detail_rows[1]
            rows = detail_rows[2:]

            def _short_grade_id(value: str) -> str:
                value = (value or '').strip()
                return f'{value[:10]}...' if len(value) > 13 else value

            def _compact_datetime(value: str) -> str:
                value = (value or '').strip()
                if not value:
                    return ''
                try:
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return dt.strftime('%Y-%m-%d %H:%M')
                except ValueError:
                    return value

            header_labels = [
                'Grade ID',
                'Fruit Type',
                'Size (mm)',
                'Defect Count',
                'Disease',
                'Overall Grade',
                'Category',
                'Created At',
            ]

            table_data = [[Paragraph(escape(label), table_header_style) for label in header_labels]]

            for row in rows:
                row_values = list(row) + [''] * max(0, len(header_labels) - len(row))
                row_values = row_values[:len(header_labels)]
                row_values[0] = _short_grade_id(str(row_values[0]))
                row_values[7] = _compact_datetime(str(row_values[7]))
                table_data.append([
                    Paragraph(escape(str(cell)), table_body_style)
                    for cell in row_values
                ])

            grades_table = Table(
                table_data,
                colWidths=[24 * mm, 18 * mm, 16 * mm, 16 * mm, 28 * mm, 20 * mm, 18 * mm, 42 * mm],
                repeatRows=1,
            )
            grades_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f766e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(grades_table)

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    async def delete_document(document_id: str, user_id: str) -> None:
        """Delete generated document metadata/content."""
        try:
            check = supabase.table('export_documents').select('id').eq('id', document_id).eq('user_id', user_id).execute()
            if not check.data:
                raise HTTPException(status_code=404, detail='Document not found')

            supabase.table('export_documents').delete().eq('id', document_id).eq('user_id', user_id).execute()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Failed to delete document: {str(e)}')
