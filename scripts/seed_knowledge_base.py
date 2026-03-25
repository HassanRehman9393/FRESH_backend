#!/usr/bin/env python3
"""
Knowledge Base Seed Script
===========================
Seeds the AI Assistant knowledge base tables with data from JSON files.

Usage:
    python scripts/seed_knowledge_base.py [--clear]
    
Options:
    --clear   Clear existing data before seeding

Author: FRESH AI Team
"""

import json
import sys
import os
import argparse
from datetime import date
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv(project_root / ".env")

# Data directory
DATA_DIR = project_root / "src" / "data" / "knowledge"


def get_supabase_client() -> Client:
    """Initialize Supabase client with admin privileges."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        raise ValueError(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables. "
            "Please check your .env file."
        )
    
    return create_client(url, key)


def load_json_file(filename: str) -> dict:
    """Load and parse a JSON file from the data directory."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_tables(db: Client, tables: list[str]) -> None:
    """Clear all data from specified tables."""
    print("\n🗑️  Clearing existing data...")
    for table in tables:
        try:
            # Delete all records
            db.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            print(f"  ✓ Cleared: {table}")
        except Exception as e:
            print(f"  ⚠ Could not clear {table}: {e}")


def seed_diseases(db: Client) -> dict[str, str]:
    """Seed diseases table and return mapping of name to id."""
    print("\n🦠 Seeding diseases...")
    data = load_json_file("diseases.json")
    
    disease_ids = {}
    
    for disease in data["diseases"]:
        record = {
            "name": disease["name"],
            "name_urdu": disease.get("name_urdu"),
            "disease_type": disease.get("disease_type"),
            "affected_fruits": disease["affected_fruits"],
            "symptoms": disease["symptoms"],
            "causes": disease.get("causes"),
            "prevention": disease.get("prevention"),
            "images": disease.get("images"),
            "severity_levels": disease.get("severity_levels"),
            "spread_conditions": disease.get("spread_conditions"),
            "detection_methods": disease.get("detection_methods"),
        }
        
        try:
            # Upsert to handle re-runs
            result = db.table("diseases").upsert(
                record, 
                on_conflict="name"
            ).execute()
            
            if result.data:
                disease_ids[disease["name"]] = result.data[0]["id"]
                print(f"  ✓ {disease['name']}")
        except Exception as e:
            print(f"  ✗ Failed to insert {disease['name']}: {e}")
    
    return disease_ids


def seed_treatments(db: Client, disease_ids: dict[str, str]) -> None:
    """Seed treatments table using disease ID mapping."""
    print("\n💊 Seeding treatments...")
    data = load_json_file("treatments.json")
    
    treatment_count = 0
    
    for disease_entry in data["treatments"]:
        disease_name = disease_entry["disease_name"]
        disease_id = disease_ids.get(disease_name)
        
        if not disease_id:
            print(f"  ⚠ Disease not found: {disease_name}, skipping treatments")
            continue
        
        for treatment in disease_entry["treatments"]:
            record = {
                "disease_id": disease_id,
                "treatment_type": treatment["treatment_type"],
                "product_name": treatment["product_name"],
                "product_name_urdu": treatment.get("product_name_urdu"),
                "active_ingredient": treatment.get("active_ingredient"),
                "concentration": treatment.get("concentration"),
                "dosage": treatment["dosage"],
                "application_method": treatment.get("application_method"),
                "application_timing": treatment.get("application_timing"),
                "frequency": treatment.get("frequency"),
                "pre_harvest_interval_days": treatment.get("pre_harvest_interval_days"),
                "re_entry_interval_hours": treatment.get("re_entry_interval_hours"),
                "safety_precautions": treatment.get("safety_precautions"),
                "effectiveness_rating": treatment.get("effectiveness_rating"),
                "cost_category": treatment.get("cost_category"),
                "availability_pakistan": treatment.get("availability_pakistan", True),
            }
            
            try:
                db.table("treatments").insert(record).execute()
                treatment_count += 1
            except Exception as e:
                print(f"  ✗ Failed to insert treatment {treatment['product_name']}: {e}")
    
    print(f"  ✓ Inserted {treatment_count} treatments")


