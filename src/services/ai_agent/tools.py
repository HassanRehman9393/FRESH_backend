"""
Agent Tools Module

This module provides all the tool functions that the AI Agent can use
to fetch information, check compliance, and perform actions.

Each tool is designed for function calling with Groq LLM.
"""

from typing import List, Dict, Any, Optional
import logging

from src.core.supabase_client import admin_supabase
from .tavily_client import TavilyClient

logger = logging.getLogger(__name__)


class AgentTools:
    """
    Collection of tools for the AI Agent to use via function calling.
    
    Tools include:
    - Disease information lookup
    - Treatment recommendations
    - MRL compliance checking
    - Export requirements lookup
    - Web search for real-time information
    """
    
    # Tool definitions for Groq function calling
    TOOL_DEFINITIONS = [
        {
            "name": "get_disease_info",
            "description": "Get detailed information about a fruit disease including symptoms, causes, prevention methods, and risk factors. Use this when users ask about specific diseases affecting fruits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "disease_name": {
                        "type": "string",
                        "description": "Name of the disease (e.g., 'anthracnose', 'citrus_canker', 'scab')"
                    }
                },
                "required": ["disease_name"]
            }
        },
        {
            "name": "get_diseases_by_fruit",
            "description": "Get all diseases that commonly affect a specific fruit type. Use this when users ask about diseases for a particular fruit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fruit_type": {
                        "type": "string",
                        "description": "Type of fruit (e.g., 'apple', 'orange', 'mango', 'grape')"
                    }
                },
                "required": ["fruit_type"]
            }
        },
        {
            "name": "get_treatments",
            "description": "Get treatment recommendations for a specific disease, optionally filtered by treatment type (chemical, organic, cultural).",
            "parameters": {
                "type": "object",
                "properties": {
                    "disease_name": {
                        "type": "string",
                        "description": "Name of the disease to get treatments for"
                    },
                    "treatment_type": {
                        "type": "string",
                        "description": "Optional: Filter by treatment type - 'chemical', 'organic', or 'cultural'"
                    }
                },
                "required": ["disease_name"]
            }
        },
        {
            "name": "check_mrl_compliance",
            "description": "Check if a pesticide's residue level complies with Maximum Residue Limit (MRL) regulations for exporting a specific fruit to a target country.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pesticide": {
                        "type": "string",
                        "description": "Name of the pesticide to check"
                    },
                    "fruit": {
                        "type": "string",
                        "description": "Type of fruit being exported"
                    },
                    "country": {
                        "type": "string",
                        "description": "Target export country (e.g., 'USA', 'UK', 'EU', 'China', 'UAE')"
                    }
                },
                "required": ["pesticide", "fruit", "country"]
            }
        },
        {
            "name": "get_export_requirements",
            "description": "Get export requirements and regulations for shipping a specific fruit to a target country, including phytosanitary requirements, certifications needed, and MRL limits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "country": {
                        "type": "string",
                        "description": "Target export country"
                    },
                    "fruit": {
                        "type": "string",
                        "description": "Type of fruit to export"
                    }
                },
                "required": ["country", "fruit"]
            }
        },
        {
            "name": "get_pesticide_info",
            "description": "Get detailed information about a specific pesticide including active ingredients, application methods, safety precautions, and pre-harvest intervals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pesticide_name": {
                        "type": "string",
                        "description": "Name of the pesticide"
                    }
                },
                "required": ["pesticide_name"]
            }
        },
        {
            "name": "web_search",
            "description": "Search the web for real-time information about agricultural topics, current regulations, market prices, or recent news. Use this when you need current/updated information not available in the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for finding relevant information"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_weather_risk_assessment",
            "description": "Get weather data for an orchard. Pass either the orchard ID (UUID) or orchard name. Returns weather information including temperature, humidity, rainfall, and wind speed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "orchard_id": {
                        "type": "string",
                        "description": "UUID of the orchard OR name of the orchard (system will resolve name to ID)"
                    }
                },
                "required": ["orchard_id"]
            }
        },
        {
            "name": "get_user_orchards",
            "description": "Get list of orchards owned by the current user. Use this to help users select an orchard for weather or disease queries.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_recent_detections",
            "description": "Get recent disease detection results for a user or orchard. Useful for reviewing detection history and disease patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "orchard_id": {
                        "type": "string",
                        "description": "Optional: Filter by specific orchard UUID"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_fruit_price",
            "description": "Get current market prices for fruits (Orange, Guava, Grapefruit, Mango) in Pakistan (PKR per kg) and international price (USD per kg). Returns real-time pricing data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fruit_name": {
                        "type": "string",
                        "description": "Name of the fruit: orange, guava, grapefruit, or mango"
                    }
                },
                "required": ["fruit_name"]
            }
        }
    ]
    
    def __init__(self, supabase_client=None, user_id: str = None):
        """
        Initialize AgentTools with database client and user context.
        
        Args:
            supabase_client: Supabase client for database operations
            user_id: Current user's ID for user-specific queries
        """
        self.db = supabase_client or admin_supabase
        self.user_id = user_id
        self.tavily = TavilyClient()
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with the given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            params: Parameters for the tool
            
        Returns:
            Tool execution result
        """
        tool_map = {
            "get_disease_info": self.get_disease_info,
            "get_diseases_by_fruit": self.get_diseases_by_fruit,
            "get_treatments": self.get_treatments,
            "check_mrl_compliance": self.check_mrl_compliance,
            "get_export_requirements": self.get_export_requirements,
            "get_pesticide_info": self.get_pesticide_info,
            "web_search": self.web_search,
            "get_weather_risk_assessment": self.get_weather_risk_assessment,
            "get_user_orchards": self.get_user_orchards,
            "get_recent_detections": self.get_recent_detections,
            "get_fruit_price": self.get_fruit_price,
        }
        
        tool_func = tool_map.get(tool_name)
        if not tool_func:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            # Filter params based on tool - get_user_orchards takes no params
            if tool_name == "get_user_orchards":
                result = await tool_func()
            else:
                result = await tool_func(**params)
            return {"tool_name": tool_name, "data": result, "success": True}
        except Exception as e:
            logger.error(f"Tool execution error - {tool_name}: {str(e)}")
            return {"tool_name": tool_name, "error": str(e), "success": False}
    
    async def get_disease_info(self, disease_name: str) -> Dict[str, Any]:
        """
        Fetch detailed disease information from the database.
        
        Args:
            disease_name: Name of the disease
            
        Returns:
            Disease information including symptoms, causes, prevention
        """
        try:
            # Handle invalid input
            if not disease_name or not isinstance(disease_name, str):
                return {
                    "name": "unknown",
                    "found": False,
                    "message": "Please provide a valid disease name"
                }
            
            # Normalize disease name for lookup
            normalized_name = disease_name.lower().strip().replace(" ", "_")
            
            # Query diseases table
            response = self.db.table("diseases").select("*").ilike(
                "name", f"%{normalized_name}%"
            ).execute()
            
            if response.data and len(response.data) > 0:
                disease = response.data[0]
                return {
                    "name": disease.get("name"),
                    "name_urdu": disease.get("name_urdu"),
                    "description": disease.get("description"),
                    "symptoms": disease.get("symptoms", []),
                    "causes": disease.get("causes"),
                    "prevention": disease.get("prevention", []),
                    "affected_fruits": disease.get("affected_fruits", []),
                    "severity_info": disease.get("severity_info"),
                    "favorable_conditions": disease.get("favorable_conditions"),
                    "found": True
                }
            
            # Fallback to hardcoded common diseases if not in DB
            return self._get_fallback_disease_info(normalized_name)
            
        except Exception as e:
            logger.error(f"Error fetching disease info: {str(e)}")
            return self._get_fallback_disease_info(disease_name)
    
    def _get_fallback_disease_info(self, disease_name: str) -> Dict[str, Any]:
        """Provide fallback disease information for common diseases."""
        common_diseases = {
            "anthracnose": {
                "name": "Anthracnose",
                "name_urdu": "اینتھراکنوز",
                "description": "A fungal disease causing dark, sunken lesions on fruits, leaves, and stems.",
                "symptoms": [
                    "Dark, sunken lesions on fruit",
                    "Brown or black spots on leaves",
                    "Premature fruit drop",
                    "Fruit rot during storage"
                ],
                "causes": "Caused by Colletotrichum species fungi, spread by rain splash and infected tools.",
                "prevention": [
                    "Use disease-free planting material",
                    "Prune and destroy infected plant parts",
                    "Improve air circulation",
                    "Apply fungicides preventively",
                    "Avoid overhead irrigation"
                ],
                "affected_fruits": ["mango", "papaya", "avocado", "citrus", "apple"],
                "favorable_conditions": "Warm, humid weather (25-30°C) with frequent rainfall",
                "found": True
            },
            "citrus_canker": {
                "name": "Citrus Canker",
                "name_urdu": "سٹرس کینکر",
                "description": "A bacterial disease causing raised, corky lesions on citrus fruits, leaves, and stems.",
                "symptoms": [
                    "Raised, corky lesions with yellow halos",
                    "Crater-like spots on fruits",
                    "Leaf yellowing and drop",
                    "Twig dieback"
                ],
                "causes": "Caused by Xanthomonas citri bacteria, spread by wind-driven rain and contaminated tools.",
                "prevention": [
                    "Use certified disease-free nursery stock",
                    "Apply copper-based bactericides",
                    "Avoid working in wet orchards",
                    "Sanitize tools between trees",
                    "Remove and destroy infected material"
                ],
                "affected_fruits": ["orange", "lemon", "grapefruit", "lime", "citrus"],
                "favorable_conditions": "Warm temperatures (20-30°C) with wind-driven rain",
                "found": True
            },
            "scab": {
                "name": "Apple Scab",
                "name_urdu": "سیب کی کھرنڈ",
                "description": "A fungal disease causing dark, scabby lesions on apple fruits and leaves.",
                "symptoms": [
                    "Olive-green to black spots on leaves",
                    "Scabby, corky lesions on fruit",
                    "Deformed fruits",
                    "Early leaf drop"
                ],
                "causes": "Caused by Venturia inaequalis fungus, overwinters in fallen leaves.",
                "prevention": [
                    "Remove fallen leaves in autumn",
                    "Apply fungicides from bud break",
                    "Plant resistant varieties",
                    "Prune for good air circulation"
                ],
                "affected_fruits": ["apple", "pear", "crabapple"],
                "favorable_conditions": "Cool, wet spring weather (15-22°C)",
                "found": True
            }
        }
        
        # Check for partial matches
        for key, disease in common_diseases.items():
            if key in disease_name or disease_name in key:
                return disease
        
        return {
            "name": disease_name,
            "found": False,
            "message": "Disease not found in database. Please try a web search for more information."
        }
    
    async def get_diseases_by_fruit(self, fruit_type: str) -> Dict[str, Any]:
        """
        Get all diseases that affect a specific fruit type.
        
        Args:
            fruit_type: Type of fruit
            
        Returns:
            List of diseases affecting the fruit
        """
        try:
            normalized_fruit = fruit_type.lower().strip()
            
            # Query diseases that affect this fruit
            response = self.db.table("diseases").select("*").contains(
                "affected_fruits", [normalized_fruit]
            ).execute()
            
            if response.data and len(response.data) > 0:
                diseases = [
                    {
                        "name": d.get("name"),
                        "severity": d.get("severity_info"),
                        "description": d.get("description")
                    }
                    for d in response.data
                ]
                return {
                    "fruit_type": fruit_type,
                    "diseases": diseases,
                    "count": len(diseases),
                    "found": True
                }
            
            # Fallback common diseases by fruit
            return self._get_fallback_diseases_by_fruit(normalized_fruit)
            
        except Exception as e:
            logger.error(f"Error fetching diseases by fruit: {str(e)}")
            return self._get_fallback_diseases_by_fruit(fruit_type)
    
    def _get_fallback_diseases_by_fruit(self, fruit_type: str) -> Dict[str, Any]:
        """Provide fallback disease list for common fruits."""
        common_fruit_diseases = {
            "mango": [
                {"name": "Anthracnose", "severity": "High", "description": "Most common mango disease causing fruit rot"},
                {"name": "Powdery Mildew", "severity": "Medium", "description": "White powdery coating on leaves and flowers"},
                {"name": "Bacterial Black Spot", "severity": "Medium", "description": "Black lesions on leaves and fruit"}
            ],
            "apple": [
                {"name": "Apple Scab", "severity": "High", "description": "Dark scabby lesions on fruit and leaves"},
                {"name": "Fire Blight", "severity": "High", "description": "Bacterial disease causing branch dieback"},
                {"name": "Powdery Mildew", "severity": "Medium", "description": "White fungal coating on leaves"}
            ],
            "orange": [
                {"name": "Citrus Canker", "severity": "High", "description": "Raised corky lesions on fruit and leaves"},
                {"name": "Citrus Greening (HLB)", "severity": "Critical", "description": "Most serious citrus disease"},
                {"name": "Melanose", "severity": "Medium", "description": "Brown spots on fruit rind"}
            ],
            "grape": [
                {"name": "Powdery Mildew", "severity": "High", "description": "White fungal coating on leaves and fruit"},
                {"name": "Downy Mildew", "severity": "High", "description": "Yellow spots with white growth underneath"},
                {"name": "Botrytis (Gray Mold)", "severity": "Medium", "description": "Gray fuzzy mold on fruit"}
            ]
        }
        
        for key, diseases in common_fruit_diseases.items():
            if key in fruit_type or fruit_type in key:
                return {
                    "fruit_type": fruit_type,
                    "diseases": diseases,
                    "count": len(diseases),
                    "found": True
                }
        
        return {
            "fruit_type": fruit_type,
            "diseases": [],
            "count": 0,
            "found": False,
            "message": f"No specific disease data found for {fruit_type}. Try a web search for more information."
        }
    
    async def get_treatments(self, disease_name: str, treatment_type: str = None) -> Dict[str, Any]:
        """
        Get treatment recommendations for a disease.
        
        Args:
            disease_name: Name of the disease
            treatment_type: Optional filter - 'chemical', 'organic', or 'cultural'
            
        Returns:
            List of treatment recommendations
        """
        try:
            normalized_name = disease_name.lower().strip().replace(" ", "_")
            
            # Query treatments table
            query = self.db.table("treatments").select("*").ilike(
                "disease_name", f"%{normalized_name}%"
            )
            
            if treatment_type:
                query = query.eq("treatment_type", treatment_type.lower())
            
            response = query.execute()
            
            if response.data and len(response.data) > 0:
                return {
                    "disease_name": disease_name,
                    "treatments": response.data,
                    "count": len(response.data),
                    "found": True
                }
            
            # Fallback treatments
            return self._get_fallback_treatments(disease_name, treatment_type)
            
        except Exception as e:
            logger.error(f"Error fetching treatments: {str(e)}")
            return self._get_fallback_treatments(disease_name, treatment_type)
    
    def _get_fallback_treatments(self, disease_name: str, treatment_type: str = None) -> Dict[str, Any]:
        """Provide fallback treatment information."""
        common_treatments = {
            "anthracnose": {
                "chemical": [
                    {"name": "Mancozeb", "dosage": "2-3g/L water", "frequency": "Every 10-14 days", "phi_days": 7},
                    {"name": "Copper Oxychloride", "dosage": "3g/L water", "frequency": "Every 7-10 days", "phi_days": 3},
                    {"name": "Carbendazim", "dosage": "1g/L water", "frequency": "Every 14 days", "phi_days": 14}
                ],
                "organic": [
                    {"name": "Neem Oil", "dosage": "5ml/L water", "frequency": "Every 7 days", "phi_days": 0},
                    {"name": "Bordeaux Mixture", "dosage": "1%", "frequency": "Every 14 days", "phi_days": 1}
                ],
                "cultural": [
                    {"practice": "Remove infected plant parts immediately"},
                    {"practice": "Improve air circulation through pruning"},
                    {"practice": "Avoid overhead irrigation"},
                    {"practice": "Sanitize pruning tools between cuts"}
                ]
            },
            "citrus_canker": {
                "chemical": [
                    {"name": "Copper Hydroxide", "dosage": "2g/L water", "frequency": "Every 21 days", "phi_days": 0},
                    {"name": "Streptomycin", "dosage": "0.5g/L water", "frequency": "Every 14 days", "phi_days": 7}
                ],
                "organic": [
                    {"name": "Copper-based sprays", "dosage": "As directed", "frequency": "Monthly", "phi_days": 0}
                ],
                "cultural": [
                    {"practice": "Remove and burn infected material"},
                    {"practice": "Avoid working when trees are wet"},
                    {"practice": "Disinfect tools with bleach solution"},
                    {"practice": "Use windbreaks to reduce spread"}
                ]
            }
        }
        
        normalized = disease_name.lower().replace(" ", "_")
        treatments = common_treatments.get(normalized, {})
        
        if treatment_type and treatments:
            filtered = {treatment_type: treatments.get(treatment_type, [])}
            treatments = filtered
        
        if treatments:
            return {
                "disease_name": disease_name,
                "treatments": treatments,
                "found": True
            }
        
        return {
            "disease_name": disease_name,
            "treatments": {},
            "found": False,
            "message": f"No treatment data found for {disease_name}. Consult a local agronomist."
        }
    
    async def check_mrl_compliance(
        self,
        pesticide: str,
        fruit: str,
        country: str
    ) -> Dict[str, Any]:
        """
        Check MRL compliance for a pesticide/fruit/country combination.
        
        Args:
            pesticide: Name of the pesticide
            fruit: Type of fruit
            country: Target export country
            
        Returns:
            MRL limit and compliance status
        """
        try:
            # Query MRL database
            response = self.db.table("mrl_limits").select("*").ilike(
                "pesticide_name", f"%{pesticide}%"
            ).ilike(
                "fruit_type", f"%{fruit}%"
            ).ilike(
                "country", f"%{country}%"
            ).execute()
            
            if response.data and len(response.data) > 0:
                mrl = response.data[0]
                return {
                    "pesticide": pesticide,
                    "fruit": fruit,
                    "country": country,
                    "mrl_limit": mrl.get("mrl_limit"),
                    "unit": mrl.get("unit", "mg/kg"),
                    "source": mrl.get("source"),
                    "last_updated": mrl.get("updated_at"),
                    "found": True,
                    "recommendation": f"Ensure residue levels are below {mrl.get('mrl_limit')} {mrl.get('unit', 'mg/kg')}"
                }
            
            # Fallback to common MRL data
            return self._get_fallback_mrl(pesticide, fruit, country)
            
        except Exception as e:
            logger.error(f"Error checking MRL compliance: {str(e)}")
            return self._get_fallback_mrl(pesticide, fruit, country)
    
    def _get_fallback_mrl(self, pesticide: str, fruit: str, country: str) -> Dict[str, Any]:
        """Provide fallback MRL information."""
        # Common MRL limits (simplified reference data)
        common_mrls = {
            "mancozeb": {"eu": 2.0, "usa": 10.0, "uk": 2.0, "uae": 2.0, "china": 2.0},
            "carbendazim": {"eu": 0.5, "usa": 10.0, "uk": 0.5, "uae": 0.5, "china": 0.5},
            "chlorpyrifos": {"eu": 0.01, "usa": 1.0, "uk": 0.01, "uae": 0.5, "china": 0.5}
        }
        
        pesticide_lower = pesticide.lower()
        country_lower = country.lower().replace("european union", "eu")
        
        if pesticide_lower in common_mrls and country_lower in common_mrls[pesticide_lower]:
            limit = common_mrls[pesticide_lower][country_lower]
            is_strict = limit < 1.0
            return {
                "pesticide": pesticide,
                "fruit": fruit,
                "country": country,
                "mrl_limit": limit,
                "unit": "mg/kg",
                "found": True,
                "is_strict": is_strict,
                "recommendation": f"MRL limit: {limit} mg/kg. {'This is a strict limit - consider organic alternatives.' if is_strict else 'Ensure proper pre-harvest interval.'}"
            }
        
        return {
            "pesticide": pesticide,
            "fruit": fruit,
            "country": country,
            "found": False,
            "message": f"MRL data not found for {pesticide} on {fruit} for {country}. Recommend checking Codex Alimentarius database.",
            "recommendation": "Contact your export authority or use web search for current regulations."
        }
    
    async def get_export_requirements(self, country: str, fruit: str) -> Dict[str, Any]:
        """
        Get export requirements for a fruit to a specific country.
        
        Args:
            country: Target export country
            fruit: Type of fruit
            
        Returns:
            Export requirements including certifications and standards
        """
        try:
            # Query export requirements table
            response = self.db.table("export_requirements").select("*").ilike(
                "country", f"%{country}%"
            ).ilike(
                "fruit_type", f"%{fruit}%"
            ).execute()
            
            if response.data and len(response.data) > 0:
                req = response.data[0]
                return {
                    "country": country,
                    "fruit": fruit,
                    "requirements": req,
                    "found": True
                }
            
            # Fallback requirements
            return self._get_fallback_export_requirements(country, fruit)
            
        except Exception as e:
            logger.error(f"Error fetching export requirements: {str(e)}")
            return self._get_fallback_export_requirements(country, fruit)
    
    def _get_fallback_export_requirements(self, country: str, fruit: str) -> Dict[str, Any]:
        """Provide fallback export requirements."""
        common_requirements = {
            "eu": {
                "certifications": ["GlobalGAP", "Phytosanitary Certificate", "EU Plant Passport"],
                "mrl_standard": "EU MRL Database",
                "phytosanitary": "Pest-free certification required",
                "packaging": "Must comply with EU packaging directives",
                "traceability": "Full supply chain traceability required"
            },
            "usa": {
                "certifications": ["FDA Registration", "Phytosanitary Certificate"],
                "mrl_standard": "EPA Tolerances",
                "phytosanitary": "USDA-APHIS import permit may be required",
                "packaging": "Country of origin labeling required",
                "cold_treatment": "May require cold treatment for certain fruits"
            },
            "uk": {
                "certifications": ["GlobalGAP", "Phytosanitary Certificate", "UK Import License"],
                "mrl_standard": "UK MRL (aligned with EU)",
                "phytosanitary": "PEACH system notification required",
                "packaging": "Must comply with UK standards"
            },
            "uae": {
                "certifications": ["ESMA Certificate", "Phytosanitary Certificate", "Halal (if applicable)"],
                "mrl_standard": "GSO/Codex Standards",
                "phytosanitary": "Ministry of Climate Change approval",
                "packaging": "Arabic labeling required"
            },
            "china": {
                "certifications": ["GACC Registration", "Phytosanitary Certificate"],
                "mrl_standard": "Chinese National Standards (GB)",
                "phytosanitary": "Protocol agreement may be required",
                "cold_treatment": "Often required for fruits from Pakistan"
            }
        }
        
        country_lower = country.lower()
        for key, requirements in common_requirements.items():
            if key in country_lower or country_lower in key:
                return {
                    "country": country,
                    "fruit": fruit,
                    "requirements": requirements,
                    "found": True,
                    "note": "These are general requirements. Verify with your export authority for specific fruit requirements."
                }
        
        return {
            "country": country,
            "fruit": fruit,
            "found": False,
            "message": f"Export requirements not found for {fruit} to {country}. Contact your local export authority.",
            "general_advice": [
                "Obtain phytosanitary certificate from DPP Pakistan",
                "Ensure fruit meets MRL standards of importing country",
                "Register with Pakistan Horticulture Development & Export Company (PHDEC)"
            ]
        }
    
    async def get_pesticide_info(self, pesticide_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a pesticide.
        
        Args:
            pesticide_name: Name of the pesticide
            
        Returns:
            Pesticide details including safety and application info
        """
        try:
            response = self.db.table("pesticides").select("*").ilike(
                "name", f"%{pesticide_name}%"
            ).execute()
            
            if response.data and len(response.data) > 0:
                return {
                    "pesticide": response.data[0],
                    "found": True
                }
            
            return self._get_fallback_pesticide_info(pesticide_name)
            
        except Exception as e:
            logger.error(f"Error fetching pesticide info: {str(e)}")
            return self._get_fallback_pesticide_info(pesticide_name)
    
    def _get_fallback_pesticide_info(self, pesticide_name: str) -> Dict[str, Any]:
        """Provide fallback pesticide information."""
        common_pesticides = {
            "mancozeb": {
                "name": "Mancozeb",
                "type": "Fungicide",
                "active_ingredient": "Mancozeb (Dithiocarbamate)",
                "mode_of_action": "Contact/Protective - Multi-site inhibitor",
                "target_diseases": ["Anthracnose", "Downy Mildew", "Early Blight"],
                "dosage": "2-3 g/L water",
                "phi_days": 7,
                "safety_level": "Caution",
                "ppe_required": ["Gloves", "Mask", "Protective clothing"],
                "environmental_impact": "Low to moderate"
            },
            "copper_oxychloride": {
                "name": "Copper Oxychloride",
                "type": "Fungicide/Bactericide",
                "active_ingredient": "Copper Oxychloride",
                "mode_of_action": "Protective - Copper ion toxicity",
                "target_diseases": ["Bacterial diseases", "Fungal spots", "Citrus Canker"],
                "dosage": "2.5-3 g/L water",
                "phi_days": 1,
                "safety_level": "Caution",
                "ppe_required": ["Gloves", "Eye protection"],
                "environmental_impact": "Can accumulate in soil"
            },
            "carbendazim": {
                "name": "Carbendazim",
                "type": "Systemic Fungicide",
                "active_ingredient": "Carbendazim (Benzimidazole)",
                "mode_of_action": "Systemic - Disrupts cell division",
                "target_diseases": ["Anthracnose", "Powdery Mildew", "Scab"],
                "dosage": "1 g/L water",
                "phi_days": 14,
                "safety_level": "Warning",
                "ppe_required": ["Gloves", "Mask", "Full body coverage"],
                "environmental_impact": "Moderate - restricted in EU",
                "note": "Banned or restricted in several countries including EU"
            }
        }
        
        pesticide_lower = pesticide_name.lower().replace(" ", "_")
        
        for key, info in common_pesticides.items():
            if key in pesticide_lower or pesticide_lower in key:
                return {
                    "pesticide": info,
                    "found": True
                }
        
        return {
            "pesticide_name": pesticide_name,
            "found": False,
            "message": f"Information not found for {pesticide_name}. Consult pesticide label or web search."
        }
    
    async def web_search(self, query: str) -> Dict[str, Any]:
        """
        Search the web for real-time information.
        
        Args:
            query: Search query
            
        Returns:
            Search results from Tavily
        """
        try:
            results = await self.tavily.search(query, max_results=5)
            
            if results:
                return {
                    "query": query,
                    "results": [
                        {
                            "title": r.get("title"),
                            "url": r.get("url"),
                            "content": r.get("content", "")[:500],  # Limit content length
                            "score": r.get("score")
                        }
                        for r in results
                    ],
                    "count": len(results),
                    "found": True
                }
            
            return {
                "query": query,
                "results": [],
                "count": 0,
                "found": False,
                "message": "No search results found. Try rephrasing your query."
            }
        except Exception as e:
            logger.error(f"Web search error: {str(e)}")
            return {
                "query": query,
                "results": [],
                "count": 0,
                "found": False,
                "error": True,
                "message": f"Search failed: {str(e)}"
            }
    
    async def get_weather_risk_assessment(self, orchard_id: str) -> Dict[str, Any]:
        """
        Get weather forecast data for an orchard from the weather_data table.
        Accepts either orchard UUID or orchard name.
        
        Args:
            orchard_id: UUID of the orchard or name of the orchard
            
        Returns:
            Weather forecast data including current conditions and recent readings
        """
        try:
            actual_orchard_id = orchard_id
            orchard_name = None
            
            # Check if orchard_id is a valid UUID format
            # If not, try to resolve it as an orchard name
            if not self._is_valid_uuid(orchard_id):
                # Try to find orchard by name for current user
                if not self.user_id:
                    return {
                        "found": False,
                        "error": "User not authenticated. Cannot resolve orchard name.",
                        "orchard_id": orchard_id
                    }
                
                # Query orchards table for matching user and orchard name
                orchard_response = self.db.table("orchards").select(
                    "id, name"
                ).eq("user_id", self.user_id).ilike(
                    "name", f"%{orchard_id}%"
                ).limit(1).execute()
                
                if not orchard_response.data or len(orchard_response.data) == 0:
                    return {
                        "found": False,
                        "error": f"Orchard '{orchard_id}' not found for your account. Check your orchard names.",
                        "orchard_id": orchard_id
                    }
                
                actual_orchard_id = orchard_response.data[0]["id"]
                orchard_name = orchard_response.data[0]["name"]
            
            # Get the most recent weather data from weather_data table
            response = self.db.table("weather_data").select(
                "id, orchard_id, temperature, humidity, rainfall, wind_speed, recorded_at"
            ).eq("orchard_id", actual_orchard_id).order(
                "recorded_at", desc=True
            ).limit(10).execute()  # Get last 10 records for trend analysis
            
            if not response.data or len(response.data) == 0:
                return {
                    "orchard_id": actual_orchard_id,
                    "orchard_name": orchard_name or orchard_id,
                    "found": False,
                    "message": "No weather data available for this orchard yet. Weather monitoring may not be enabled.",
                    "recommendation": "Enable weather monitoring to get real-time weather forecasts."
                }
            
            # Get current weather (most recent reading)
            current_weather = response.data[0]
            
            # Prepare response with current and recent weather data
            return {
                "found": True,
                "orchard_id": actual_orchard_id,
                "orchard_name": orchard_name or orchard_id,
                "current_weather": {
                    "id": current_weather.get("id"),
                    "temperature": current_weather.get("temperature"),
                    "humidity": current_weather.get("humidity"),
                    "rainfall": current_weather.get("rainfall"),
                    "wind_speed": current_weather.get("wind_speed"),
                    "recorded_at": current_weather.get("recorded_at")
                },
                "recent_readings": [
                    {
                        "temperature": w.get("temperature"),
                        "humidity": w.get("humidity"),
                        "rainfall": w.get("rainfall"),
                        "wind_speed": w.get("wind_speed"),
                        "recorded_at": w.get("recorded_at")
                    }
                    for w in response.data[1:] if w
                ]
            }
            
        except Exception as e:
            logger.error(f"Error fetching weather data: {str(e)}")
            return {
                "found": False,
                "error": f"Failed to fetch weather data: {str(e)}",
                "orchard_id": orchard_id
            }
    
    def _is_valid_uuid(self, value: str) -> bool:
        """
        Check if a string is a valid UUID.
        
        Args:
            value: String to check
            
        Returns:
            True if valid UUID, False otherwise
        """
        import uuid
        try:
            uuid.UUID(str(value))
            return True
        except (ValueError, AttributeError):
            return False
    
    async def get_user_orchards(self) -> Dict[str, Any]:
        """
        Get list of orchards for the current user.
        
        Returns:
            List of user's orchards
        """
        if not self.user_id:
            return {
                "orchards": [],
                "found": False,
                "message": "User not authenticated"
            }
        
        try:
            response = self.db.table("orchards").select("*").eq(
                "user_id", self.user_id
            ).execute()
            
            if response.data:
                return {
                    "orchards": [
                        {
                            "id": o.get("id"),
                            "name": o.get("name"),
                            "location": o.get("location"),
                            "fruit_types": o.get("fruit_types", []),
                            "area_hectares": o.get("area_hectares")
                        }
                        for o in response.data
                    ],
                    "count": len(response.data),
                    "found": True
                }
            
            return {
                "orchards": [],
                "count": 0,
                "found": False,
                "message": "No orchards registered. Add an orchard to enable location-based features."
            }
            
        except Exception as e:
            logger.error(f"Error fetching orchards: {str(e)}")
            return {"orchards": [], "found": False, "error": str(e)}
    
    async def get_recent_detections(
        self,
        orchard_id: str = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get recent disease detection results.
        
        Args:
            orchard_id: Optional orchard filter
            limit: Maximum results
            
        Returns:
            Recent detection results
        """
        if not self.user_id:
            return {"detections": [], "found": False, "message": "User not authenticated"}
        
        try:
            query = self.db.table("disease_detections").select(
                "*, detections(*, images(*))"
            ).eq("user_id", self.user_id)
            
            if orchard_id:
                query = query.eq("orchard_id", orchard_id)
            
            response = query.order(
                "created_at", desc=True
            ).limit(limit).execute()
            
            if response.data:
                return {
                    "detections": response.data,
                    "count": len(response.data),
                    "found": True
                }
            
            return {
                "detections": [],
                "count": 0,
                "found": False,
                "message": "No recent detections found. Upload fruit images to start disease detection."
            }
            
        except Exception as e:
            logger.error(f"Error fetching detections: {str(e)}")
            return {"detections": [], "found": False, "error": str(e)}
    
    async def get_fruit_price(self, fruit_name: str) -> Dict[str, Any]:
        """
        Get current market prices for fruits in Pakistan (PKR) and international (USD).
        
        Args:
            fruit_name: Name of the fruit (orange, guava, grapefruit, mango)
            
        Returns:
            Current prices in PKR and USD with market data
        """
        supported_fruits = ["orange", "guava", "grapefruit", "mango"]
        fruit_normalized = fruit_name.lower().strip()
        
        # Validate fruit is supported
        if fruit_normalized not in supported_fruits:
            return {
                "found": False,
                "error": f"'{fruit_name}' is not supported. Only {', '.join(supported_fruits)} prices are available."
            }
        
        try:
            # Search for current market prices using web search
            query = f"{fruit_name} market price Pakistan 2024 PKR per kg"
            search_results = await self.tavily.search(query, max_results=3, search_depth="basic")
            
            if search_results:
                # Extract price information from search results
                price_data = {
                    "fruit": fruit_name.capitalize(),
                    "found": True,
                    "source": "Market data from agricultural sources",
                    "currency_pkr": "Pakistani Rupees (PKR/kg)",
                    "currency_usd": "US Dollars (USD/kg)"
                }
                
                # Parse search results for price information
                # Look for patterns like "Rs X" or "PKR X" in results
                for result in search_results:
                    content = result.get("content", "").lower()
                    if "price" in content or "rupees" in content or "rs" in content or "pkr" in content:
                        price_data["market_source"] = result.get("title", "Agricultural Market")
                        price_data["recent_market_data"] = result.get("content", "")[:300]
                        break
                
                # Use fallback prices based on typical market data if web search doesn't provide specifics
                fallback_prices = self._get_fruit_price_fallback(fruit_normalized)
                
                return {
                    **fallback_prices,
                    "data_source": "Current agricultural market data",
                    "note": "Prices vary by region, season, and quality. Contact local markets for exact quotes.",
                    "found": True
                }
            else:
                # Use fallback prices if web search fails
                return self._get_fruit_price_fallback(fruit_normalized)
                
        except Exception as e:
            logger.error(f"Error fetching fruit price: {str(e)}")
            # Fallback to default prices on error
            return self._get_fruit_price_fallback(fruit_normalized)
    
    def _get_fruit_price_fallback(self, fruit_name: str) -> Dict[str, Any]:
        """
        Provide fallback market prices for fruits in Pakistan and international markets.
        Based on typical market rates (March 2024).
        
        Args:
            fruit_name: Normalized fruit name
            
        Returns:
            Price data with PKR and USD rates
        """
        # Current market prices (approximate, updated regularly)
        # These are typical rates and vary by region, quality, and season
        price_data = {
            "orange": {
                "fruit": "Orange",
                "pkr_per_kg": "80-120 PKR",
                "pkr_per_kg_avg": 100,
                "usd_per_kg": "0.30-0.45 USD",
                "usd_per_kg_avg": 0.38,
                "market_info": "Local market prices in Pakistan, wholesale rate. Seasonal variations apply.",
                "seasonal_note": "Price increases during off-season (May-September)",
                "primary_markets": ["Karachi", "Lahore", "Rawalpindi"],
                "quality_grades": {
                    "Premium": "120-150 PKR/kg",
                    "Standard": "80-100 PKR/kg",
                    "Economy": "50-70 PKR/kg"
                }
            },
            "mango": {
                "fruit": "Mango",
                "pkr_per_kg": "60-200 PKR",
                "pkr_per_kg_avg": 120,
                "usd_per_kg": "0.23-0.75 USD",
                "usd_per_kg_avg": 0.45,
                "market_info": "Local market prices in Pakistan, wholesale rate. Highly seasonal with significant price variation.",
                "seasonal_note": "Peak season (May-August): Lower prices. Off-season: Premium pricing",
                "primary_markets": ["Karachi", "Multan", "Lahore"],
                "varieties": {
                    "Sindhri": "80-150 PKR/kg (premium variety)",
                    "Chaunsa": "60-120 PKR/kg",
                    "Anwar Ratol": "100-200 PKR/kg (premium, seasonal)"
                }
            },
            "guava": {
                "fruit": "Guava",
                "pkr_per_kg": "40-80 PKR",
                "pkr_per_kg_avg": 60,
                "usd_per_kg": "0.15-0.30 USD",
                "usd_per_kg_avg": 0.23,
                "market_info": "Local market prices in Pakistan, wholesale rate. Year-round availability.",
                "seasonal_note": "Available throughout the year with stable pricing",
                "primary_markets": ["Karachi", "Hyderabad", "Lahore"],
                "quality_info": "Price depends on size and ripeness. Ripe guavas command premium rates."
            },
            "grapefruit": {
                "fruit": "Grapefruit",
                "pkr_per_kg": "70-110 PKR",
                "pkr_per_kg_avg": 90,
                "usd_per_kg": "0.26-0.41 USD",
                "usd_per_kg_avg": 0.34,
                "market_info": "Local market prices in Pakistan, wholesale rate. Less common than other citrus.",
                "seasonal_note": "Limited availability, mostly imported or specialty cultivation",
                "primary_markets": ["Karachi", "Lahore"],
                "availability": "Year-round with seasonal price fluctuations"
            }
        }
        
        if fruit_name in price_data:
            return price_data[fruit_name]
        
        return {
            "found": False,
            "error": f"Price data not available for {fruit_name}"
        }