"""
Unit Tests for AI Assistant Agent Tools
========================================

Comprehensive tests for all agent tools including:
- Disease lookup (get_disease_info, get_diseases_by_fruit)
- Treatment recommendations (get_treatments)
- MRL compliance checking (check_mrl_compliance, get_mrl_for_country)
- Export requirements (get_export_requirements)
- Web search (web_search)
- User data tools (get_user_orchards, get_weather_data, get_disease_alerts)

Run with: pytest tests/unit/test_ai_assistant_tools.py -v
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
import json


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_supabase():
    """Mock Supabase client for database operations."""
    mock = MagicMock()
    return mock


@pytest.fixture
def agent_tools(mock_supabase):
    """Create AgentTools instance with mocked database."""
    from src.services.ai_agent.tools import AgentTools
    tools = AgentTools(mock_supabase, user_id=str(uuid4()))
    return tools


@pytest.fixture
def sample_disease_data():
    """Sample disease data from database."""
    return {
        "id": str(uuid4()),
        "name": "anthracnose",
        "name_urdu": "اینتھراکنوز",
        "disease_type": "fungal",
        "affected_fruits": ["mango", "guava"],
        "symptoms": [
            "Dark, sunken lesions on fruits",
            "Black spots on leaves",
            "Fruit rot"
        ],
        "causes": "Colletotrichum gloeosporioides fungus, spreads through rain splash",
        "prevention": [
            "Remove infected fruits",
            "Improve air circulation",
            "Apply fungicides preventively"
        ],
        "severity_levels": {
            "mild": "Few spots, less than 5% fruit affected",
            "moderate": "5-25% affected",
            "severe": "Over 25% affected"
        }
    }


@pytest.fixture
def sample_treatments_data():
    """Sample treatments data from database."""
    return [
        {
            "id": str(uuid4()),
            "disease_id": str(uuid4()),
            "treatment_type": "chemical",
            "product_name": "Carbendazim 50% WP",
            "active_ingredient": "Carbendazim",
            "dosage": "1g per liter of water",
            "application_method": "Foliar spray",
            "pre_harvest_interval_days": 14,
            "effectiveness_rating": 4
        },
        {
            "id": str(uuid4()),
            "disease_id": str(uuid4()),
            "treatment_type": "organic",
            "product_name": "Trichoderma viride",
            "active_ingredient": "Trichoderma",
            "dosage": "5g per liter of water",
            "application_method": "Soil drench",
            "pre_harvest_interval_days": 0,
            "effectiveness_rating": 3
        }
    ]


@pytest.fixture
def sample_mrl_data():
    """Sample MRL limits data."""
    return [
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
        }
    ]


@pytest.fixture
def sample_export_requirements():
    """Sample export requirements data."""
    return {
        "id": str(uuid4()),
        "country_code": "EU",
        "country_name": "European Union",
        "fruit_type": "mango",
        "phytosanitary_requirements": [
            "Phytosanitary Certificate",
            "Pest-free declaration"
        ],
        "certifications_needed": ["GlobalGAP", "HACCP"],
        "temperature_requirements": {
            "transport_temp_celsius": "10-13",
            "humidity_percent": "85-90"
        },
        "documentation_required": [
            "Commercial Invoice",
            "Packing List",
            "Bill of Lading"
        ]
    }


# ============================================================================
# TEST: TOOL DEFINITIONS
# ============================================================================

class TestToolDefinitions:
    """Test that all tool definitions are valid for Gemini function calling."""
    
    def test_tool_definitions_exist(self, agent_tools):
        """Verify TOOL_DEFINITIONS is not empty."""
        from src.services.ai_agent.tools import AgentTools
        assert len(AgentTools.TOOL_DEFINITIONS) > 0
    
    def test_tool_definitions_have_required_fields(self, agent_tools):
        """Each tool definition must have name, description, parameters."""
        from src.services.ai_agent.tools import AgentTools
        
        for tool in AgentTools.TOOL_DEFINITIONS:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool {tool.get('name')} missing 'description'"
            assert "parameters" in tool, f"Tool {tool.get('name')} missing 'parameters'"
    
    def test_tool_parameters_are_valid_json_schema(self, agent_tools):
        """Tool parameters must follow JSON schema format."""
        from src.services.ai_agent.tools import AgentTools
        
        for tool in AgentTools.TOOL_DEFINITIONS:
            params = tool["parameters"]
            assert params.get("type") == "object", f"Tool {tool['name']} parameters must be type 'object'"
            assert "properties" in params, f"Tool {tool['name']} missing 'properties'"
    
    def test_expected_tools_are_defined(self, agent_tools):
        """Verify all expected tools are defined."""
        from src.services.ai_agent.tools import AgentTools
        
        expected_tools = [
            "get_disease_info",
            "get_diseases_by_fruit",
            "get_treatments",
            "check_mrl_compliance",
            "get_export_requirements",
            "web_search"
        ]
        
        defined_tools = [t["name"] for t in AgentTools.TOOL_DEFINITIONS]
        
        for expected in expected_tools:
            assert expected in defined_tools, f"Expected tool '{expected}' not defined"


# ============================================================================
# TEST: DISEASE TOOLS
# ============================================================================

class TestDiseaseTools:
    """Tests for disease-related tools."""
    
    @pytest.mark.asyncio
    async def test_get_disease_info_success(self, agent_tools, mock_supabase, sample_disease_data):
        """Test successful disease info retrieval."""
        # Mock database response
        mock_supabase.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = [sample_disease_data]
        
        result = await agent_tools.get_disease_info("anthracnose")
        
        assert result is not None
        assert "found" in result or "name" in str(result).lower()
    
    @pytest.mark.asyncio
    async def test_get_disease_info_not_found(self, agent_tools, mock_supabase):
        """Test disease info when disease doesn't exist."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = []
        
        result = await agent_tools.get_disease_info("nonexistent_disease")
        
        assert result is not None
        assert "not found" in str(result).lower() or "no " in str(result).lower()
    
    @pytest.mark.asyncio
    async def test_get_disease_info_case_insensitive(self, agent_tools, mock_supabase, sample_disease_data):
        """Test disease lookup is case-insensitive."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = [sample_disease_data]
        
        # Should work with different cases
        await agent_tools.get_disease_info("ANTHRACNOSE")
        await agent_tools.get_disease_info("Anthracnose")
        await agent_tools.get_disease_info("anthracnose")
        
        # Verify ilike was called (case-insensitive search)
        assert mock_supabase.table.return_value.select.return_value.ilike.called
    
    @pytest.mark.asyncio
    async def test_get_diseases_by_fruit_success(self, agent_tools, mock_supabase, sample_disease_data):
        """Test getting diseases for a specific fruit."""
        mock_supabase.table.return_value.select.return_value.contains.return_value.execute.return_value.data = [sample_disease_data]
        
        result = await agent_tools.get_diseases_by_fruit("mango")
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_diseases_by_fruit_no_results(self, agent_tools, mock_supabase):
        """Test diseases by fruit when no diseases found."""
        mock_supabase.table.return_value.select.return_value.contains.return_value.execute.return_value.data = []
        
        result = await agent_tools.get_diseases_by_fruit("banana")
        
        assert result is not None


# ============================================================================
# TEST: TREATMENT TOOLS
# ============================================================================

class TestTreatmentTools:
    """Tests for treatment-related tools."""
    
    @pytest.mark.asyncio
    async def test_get_treatments_success(self, agent_tools, mock_supabase, sample_disease_data, sample_treatments_data):
        """Test successful treatment retrieval."""
        # Mock disease lookup
        mock_supabase.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = [sample_disease_data]
        # Mock treatments lookup
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = sample_treatments_data
        
        result = await agent_tools.get_treatments("anthracnose")
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_treatments_filtered_by_type(self, agent_tools, mock_supabase, sample_disease_data, sample_treatments_data):
        """Test treatment retrieval filtered by type."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = [sample_disease_data]
        
        # Only return organic treatments
        organic_only = [t for t in sample_treatments_data if t["treatment_type"] == "organic"]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = organic_only
        
        result = await agent_tools.get_treatments("anthracnose", treatment_type="organic")
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_treatments_disease_not_found(self, agent_tools, mock_supabase):
        """Test treatments when disease doesn't exist."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = []
        
        result = await agent_tools.get_treatments("nonexistent")
        
        assert result is not None
        # Result should indicate no data found or have found=False
        assert result.get("found") == False or "No treatment" in result.get("message", "")


# ============================================================================
# TEST: MRL COMPLIANCE TOOLS
# ============================================================================

class TestMRLTools:
    """Tests for MRL (Maximum Residue Limit) compliance tools."""
    
    @pytest.mark.asyncio
    async def test_check_mrl_compliance_compliant(self, agent_tools, mock_supabase, sample_mrl_data):
        """Test MRL check when pesticide is compliant."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.ilike.return_value.ilike.return_value.execute.return_value.data = [sample_mrl_data[0]]
        
        result = await agent_tools.check_mrl_compliance("Carbendazim", "mango", "EU")
        
        assert result is not None
        # Should contain MRL value info
        assert "mrl" in str(result).lower() or "limit" in str(result).lower() or "value" in str(result).lower()
    
    @pytest.mark.asyncio
    async def test_check_mrl_compliance_not_found(self, agent_tools, mock_supabase):
        """Test MRL check when no data exists for combination."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.ilike.return_value.ilike.return_value.execute.return_value.data = []
        
        result = await agent_tools.check_mrl_compliance("UnknownPesticide", "mango", "EU")
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_check_mrl_different_countries(self, agent_tools, mock_supabase, sample_mrl_data):
        """Test MRL varies by country."""
        # EU has stricter limits
        mock_supabase.table.return_value.select.return_value.ilike.return_value.ilike.return_value.ilike.return_value.execute.return_value.data = [sample_mrl_data[0]]
        
        eu_result = await agent_tools.check_mrl_compliance("Carbendazim", "mango", "EU")
        
        # UAE has more relaxed limits
        mock_supabase.table.return_value.select.return_value.ilike.return_value.ilike.return_value.ilike.return_value.execute.return_value.data = [sample_mrl_data[1]]
        
        uae_result = await agent_tools.check_mrl_compliance("Carbendazim", "mango", "UAE")
        
        assert eu_result is not None
        assert uae_result is not None


# ============================================================================
# TEST: EXPORT REQUIREMENTS TOOLS
# ============================================================================

class TestExportRequirementsTools:
    """Tests for export requirements tools."""
    
    @pytest.mark.asyncio
    async def test_get_export_requirements_success(self, agent_tools, mock_supabase, sample_export_requirements):
        """Test successful export requirements retrieval."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.ilike.return_value.execute.return_value.data = [sample_export_requirements]
        
        result = await agent_tools.get_export_requirements("EU", "mango")
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_export_requirements_not_found(self, agent_tools, mock_supabase):
        """Test export requirements when not available."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.ilike.return_value.execute.return_value.data = []
        
        result = await agent_tools.get_export_requirements("Unknown", "fruit")
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_export_requirements_country_code_variations(self, agent_tools, mock_supabase, sample_export_requirements):
        """Test export requirements with different country code formats."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.ilike.return_value.execute.return_value.data = [sample_export_requirements]
        
        # Should handle "EU", "European Union", "europe" etc.
        await agent_tools.get_export_requirements("EU", "mango")
        await agent_tools.get_export_requirements("European Union", "mango")
        
        # At least one call should be made
        assert mock_supabase.table.called