def seed_mrl_limits(db: Client) -> None:
    """Seed MRL limits table."""
    print("\n📊 Seeding MRL limits...")
    data = load_json_file("mrl_limits.json")
    
    record_count = 0
    
    for pesticide_entry in data["mrl_limits"]:
        pesticide_name = pesticide_entry["pesticide_name"]
        active_ingredient = pesticide_entry["active_ingredient"]
        
        for limit in pesticide_entry["limits"]:
            record = {
                "pesticide_name": pesticide_name,
                "active_ingredient": active_ingredient,
                "fruit_type": limit["fruit_type"],
                "country_code": limit["country_code"],
                "country_name": limit["country_name"],
                "mrl_value": limit["mrl_value"],
                "unit": limit.get("unit", "mg/kg"),
                "source": limit.get("source"),
                "regulation_reference": limit.get("regulation_reference"),
                "last_updated": str(date.today()),
                "notes": limit.get("notes"),
            }
            
            try:
                # Upsert to handle conflicts
                db.table("mrl_limits").upsert(
                    record,
                    on_conflict="pesticide_name,fruit_type,country_code"
                ).execute()
                record_count += 1
            except Exception as e:
                print(f"  ✗ Failed: {pesticide_name}/{limit['fruit_type']}/{limit['country_code']}: {e}")
    
    print(f"  ✓ Inserted {record_count} MRL records")


def seed_export_requirements(db: Client) -> None:
    """Seed export requirements table."""
    print("\n🌍 Seeding export requirements...")
    data = load_json_file("export_requirements.json")
    
    record_count = 0
    
    for country_entry in data["export_requirements"]:
        country_code = country_entry["country_code"]
        country_name = country_entry["country_name"]
        
        for fruit_entry in country_entry.get("fruits", []):
            record = {
                "country_code": country_code,
                "country_name": country_name,
                "fruit_type": fruit_entry["fruit_type"],
                "phytosanitary_requirements": fruit_entry.get("phytosanitary_requirements"),
                "pest_free_requirements": fruit_entry.get("pest_free_requirements"),
                "packaging_standards": fruit_entry.get("packaging_standards"),
                "labeling_requirements": fruit_entry.get("labeling_requirements"),
                "documentation_required": fruit_entry.get("documentation_required"),
                "temperature_requirements": fruit_entry.get("temperature_requirements"),
                "humidity_requirements": fruit_entry.get("humidity_requirements"),
                "shelf_life_days": fruit_entry.get("shelf_life_days"),
                "certifications_needed": fruit_entry.get("certifications_needed"),
                "import_restrictions": fruit_entry.get("import_restrictions"),
                "port_of_entry": fruit_entry.get("port_of_entry"),
                "inspection_requirements": fruit_entry.get("inspection_requirements"),
                "quarantine_treatment": fruit_entry.get("quarantine_treatment"),
                "season_restrictions": fruit_entry.get("season_restrictions"),
            }
            
            try:
                # Upsert to handle conflicts
                db.table("export_requirements").upsert(
                    record,
                    on_conflict="country_code,fruit_type"
                ).execute()
                record_count += 1
            except Exception as e:
                print(f"  ✗ Failed: {country_code}/{fruit_entry['fruit_type']}: {e}")
    
    print(f"  ✓ Inserted {record_count} export requirement records")


def seed_fruit_varieties(db: Client) -> None:
    """Seed fruit varieties table."""
    print("\n🍊 Seeding fruit varieties...")
    data = load_json_file("fruit_varieties.json")
    
    record_count = 0
    
    for fruit_entry in data["fruit_varieties"]:
        fruit_type = fruit_entry["fruit_type"]
        
        for variety in fruit_entry.get("varieties", []):
            record = {
                "fruit_type": fruit_type,
                "variety_name": variety["variety_name"],
                "variety_name_urdu": variety.get("variety_name_urdu"),
                "region": variety.get("region"),
                "harvest_season": variety.get("harvest_season"),
                "harvest_months": variety.get("harvest_months"),
                "export_grade_criteria": variety.get("export_grade_criteria"),
                "quality_parameters": variety.get("quality_parameters"),
                "common_diseases": variety.get("common_diseases"),
                "storage_requirements": variety.get("storage_requirements"),
                "shelf_life_days": variety.get("shelf_life_days"),
                "export_popularity": variety.get("export_popularity"),
            }
            
            try:
                # Upsert to handle conflicts
                db.table("fruit_varieties").upsert(
                    record,
                    on_conflict="fruit_type,variety_name"
                ).execute()
                record_count += 1
            except Exception as e:
                print(f"  ✗ Failed: {fruit_type}/{variety['variety_name']}: {e}")
    
    print(f"  ✓ Inserted {record_count} fruit variety records")


