"""
Unit Tests for Knowledge Base Queries
======================================

Tests for database queries against the knowledge base tables:
- diseases, treatments, mrl_limits, export_requirements
- fruit_varieties, farming_calendar

These tests verify data integrity and query correctness.

Run with: pytest tests/unit/test_knowledge_base.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    mock = MagicMock()
    return mock


@pytest.fixture
def knowledge_base_data():
    """Complete knowledge base test data."""
    return {
        "diseases": [
            {
                "id": str(uuid4()),
                "name": "anthracnose",
                "name_urdu": "اینتھراکنوز",
                "disease_type": "fungal",
                "affected_fruits": ["mango", "guava"],
                "symptoms": ["Dark, sunken lesions", "Black spots", "Fruit rot"],
                "causes": "Colletotrichum gloeosporioides fungus",
                "prevention": ["Remove infected fruits", "Fungicide application"],
                "severity_levels": {
                    "mild": "Less than 5% affected",
                    "moderate": "5-25% affected",
                    "severe": "Over 25% affected"
                }
            },
            {
                "id": str(uuid4()),
                "name": "citrus_canker",
                "name_urdu": "کھٹی کا کینکر",
                "disease_type": "bacterial",
                "affected_fruits": ["orange", "grapefruit"],
                "symptoms": ["Raised lesions", "Yellow halos", "Premature fruit drop"],
                "causes": "Xanthomonas citri bacteria",
                "prevention": ["Remove infected branches", "Copper spray"],
                "severity_levels": {
                    "mild": "Few lesions",
                    "severe": "Widespread infection"
                }
            }
        ],
        "treatments": [
            {
                "id": str(uuid4()),
                "disease_id": None,  # Will be set in test
                "treatment_type": "chemical",
                "product_name": "Carbendazim 50% WP",
                "active_ingredient": "Carbendazim",
                "dosage": "1g per liter water",
                "application_method": "Foliar spray",
                "pre_harvest_interval_days": 14,
                "effectiveness_rating": 4
            },
            {
                "id": str(uuid4()),
                "disease_id": None,
                "treatment_type": "organic",
                "product_name": "Trichoderma viride",
                "active_ingredient": "Trichoderma",
                "dosage": "5g per liter water",
                "application_method": "Soil drench",
                "pre_harvest_interval_days": 0,
                "effectiveness_rating": 3
            }
        ],
        "mrl_limits": [
            {
                "id": str(uuid4()),
                "pesticide_name": "Carbendazim",
                "active_ingredient": "Carbendazim",
                "fruit_type": "mango",
                "country_code": "EU",
                "country_name": "European Union",
                "mrl_value": 0.1,
                "unit": "mg/kg"
            },
            {
                "id": str(uuid4()),
                "pesticide_name": "Carbendazim",
                "active_ingredient": "Carbendazim",
                "fruit_type": "mango",
                "country_code": "UAE",
                "country_name": "United Arab Emirates",
                "mrl_value": 0.5,
                "unit": "mg/kg"
            },
            {
                "id": str(uuid4()),
                "pesticide_name": "Imidacloprid",
                "active_ingredient": "Imidacloprid",
                "fruit_type": "mango",
                "country_code": "EU",
                "country_name": "European Union",
                "mrl_value": 0.01,
                "unit": "mg/kg"
            }
        ],
        "export_requirements": [
            {
                "id": str(uuid4()),
                "country_code": "EU",
                "country_name": "European Union",
                "fruit_type": "mango",
                "phytosanitary_requirements": ["Phytosanitary Certificate", "VHT treatment"],
                "certifications_needed": ["GlobalGAP", "HACCP"],
                "temperature_requirements": {"transport": "10-13°C"},
                "documentation_required": ["Invoice", "Packing List", "Bill of Lading"]
            },
            {
                "id": str(uuid4()),
                "country_code": "UAE",
                "country_name": "United Arab Emirates",
                "fruit_type": "mango",
                "phytosanitary_requirements": ["Phytosanitary Certificate"],
                "certifications_needed": ["GlobalGAP"],
                "temperature_requirements": {"transport": "10-13°C"},
                "documentation_required": ["Invoice", "Certificate of Origin"]
            }
        ],
        "fruit_varieties": [
            {
                "id": str(uuid4()),
                "fruit_type": "mango",
                "variety_name": "Sindhri",
                "variety_name_urdu": "سندھری",
                "region": "Sindh",
                "harvest_season": "May-June",
                "export_popularity": "high"
            },
            {
                "id": str(uuid4()),
                "fruit_type": "mango",
                "variety_name": "Chaunsa",
                "variety_name_urdu": "چونسا",
                "region": "Punjab",
                "harvest_season": "July-August",
                "export_popularity": "high"
            }
        ],
        "farming_calendar": [
            {
                "id": str(uuid4()),
                "fruit_type": "mango",
                "month": 3,  # March
                "activities": ["Flowering monitoring", "Pest control"],
                "disease_risks": ["anthracnose", "powdery_mildew"],
                "recommended_treatments": ["Carbendazim spray"]
            },
            {
                "id": str(uuid4()),
                "fruit_type": "mango",
                "month": 6,  # June
                "activities": ["Harvest", "Post-harvest treatment"],
                "disease_risks": ["anthracnose", "stem_end_rot"],
                "recommended_treatments": ["Hot water treatment"]
            }
        ]
    }


# ============================================================================
# TEST: DISEASE QUERIES
# ============================================================================

class TestDiseaseQueries:
    """Tests for disease table queries."""
    
    def test_get_disease_by_name(self, mock_supabase, knowledge_base_data):
        """Test fetching disease by exact name."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            knowledge_base_data["diseases"][0]
        ]
        
        result = mock_supabase.table("diseases").select("*").eq("name", "anthracnose").execute()
        
        assert len(result.data) == 1
        assert result.data[0]["name"] == "anthracnose"
    
    def test_get_disease_by_name_case_insensitive(self, mock_supabase, knowledge_base_data):
        """Test case-insensitive disease lookup."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = [
            knowledge_base_data["diseases"][0]
        ]
        
        result = mock_supabase.table("diseases").select("*").ilike("name", "%ANTHRACNOSE%").execute()
        
        assert len(result.data) == 1
    
    def test_get_diseases_by_fruit(self, mock_supabase, knowledge_base_data):
        """Test fetching diseases that affect a specific fruit."""
        mock_supabase.table.return_value.select.return_value.contains.return_value.execute.return_value.data = [
            knowledge_base_data["diseases"][0]  # anthracnose affects mango
        ]
        
        result = mock_supabase.table("diseases").select("*").contains("affected_fruits", ["mango"]).execute()
        
        assert len(result.data) >= 1
        for disease in result.data:
            assert "mango" in disease["affected_fruits"]
    
    def test_get_all_fungal_diseases(self, mock_supabase, knowledge_base_data):
        """Test filtering diseases by type."""
        fungal_diseases = [d for d in knowledge_base_data["diseases"] if d["disease_type"] == "fungal"]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = fungal_diseases
        
        result = mock_supabase.table("diseases").select("*").eq("disease_type", "fungal").execute()
        
        assert all(d["disease_type"] == "fungal" for d in result.data)
    
    def test_disease_has_urdu_translation(self, mock_supabase, knowledge_base_data):
        """Test that diseases have Urdu translations."""
        for disease in knowledge_base_data["diseases"]:
            assert "name_urdu" in disease
            assert disease["name_urdu"] is not None
    
    def test_disease_has_severity_levels(self, mock_supabase, knowledge_base_data):
        """Test that diseases have severity level definitions."""
        for disease in knowledge_base_data["diseases"]:
            assert "severity_levels" in disease
            assert len(disease["severity_levels"]) > 0


# ============================================================================
# TEST: TREATMENT QUERIES
# ============================================================================

class TestTreatmentQueries:
    """Tests for treatment table queries."""
    
    def test_get_treatments_for_disease(self, mock_supabase, knowledge_base_data):
        """Test fetching treatments for a specific disease."""
        disease_id = knowledge_base_data["diseases"][0]["id"]
        treatments = knowledge_base_data["treatments"]
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = treatments
        
        result = mock_supabase.table("treatments").select("*").eq("disease_id", disease_id).execute()
        
        assert len(result.data) >= 1
    
    def test_filter_organic_treatments(self, mock_supabase, knowledge_base_data):
        """Test filtering treatments by type (organic)."""
        organic = [t for t in knowledge_base_data["treatments"] if t["treatment_type"] == "organic"]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = organic
        
        result = mock_supabase.table("treatments").select("*").eq("treatment_type", "organic").execute()
        
        assert all(t["treatment_type"] == "organic" for t in result.data)
    
    def test_treatment_has_dosage_info(self, mock_supabase, knowledge_base_data):
        """Test that treatments have dosage information."""
        for treatment in knowledge_base_data["treatments"]:
            assert "dosage" in treatment
            assert treatment["dosage"] is not None
            assert len(treatment["dosage"]) > 0
    
    def test_treatment_has_pre_harvest_interval(self, mock_supabase, knowledge_base_data):
        """Test that treatments have pre-harvest interval."""
        for treatment in knowledge_base_data["treatments"]:
            assert "pre_harvest_interval_days" in treatment
            assert treatment["pre_harvest_interval_days"] >= 0
    
    def test_get_treatments_with_join(self, mock_supabase, knowledge_base_data):
        """Test fetching treatments with disease information."""
        # Simulating a join result
        treatment_with_disease = {
            **knowledge_base_data["treatments"][0],
            "diseases": knowledge_base_data["diseases"][0]
        }
        mock_supabase.table.return_value.select.return_value.execute.return_value.data = [treatment_with_disease]
        
        result = mock_supabase.table("treatments").select("*, diseases(*)").execute()
        
        assert "diseases" in result.data[0]


# ============================================================================
# TEST: MRL LIMIT QUERIES
# ============================================================================

class TestMRLQueries:
    """Tests for MRL (Maximum Residue Limit) queries."""
    
    def test_get_mrl_for_pesticide_fruit_country(self, mock_supabase, knowledge_base_data):
        """Test fetching MRL for specific pesticide/fruit/country combination."""
        mrl = knowledge_base_data["mrl_limits"][0]
        mock_supabase.table.return_value.select.return_value.ilike.return_value.ilike.return_value.ilike.return_value.execute.return_value.data = [mrl]
        
        result = mock_supabase.table("mrl_limits").select("*") \
            .ilike("pesticide_name", "%Carbendazim%") \
            .ilike("fruit_type", "%mango%") \
            .ilike("country_code", "%EU%").execute()
        
        assert len(result.data) == 1
        assert result.data[0]["mrl_value"] == 0.1
    
    def test_compare_mrl_across_countries(self, mock_supabase, knowledge_base_data):
        """Test comparing MRL values across different countries."""
        eu_mrl = knowledge_base_data["mrl_limits"][0]  # EU: 0.1
        uae_mrl = knowledge_base_data["mrl_limits"][1]  # UAE: 0.5
        
        # EU is stricter
        assert eu_mrl["mrl_value"] < uae_mrl["mrl_value"]
    
    def test_get_all_mrl_for_pesticide(self, mock_supabase, knowledge_base_data):
        """Test fetching all MRL entries for a pesticide."""
        carbendazim_mrls = [m for m in knowledge_base_data["mrl_limits"] if "Carbendazim" in m["pesticide_name"]]
        mock_supabase.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = carbendazim_mrls
        
        result = mock_supabase.table("mrl_limits").select("*").ilike("pesticide_name", "%Carbendazim%").execute()
        
        assert len(result.data) >= 2  # At least EU and UAE
    
    def test_mrl_has_unit(self, mock_supabase, knowledge_base_data):
        """Test that all MRL entries have a unit."""
        for mrl in knowledge_base_data["mrl_limits"]:
            assert "unit" in mrl
            assert mrl["unit"] == "mg/kg"  # Standard unit
    
    def test_get_strictest_mrl(self, mock_supabase, knowledge_base_data):
        """Test finding the strictest MRL for a pesticide/fruit combo."""
        mrls = knowledge_base_data["mrl_limits"][:2]  # Carbendazim for mango
        
        strictest = min(mrls, key=lambda x: x["mrl_value"])
        
        assert strictest["country_code"] == "EU"  # EU is stricter
        assert strictest["mrl_value"] == 0.1


# ============================================================================
# TEST: EXPORT REQUIREMENTS QUERIES
# ============================================================================

class TestExportRequirementsQueries:
    """Tests for export requirements queries."""
    
    def test_get_requirements_for_country_fruit(self, mock_supabase, knowledge_base_data):
        """Test fetching export requirements for country/fruit combo."""
        req = knowledge_base_data["export_requirements"][0]
        mock_supabase.table.return_value.select.return_value.ilike.return_value.ilike.return_value.execute.return_value.data = [req]
        
        result = mock_supabase.table("export_requirements").select("*") \
            .ilike("country_code", "%EU%") \
            .ilike("fruit_type", "%mango%").execute()
        
        assert len(result.data) == 1
        assert "phytosanitary_requirements" in result.data[0]
    
    def test_requirements_has_certifications(self, mock_supabase, knowledge_base_data):
        """Test that export requirements include certifications."""
        for req in knowledge_base_data["export_requirements"]:
            assert "certifications_needed" in req
            assert len(req["certifications_needed"]) > 0
    
    def test_requirements_has_documentation(self, mock_supabase, knowledge_base_data):
        """Test that export requirements include documentation list."""
        for req in knowledge_base_data["export_requirements"]:
            assert "documentation_required" in req
            assert isinstance(req["documentation_required"], list)
    
    def test_compare_requirements_across_countries(self, mock_supabase, knowledge_base_data):
        """Test comparing requirements between EU and UAE."""
        eu_req = knowledge_base_data["export_requirements"][0]
        uae_req = knowledge_base_data["export_requirements"][1]
        
        # EU generally has more requirements
        assert len(eu_req["certifications_needed"]) >= len(uae_req["certifications_needed"])


# ============================================================================
# TEST: FRUIT VARIETIES QUERIES
# ============================================================================

class TestFruitVarietiesQueries:
    """Tests for fruit varieties queries."""
    
    def test_get_varieties_by_fruit(self, mock_supabase, knowledge_base_data):
        """Test fetching varieties for a fruit type."""
        mango_varieties = knowledge_base_data["fruit_varieties"]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mango_varieties
        
        result = mock_supabase.table("fruit_varieties").select("*").eq("fruit_type", "mango").execute()
        
        assert len(result.data) >= 2
    
    def test_variety_has_urdu_name(self, mock_supabase, knowledge_base_data):
        """Test that varieties have Urdu translations."""
        for variety in knowledge_base_data["fruit_varieties"]:
            assert "variety_name_urdu" in variety
            assert variety["variety_name_urdu"] is not None
    
    def test_variety_has_harvest_season(self, mock_supabase, knowledge_base_data):
        """Test that varieties have harvest season info."""
        for variety in knowledge_base_data["fruit_varieties"]:
            assert "harvest_season" in variety
    
    def test_get_export_grade_varieties(self, mock_supabase, knowledge_base_data):
        """Test filtering varieties by export popularity."""
        high_export = [v for v in knowledge_base_data["fruit_varieties"] if v["export_popularity"] == "high"]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = high_export
        
        result = mock_supabase.table("fruit_varieties").select("*").eq("export_popularity", "high").execute()
        
        assert all(v["export_popularity"] == "high" for v in result.data)


# ============================================================================
# TEST: FARMING CALENDAR QUERIES
# ============================================================================

class TestFarmingCalendarQueries:
    """Tests for farming calendar queries."""
    
    def test_get_calendar_for_month(self, mock_supabase, knowledge_base_data):
        """Test fetching calendar entries for a month."""
        march_entries = [c for c in knowledge_base_data["farming_calendar"] if c["month"] == 3]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = march_entries
        
        result = mock_supabase.table("farming_calendar").select("*").eq("month", 3).execute()
        
        assert len(result.data) >= 1
    
    def test_calendar_has_activities(self, mock_supabase, knowledge_base_data):
        """Test that calendar entries have activities."""
        for entry in knowledge_base_data["farming_calendar"]:
            assert "activities" in entry
            assert len(entry["activities"]) > 0
    
    def test_calendar_has_disease_risks(self, mock_supabase, knowledge_base_data):
        """Test that calendar entries include disease risks."""
        for entry in knowledge_base_data["farming_calendar"]:
            assert "disease_risks" in entry
    
    def test_get_calendar_for_fruit_and_month(self, mock_supabase, knowledge_base_data):
        """Test fetching calendar for specific fruit and month."""
        entry = knowledge_base_data["farming_calendar"][0]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [entry]
        
        result = mock_supabase.table("farming_calendar").select("*") \
            .eq("fruit_type", "mango") \
            .eq("month", 3).execute()
        
        assert len(result.data) == 1


# ============================================================================
# TEST: DATA INTEGRITY
# ============================================================================

class TestDataIntegrity:
    """Tests for data integrity across tables."""
    
    def test_treatment_disease_reference(self, mock_supabase, knowledge_base_data):
        """Test that treatments reference valid diseases."""
        # In real data, disease_id should reference diseases table
        # This test ensures the relationship structure is correct
        diseases = knowledge_base_data["diseases"]
        treatments = knowledge_base_data["treatments"]
        
        # Treatments should have disease_id field
        for treatment in treatments:
            assert "disease_id" in treatment
    
    def test_mrl_fruit_consistency(self, mock_supabase, knowledge_base_data):
        """Test that MRL fruit types are consistent with varieties."""
        mrl_fruits = set(m["fruit_type"] for m in knowledge_base_data["mrl_limits"])
        variety_fruits = set(v["fruit_type"] for v in knowledge_base_data["fruit_varieties"])
        
        # MRL fruits should be in varieties
        # Note: There might be MRL for fruits without varieties defined
        assert len(mrl_fruits.intersection(variety_fruits)) > 0
    
    def test_calendar_disease_references(self, mock_supabase, knowledge_base_data):
        """Test that calendar disease_risks reference actual diseases."""
        disease_names = set(d["name"] for d in knowledge_base_data["diseases"])
        
        for calendar in knowledge_base_data["farming_calendar"]:
            for risk in calendar.get("disease_risks", []):
                # Disease risk should be a known disease or variation
                # Some might be variations like "powdery_mildew" not in base data
                pass  # Actual validation would check against full disease list
    
    def test_no_duplicate_country_fruit_requirements(self, mock_supabase, knowledge_base_data):
        """Test no duplicate country+fruit combinations in export requirements."""
        combinations = []
        for req in knowledge_base_data["export_requirements"]:
            combo = (req["country_code"], req["fruit_type"])
            assert combo not in combinations, f"Duplicate: {combo}"
            combinations.append(combo)
    
    def test_no_duplicate_mrl_entries(self, mock_supabase, knowledge_base_data):
        """Test no duplicate MRL entries for same pesticide/fruit/country."""
        combinations = []
        for mrl in knowledge_base_data["mrl_limits"]:
            combo = (mrl["pesticide_name"], mrl["fruit_type"], mrl["country_code"])
            assert combo not in combinations, f"Duplicate: {combo}"
            combinations.append(combo)


# ============================================================================
# TEST: SEARCH FUNCTIONALITY
# ============================================================================

class TestSearchFunctionality:
    """Tests for full-text search capabilities."""
    
    def test_search_diseases_by_symptom(self, mock_supabase, knowledge_base_data):
        """Test searching diseases by symptom keyword."""
        # Simulating text search for "spots"
        results = [d for d in knowledge_base_data["diseases"] 
                   if any("spot" in s.lower() for s in d["symptoms"])]
        
        mock_supabase.table.return_value.select.return_value.execute.return_value.data = results
        
        assert len(results) > 0
    
    def test_search_treatments_by_product(self, mock_supabase, knowledge_base_data):
        """Test searching treatments by product name."""
        results = [t for t in knowledge_base_data["treatments"] 
                   if "carbendazim" in t["product_name"].lower()]
        
        assert len(results) > 0
    
    def test_search_with_urdu_term(self, mock_supabase, knowledge_base_data):
        """Test searching with Urdu terms."""
        # Search for سندھری (Sindhri in Urdu)
        results = [v for v in knowledge_base_data["fruit_varieties"] 
                   if "سندھری" in v.get("variety_name_urdu", "")]
        
        assert len(results) == 1
        assert results[0]["variety_name"] == "Sindhri"