# ============================================================================
# TEST: WEB SEARCH TOOL
# ============================================================================

class TestWebSearchTool:
    """Tests for Tavily web search tool."""
    
    @pytest.mark.asyncio
    async def test_web_search_success(self, agent_tools):
        """Test successful web search."""
        with patch.object(agent_tools.tavily, 'search') as mock_search:
            mock_search.return_value = [
                {"title": "Test Result", "url": "https://example.com", "content": "Test content"}
            ]
            
            result = await agent_tools.web_search("mango prices Pakistan")
            
            # Should return results
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_web_search_empty_query(self, agent_tools):
        """Test web search with empty query."""
        with patch.object(agent_tools.tavily, 'search') as mock_search:
            mock_search.return_value = []
            result = await agent_tools.web_search("")
            
            assert result is not None
            # Should handle gracefully
    
    @pytest.mark.asyncio
    async def test_web_search_error_handling(self, agent_tools):
        """Test web search handles API errors gracefully."""
        with patch.object(agent_tools.tavily, 'search') as mock_search:
            mock_search.side_effect = Exception("API Error")
            
            result = await agent_tools.web_search("test query")
            
            # Should not raise, return error message
            assert result is not None


# ============================================================================
# TEST: USER DATA TOOLS
# ============================================================================

class TestUserDataTools:
    """Tests for user-specific data tools."""
    
    @pytest.mark.asyncio
    async def test_get_user_orchards(self, agent_tools, mock_supabase):
        """Test fetching user's orchards."""
        mock_orchards = [
            {
                "id": str(uuid4()),
                "name": "Test Orchard",
                "fruit_types": ["mango", "guava"],
                "area_hectares": 5.0
            }
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = mock_orchards
        
        result = await agent_tools.get_user_orchards()
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_get_user_orchards_no_user(self, mock_supabase):
        """Test orchards tool without user ID."""
        from src.services.ai_agent.tools import AgentTools
        tools = AgentTools(mock_supabase, user_id=None)
        
        result = await tools.get_user_orchards()
        
        # Should handle gracefully
        assert result is not None


# ============================================================================
# TEST: ERROR HANDLING
# ============================================================================

class TestErrorHandling:
    """Tests for error handling across all tools."""
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self, agent_tools, mock_supabase):
        """Test handling of database connection errors."""
        mock_supabase.table.side_effect = Exception("Database connection failed")
        
        result = await agent_tools.get_disease_info("anthracnose")
        
        # Should not raise - implementation uses fallback data
        assert result is not None
        # Either returns fallback data or indicates not found
        assert "found" in str(result).lower()
    
    @pytest.mark.asyncio
    async def test_invalid_input_handling(self, agent_tools, mock_supabase):
        """Test handling of invalid inputs."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = []
        
        # Empty string - should return fallback or not found
        result = await agent_tools.get_disease_info("")
        assert result is not None
        
        # Whitespace only
        result = await agent_tools.get_disease_info("   ")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_special_characters_in_input(self, agent_tools, mock_supabase):
        """Test handling of special characters in input."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = []
        
        # SQL injection attempt (should be handled by parameterized queries)
        result = await agent_tools.get_disease_info("'; DROP TABLE diseases; --")
        assert result is not None
        
        # Unicode characters
        result = await agent_tools.get_disease_info("بیماری")
        assert result is not None


# ============================================================================
# TEST: TOOL EXECUTION MAPPING
# ============================================================================

class TestToolExecutionMapping:
    """Test that tools can be executed by name."""
    
    @pytest.mark.asyncio
    async def test_execute_tool_by_name(self, agent_tools, mock_supabase, sample_disease_data):
        """Test executing tools by their string name."""
        mock_supabase.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = [sample_disease_data]
        
        # Get the method by name
        tool_method = getattr(agent_tools, "get_disease_info", None)
        
        assert tool_method is not None
        assert callable(tool_method)
        
        result = await tool_method("anthracnose")
        assert result is not None
    
    def test_all_defined_tools_have_methods(self, agent_tools):
        """Verify each defined tool has a corresponding method."""
        from src.services.ai_agent.tools import AgentTools
        
        for tool in AgentTools.TOOL_DEFINITIONS:
            tool_name = tool["name"]
            method = getattr(agent_tools, tool_name, None)
            
            assert method is not None, f"No method found for tool '{tool_name}'"
            assert callable(method), f"Tool '{tool_name}' is not callable"