def seed_farming_calendar(db: Client) -> None:
    """Seed farming calendar with monthly activities."""
    print("\n📅 Seeding farming calendar...")
    
    # Farming calendar data structure
    calendar_data = {
        "mango": {
            1: {
                "activities": [
                    "Apply dormant spray for pest control",
                    "Pruning of dead and diseased branches",
                    "Prepare for pre-bloom sprays",
                    "Soil testing and nutrient management"
                ],
                "disease_risks": ["malformation", "powdery_mildew"],
                "recommended_treatments": ["Copper spray", "Sulfur dust"],
                "weather_considerations": ["Monitor for frost", "Ensure drainage"]
            },
            2: {
                "activities": [
                    "Pre-bloom fungicide application",
                    "Monitor for mango hopper",
                    "Irrigation management",
                    "Weed control around trees"
                ],
                "disease_risks": ["anthracnose", "powdery_mildew"],
                "recommended_treatments": ["Carbendazim", "Mancozeb", "Imidacloprid for hoppers"],
                "weather_considerations": ["Watch for late frost", "Avoid overhead irrigation"]
            },
            3: {
                "activities": [
                    "Flowering stage - critical spray period",
                    "Mango hopper control",
                    "Pollinator management",
                    "Fruit fly trap installation"
                ],
                "disease_risks": ["anthracnose", "powdery_mildew", "blossom_blight"],
                "recommended_treatments": ["Azoxystrobin", "Copper hydroxide"],
                "weather_considerations": ["Avoid spraying during bloom for pollinators", "Monitor humidity"]
            },
            4: {
                "activities": [
                    "Fruit set monitoring",
                    "Continue fungicide program",
                    "Fruit fly monitoring intensifies",
                    "Thinning of excess fruit clusters"
                ],
                "disease_risks": ["anthracnose", "fruit_fly"],
                "recommended_treatments": ["Mancozeb", "Methyl eugenol traps"],
                "weather_considerations": ["Pre-monsoon period", "Heat stress management"]
            },
            5: {
                "activities": [
                    "Early harvest begins (Sindhri)",
                    "Intensive fruit fly management",
                    "Post-harvest handling preparation",
                    "VHT facility coordination"
                ],
                "disease_risks": ["anthracnose", "fruit_fly", "stem_end_rot"],
                "recommended_treatments": ["Bait sprays", "Hot water treatment"],
                "weather_considerations": ["High temperatures", "Pre-harvest interval compliance"]
            },
            6: {
                "activities": [
                    "Peak harvest season",
                    "Export operations",
                    "Field sanitation",
                    "Continue fruit fly management"
                ],
                "disease_risks": ["fruit_fly", "anthracnose"],
                "recommended_treatments": ["Spinosad bait", "Copper for late fruits"],
                "weather_considerations": ["Monsoon onset", "High humidity disease pressure"]
            },
            7: {
                "activities": [
                    "Late variety harvest (Chaunsa)",
                    "Post-harvest orchard cleanup",
                    "Monsoon disease management",
                    "Drainage maintenance"
                ],
                "disease_risks": ["anthracnose", "dieback"],
                "recommended_treatments": ["Copper sprays after harvest"],
                "weather_considerations": ["Heavy rains", "Waterlogging prevention"]
            },
            8: {
                "activities": [
                    "End of harvest season",
                    "Pruning after harvest",
                    "Fertilizer application",
                    "Soil amendments"
                ],
                "disease_risks": ["dieback", "gummosis"],
                "recommended_treatments": ["Wound dressing after pruning"],
                "weather_considerations": ["Monsoon management", "Avoid fertilizing in waterlogged conditions"]
            },
            9: {
                "activities": [
                    "Post-monsoon orchard maintenance",
                    "Continue fertilization",
                    "Pest monitoring",
                    "Irrigation setup for dry season"
                ],
                "disease_risks": ["stem_borer", "bark_eating_caterpillar"],
                "recommended_treatments": ["Trunk spray for borers"],
                "weather_considerations": ["Transition period", "Monitor soil moisture"]
            },
            10: {
                "activities": [
                    "Pre-flowering preparation",
                    "Micronutrient spray (Zinc, Boron)",
                    "Pest control",
                    "Irrigation management"
                ],
                "disease_risks": ["malformation"],
                "recommended_treatments": ["NAA spray to prevent malformation"],
                "weather_considerations": ["Cool nights favor flower initiation"]
            },
            11: {
                "activities": [
                    "Flower bud development",
                    "Whitewash trunk (sunburn prevention)",
                    "Continue micronutrient program",
                    "Prepare for flowering sprays"
                ],
                "disease_risks": ["malformation", "powdery_mildew"],
                "recommended_treatments": ["Pre-bloom copper"],
                "weather_considerations": ["Cool dry weather", "Frost risk monitoring"]
            },
            12: {
                "activities": [
                    "Early flowering begins",
                    "Mango hopper monitoring starts",
                    "Apply pre-bloom sprays",
                    "Orchard floor management"
                ],
                "disease_risks": ["powdery_mildew", "anthracnose"],
                "recommended_treatments": ["Sulfur", "Carbendazim"],
                "weather_considerations": ["Cold weather", "Frost protection for young trees"]
            }
        },
        "orange": {
            1: {
                "activities": [
                    "Peak Kinnow harvest",
                    "Post-harvest handling",
                    "Export operations",
                    "Orchard cleanup"
                ],
                "disease_risks": ["citrus_canker", "black_spot"],
                "recommended_treatments": ["Post-harvest fungicide dip"],
                "weather_considerations": ["Cold storage management", "Frost risk"]
            },
            2: {
                "activities": [
                    "End of Kinnow season",
                    "Post-harvest pruning",
                    "Fertilizer application",
                    "Pest monitoring"
                ],
                "disease_risks": ["citrus_canker"],
                "recommended_treatments": ["Copper spray after pruning"],
                "weather_considerations": ["Late frost risk", "Transition to spring"]
            },
            3: {
                "activities": [
                    "Spring flush emergence",
                    "Leaf miner control",
                    "Pre-bloom nutrition",
                    "Irrigation initiation"
                ],
                "disease_risks": ["citrus_canker", "leaf_miner_damage"],
                "recommended_treatments": ["Imidacloprid for leaf miner", "Copper spray"],
                "weather_considerations": ["Spring growth", "Watch for hailstorms"]
            },
            4: {
                "activities": [
                    "Flowering period",
                    "Citrus psyllid monitoring",
                    "Pollination support",
                    "Micronutrient spray"
                ],
                "disease_risks": ["citrus_canker", "greening_HLB"],
                "recommended_treatments": ["Avoid copper during full bloom"],
                "weather_considerations": ["Hot winds can cause flower drop"]
            },
            5: {
                "activities": [
                    "Fruit set",
                    "June drop thinning",
                    "Continue pest management",
                    "Irrigation scheduling"
                ],
                "disease_risks": ["fruit_fly", "citrus_canker"],
                "recommended_treatments": ["Light copper application"],
                "weather_considerations": ["Heat stress", "Adequate irrigation"]
            },
            6: {
                "activities": [
                    "Fruit development",
                    "Monsoon preparation",
                    "Disease prevention program",
                    "Fruit fly trap maintenance"
                ],
                "disease_risks": ["citrus_canker", "black_spot"],
                "recommended_treatments": ["Mancozeb + Copper tank mix"],
                "weather_considerations": ["Pre-monsoon sprays critical"]
            },
            7: {
                "activities": [
                    "Monsoon disease management",
                    "Intensive fungicide program",
                    "Drainage maintenance",
                    "Nutrient management"
                ],
                "disease_risks": ["citrus_canker", "black_spot", "gummosis"],
                "recommended_treatments": ["Copper sprays every 14 days"],
                "weather_considerations": ["High humidity", "Rain wash-off of sprays"]
            },
            8: {
                "activities": [
                    "Continue monsoon management",
                    "Fruit size development",
                    "Potassium application",
                    "Pest monitoring"
                ],
                "disease_risks": ["black_spot", "citrus_canker"],
                "recommended_treatments": ["Mancozeb application"],
                "weather_considerations": ["Monsoon continues", "Watch for waterlogging"]
            },
            9: {
                "activities": [
                    "Post-monsoon management",
                    "Fruit maturation begins",
                    "Color development",
                    "Reduce nitrogen"
                ],
                "disease_risks": ["black_spot"],
                "recommended_treatments": ["Late season fungicide if needed"],
                "weather_considerations": ["Humidity decreasing", "Good for fruit quality"]
            },
            10: {
                "activities": [
                    "Pre-harvest preparation",
                    "Quality assessment",
                    "Pack house preparation",
                    "Export documentation"
                ],
                "disease_risks": ["storage_diseases"],
                "recommended_treatments": ["Wax coating preparation"],
                "weather_considerations": ["Optimal harvest weather", "Monitor maturity"]
            },
            11: {
                "activities": [
                    "Early harvest begins",
                    "Continue quality monitoring",
                    "Export operations start",
                    "Cold storage preparation"
                ],
                "disease_risks": ["post_harvest_rot"],
                "recommended_treatments": ["Post-harvest thiabendazole dip"],
                "weather_considerations": ["Cool nights improve color"]
            },
            12: {
                "activities": [
                    "Main Kinnow harvest",
                    "Peak export season",
                    "Careful handling",
                    "Storage management"
                ],
                "disease_risks": ["storage_diseases", "chilling_injury"],
                "recommended_treatments": ["Proper cold chain maintenance"],
                "weather_considerations": ["Freezing temperatures", "Careful temperature management"]
            }
        }
    }
    
    record_count = 0
    
    for fruit_type, months in calendar_data.items():
        for month, data in months.items():
            record = {
                "fruit_type": fruit_type,
                "month": month,
                "activities": data["activities"],
                "disease_risks": data.get("disease_risks", []),
                "recommended_treatments": data.get("recommended_treatments", []),
                "weather_considerations": data.get("weather_considerations", []),
            }
            
            try:
                db.table("farming_calendar").upsert(
                    record,
                    on_conflict="fruit_type,month"
                ).execute()
                record_count += 1
            except Exception as e:
                print(f"  ✗ Failed: {fruit_type}/month {month}: {e}")
    
    print(f"  ✓ Inserted {record_count} farming calendar records")


def main():
    """Main entry point for the seed script."""
    parser = argparse.ArgumentParser(
        description="Seed the AI Assistant knowledge base"
    )
    parser.add_argument(
        "--clear", 
        action="store_true",
        help="Clear existing data before seeding"
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("🌱 FRESH AI Knowledge Base Seeder")
    print("=" * 60)
    
    # Verify data directory exists
    if not DATA_DIR.exists():
        print(f"\n❌ Error: Data directory not found: {DATA_DIR}")
        print("Please ensure the JSON seed files are in place.")
        sys.exit(1)
    
    # List available data files
    print(f"\n📁 Data directory: {DATA_DIR}")
    json_files = list(DATA_DIR.glob("*.json"))
    print(f"   Found {len(json_files)} JSON files:")
    for f in json_files:
        print(f"   - {f.name}")
    
    try:
        # Initialize database connection
        print("\n🔌 Connecting to Supabase...")
        db = get_supabase_client()
        print("   ✓ Connected successfully")
        
        # Tables to manage
        tables = [
            "farming_calendar",
            "fruit_varieties", 
            "export_requirements",
            "mrl_limits",
            "treatments",
            "diseases"
        ]
        
        # Clear existing data if requested
        if args.clear:
            clear_tables(db, tables)
        
        # Seed in order (diseases first for foreign key references)
        disease_ids = seed_diseases(db)
        seed_treatments(db, disease_ids)
        seed_mrl_limits(db)
        seed_export_requirements(db)
        seed_fruit_varieties(db)
        seed_farming_calendar(db)
        
        print("\n" + "=" * 60)
        print("✅ Knowledge base seeding completed successfully!")
        print("=" * 60)
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌ File Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
